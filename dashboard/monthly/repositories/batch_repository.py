"""Transactional batch ownership, progress and bounded heartbeat leases."""
import hashlib
import json
import secrets
import time

from ..forecasting.config import MODEL_VERSION

ACTIVE_STATUSES = ('queued', 'running', 'cancelling')


class BatchBusy(ValueError):
    pass


class BatchInterrupted(ValueError):
    pass


class BatchRepository:
    lease_seconds = 120
    max_seconds = 1800

    def __init__(self, store):
        self.store = store

    def slot(self, signature):
        return hashlib.sha256(f'{signature}:{MODEL_VERSION}:{self.store.is_prototype}:{self.store.model_config.signature}'.encode()).hexdigest()

    def _read(self, db, slot):
        row = db.execute('SELECT payload,heartbeat FROM forecast_batches WHERE slot=?', (slot,)).fetchone()
        if not row:
            return None
        batch = json.loads(row[0])
        if batch['status'] in ('running', 'cancelling') and (time.time() - row[1] > self.lease_seconds or time.time() > batch['deadline']):
            batch.update(status='interrupted', finished=time.time(), error='Forecast worker stopped responding. Generate forecasts again.')
            self._write(db, batch)
            self._close_runs(db, batch)
        return batch

    def _close_runs(self, db, batch):
        for record in db.execute("SELECT id,payload FROM forecasts WHERE signature=? AND status='running'", (batch['signature'],)).fetchall():
            run = json.loads(record[1])
            if run.get('forecast_run_group_id') == batch['id']:
                run.update(status='forecast_failed', forecast_status='forecast_failed', model_status='forecast_failed',
                           error=batch.get('error', 'Batch stopped before this forecast completed. Retry generation.'))
                db.execute("UPDATE forecasts SET status='forecast_failed',payload=? WHERE id=?", (json.dumps(run), record[0]))

    def _write(self, db, batch):
        db.execute('UPDATE forecast_batches SET heartbeat=?,payload=? WHERE slot=? AND id=?',
                   (time.time(), json.dumps(batch), batch['slot'], batch['id']))
        self._archive(db, batch)

    def _archive(self, db, batch):
        db.execute('INSERT INTO forecast_batch_history(id,slot,started,payload) VALUES (?,?,?,?) '
                   'ON CONFLICT(id) DO UPDATE SET payload=excluded.payload',
                   (batch['id'], batch['slot'], batch['started'], json.dumps(batch)))

    def latest(self, signature):
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            return self._read(db, self.slot(signature))

    def claim(self, signature, *, queued=False, actor_id=None):
        slot = self.slot(signature)
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            current = self._read(db, slot)
            if current and current['status'] in ACTIVE_STATUSES:
                raise BatchBusy('Forecasts are already running for this dataset. Follow the current progress below.')
            if current:
                self._archive(db, current)
            batch = dict(slot=slot, id=secrets.token_hex(16), signature=signature, status='queued' if queued else 'running',
                         started=time.time(), deadline=time.time() + self.max_seconds,
                         current=None, completed=0, successes=0, failures={}, actor_id=actor_id,
                         configuration=self.store.model_config.snapshot(), model_version=MODEL_VERSION,
                         is_prototype=self.store.is_prototype)
            db.execute('INSERT INTO forecast_batches(slot,id,heartbeat,payload) VALUES (?,?,?,?) '
                       'ON CONFLICT(slot) DO UPDATE SET id=excluded.id,heartbeat=excluded.heartbeat,payload=excluded.payload',
                       (slot, batch['id'], time.time(), json.dumps(batch)))
            self._archive(db, batch)
            return batch

    def get(self, identity):
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT slot FROM forecast_batches WHERE id=?', (identity,)).fetchone()
            if row:
                return self._read(db, row[0])
            row = db.execute('SELECT payload FROM forecast_batch_history WHERE id=?', (identity,)).fetchone()
            return json.loads(row[0]) if row else None

    def history(self, signature, limit=20):
        with self.store.connect() as db:
            return [json.loads(r[0]) for r in db.execute(
                'SELECT payload FROM forecast_batch_history WHERE slot=? ORDER BY started DESC LIMIT ?',
                (self.slot(signature), limit)).fetchall()]

    def take_next(self):
        """One serial worker per database, including across web/worker processes."""
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            batches = [self._read(db, r[0]) for r in db.execute('SELECT slot FROM forecast_batches').fetchall()]
            if any(b['status'] in ('running', 'cancelling') for b in batches):
                return None
            for batch in sorted(batches, key=lambda b: b['started']):
                if batch['status'] != 'queued':
                    continue
                if batch['model_version'] != MODEL_VERSION or batch['slot'] != self.slot(batch['signature']):
                    batch.update(status='interrupted', finished=time.time(), error='Worker configuration changed. Generate forecasts again.')
                    self._write(db, batch)
                    continue
                batch.update(status='running', execution_started=time.time(), deadline=time.time() + self.max_seconds)
                self._write(db, batch)
                return batch
        return None

    def cancel(self, user, identity):
        from ..store import require_admin
        require_admin(user)
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT slot FROM forecast_batches WHERE id=?', (identity,)).fetchone()
            batch = self._read(db, row[0]) if row else None
            if not batch or batch['status'] not in ACTIVE_STATUSES:
                raise ValueError('This batch has already stopped. Refresh its status.')
            batch.update(status='cancelled' if batch['status'] == 'queued' else 'cancelling',
                         error='Cancellation requested. Completed results are retained.')
            if batch['status'] == 'cancelled':
                batch['finished'] = time.time()
            self._write(db, batch)
            self._close_runs(db, batch)
            self.store.audit(user['id'], 'forecast_cancel', identity, db=db)
            return batch

    def stopped(self, batch, status, error):
        """Called after the supervisor has stopped/reaped the process tree."""
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            current = self._read(db, batch['slot'])
            if not current or current['id'] != batch['id'] or current['status'] not in ACTIVE_STATUSES:
                return
            current.update(status=status, error=error, current=None, finished=time.time())
            self._write(db, current)
            self._close_runs(db, current)

    def check(self, db, batch, *, require_dataset=False):
        current = self._read(db, batch['slot'])
        if not current or current['id'] != batch['id'] or current['status'] != 'running':
            raise BatchInterrupted('Forecast batch was interrupted; its late results were discarded. Generate forecasts again.')
        if require_dataset:
            active = db.execute("SELECT signature FROM datasets WHERE state='active'").fetchone()
            if not active or active[0] != batch['signature']:
                raise BatchInterrupted('Dataset changed during forecasting. Generate forecasts again.')
        return current

    def update(self, batch, **changes):
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            current = self.check(db, batch)
            current.update(changes)
            self._write(db, current)
            if current['status'] in ('failed', 'interrupted'):
                self._close_runs(db, current)
            return current
