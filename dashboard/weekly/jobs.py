"""Durable single-worker forecast queue with cancellable subprocess isolation.

Local/VM/container deployments autostart a detached supervisor. Serverless web
deployments connect to job_service on a persistent host instead.
"""
import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import secrets
import sqlite3
import subprocess
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

TERMINAL = {'completed', 'failed', 'cancelled'}
LEASE_SECONDS = 30
ROOT = Path(__file__).resolve().parents[2]


class JobError(ValueError):
    pass


class JobNotFound(JobError):
    pass


def database_path():
    return Path(os.environ.get('WEEKLY_JOB_DIR', str(ROOT / '.forecast-jobs'))).resolve() / 'jobs.sqlite3'


class Queue:
    def __init__(self, path=None):
        self.path = Path(path or database_path()).resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY, signature TEXT UNIQUE NOT NULL,
                    status TEXT NOT NULL, request TEXT NOT NULL, result TEXT,
                    progress TEXT NOT NULL, created REAL NOT NULL, updated REAL NOT NULL,
                    started REAL, attempt TEXT);
                CREATE TABLE IF NOT EXISTS worker (
                    singleton INTEGER PRIMARY KEY CHECK(singleton=1), owner TEXT, heartbeat REAL);
            ''')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def submit(self, dataset, disease, config):
        from dashboard.weekly.model import cache_key, training_series
        from dashboard.weekly.selection import evaluation_splits, validate_configuration
        validate_configuration(config)
        if not dataset or not dataset.get('records'):
            raise JobError('Choose a validated Active Dataset first.')
        values, _ = training_series(dataset, disease)
        evaluation_splits(len(values))  # Cheap preflight before queueing thousands of fits.
        signature = cache_key(dataset, disease, config)
        request = json.dumps({'dataset': dataset, 'disease': disease, 'config': config}, allow_nan=False)
        stamp = time.time()
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            existing = db.execute('SELECT id,status FROM jobs WHERE signature=?', (signature,)).fetchone()
            if existing and existing['status'] not in ('failed', 'cancelled'):
                identity = existing['id']
            else:
                # Rotate capability ID on retry; old polling/cancel requests cannot affect a new attempt.
                identity = secrets.token_hex(24)
                if existing:
                    db.execute('DELETE FROM jobs WHERE id=?', (existing['id'],))
                db.execute('INSERT INTO jobs(id,signature,status,request,progress,created,updated) VALUES(?,?,?,?,?,?,?)',
                           (identity, signature, 'queued', request,
                            json.dumps({'stage': 'Queued', 'detail': 'Waiting for the forecast worker.'}), stamp, stamp))
        state = self.status(identity)
        state['cached'] = bool(existing and existing['status'] == 'completed')
        return state

    def status(self, identity, include_result=True):
        with self.connect() as db:
            row = db.execute('SELECT * FROM jobs WHERE id=?', (identity,)).fetchone()
        if row is None:
            raise JobNotFound('Forecast job was not found. Generate again to start or retrieve a matching forecast.')
        result = {k: row[k] for k in ('id', 'signature', 'status', 'created', 'updated', 'started')}
        result['progress'] = json.loads(row['progress'])
        result['elapsed_seconds'] = max(0, int((row['updated'] if row['status'] in TERMINAL else time.time()) - (row['started'] or row['created'])))
        if include_result and row['result']:
            result['result'] = json.loads(row['result'])
        return result

    def cancel(self, identity):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT status FROM jobs WHERE id=?', (identity,)).fetchone()
            if row is None:
                raise JobNotFound('Forecast job was not found.')
            if row['status'] not in TERMINAL:
                status = 'cancelled' if row['status'] == 'queued' else 'cancelling'
                db.execute('UPDATE jobs SET status=?,updated=?,progress=? WHERE id=?',
                           (status, time.time(), json.dumps({'stage': status.capitalize(), 'detail': 'Stopping the worker; no partial forecast will be used.'}), identity))
        return self.status(identity)

    def acquire_worker(self, owner):
        stamp = time.time()
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT * FROM worker WHERE singleton=1').fetchone()
            if row and row['heartbeat'] > stamp - LEASE_SECONDS:
                return False
            # A vanished worker must never leave a permanently running job or cache a partial result.
            db.execute("UPDATE jobs SET status=CASE WHEN status='cancelling' THEN 'cancelled' ELSE 'failed' END, updated=?,progress=? WHERE status IN ('running','cancelling')",
                       (stamp, json.dumps({'stage': 'Worker interrupted', 'detail': 'The worker stopped. Generate again to retry.'})))
            db.execute('INSERT OR REPLACE INTO worker VALUES(1,?,?)', (owner, stamp))
            return True

    def heartbeat(self, owner):
        with self.connect() as db:
            return db.execute('UPDATE worker SET heartbeat=? WHERE singleton=1 AND owner=?',
                              (time.time(), owner)).rowcount == 1

    def release_worker(self, owner):
        with self.connect() as db:
            db.execute('DELETE FROM worker WHERE owner=?', (owner,))

    def worker_alive(self):
        with self.connect() as db:
            row = db.execute('SELECT heartbeat FROM worker WHERE singleton=1').fetchone()
        return bool(row and row['heartbeat'] > time.time() - LEASE_SECONDS)

    def claim(self):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute("SELECT id FROM jobs WHERE status='queued' ORDER BY created LIMIT 1").fetchone()
            if not row:
                return None
            attempt = secrets.token_hex(16)
            db.execute("UPDATE jobs SET status='running',attempt=?,started=?,updated=? WHERE id=?", (attempt, time.time(), time.time(), row['id']))
            return row['id'], attempt

    def progress(self, identity, attempt, progress):
        with self.connect() as db:
            changed = db.execute("UPDATE jobs SET progress=?,updated=? WHERE id=? AND attempt=? AND status='running'",
                                 (json.dumps(progress, allow_nan=False), time.time(), identity, attempt)).rowcount
        if not changed:
            raise InterruptedError('Forecast job is no longer running.')

    def finish(self, identity, attempt, result=None, error=None):
        status = 'failed' if error else 'completed'
        with self.connect() as db:
            db.execute("UPDATE jobs SET status=?,result=?,progress=?,updated=? WHERE id=? AND attempt=? AND status='running'",
                       (status, json.dumps(result, allow_nan=False) if result is not None else None,
                        json.dumps({'stage': status.capitalize(), 'detail': error or 'Forecast saved. Matching requests reuse this result.'}),
                        time.time(), identity, attempt))


def spawn(arguments, log_path):
    env = os.environ.copy()
    # One numerical worker, with bounded BLAS threads, keeps the dashboard responsive.
    for key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
        env[key] = os.environ.get('WEEKLY_WORKER_THREADS', '1')
    options = {'creationflags': subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {'start_new_session': True}
    with Path(log_path).open('ab') as log:
        return subprocess.Popen([sys.executable, '-m', 'dashboard.weekly.jobs', *arguments], cwd=ROOT,
                                env=env, stdin=subprocess.DEVNULL, stdout=log, stderr=log, **options)


def ensure_worker(queue):
    if not queue.worker_alive() and os.environ.get('WEEKLY_JOB_AUTOSTART', '1') != '0':
        spawn(['worker', '--database', str(queue.path)], queue.path.parent / 'worker.log')


def execute_job(queue, identity, attempt, runner=None):
    from dashboard.weekly.model import run
    from dashboard.weekly.progress import reporting
    with queue.connect() as db:
        row = db.execute("SELECT request FROM jobs WHERE id=? AND attempt=? AND status='running'", (identity, attempt)).fetchone()
    if not row:
        return
    request = json.loads(row['request'])
    phase = {}
    def update(progress):
        nonlocal phase
        if progress['stage'] == 'NNAR initialization' and phase:
            progress = {**phase, 'detail': phase.get('detail', '') + '; ' + progress['detail']}
        else:
            phase = progress
        queue.progress(identity, attempt, progress)
    try:
        with reporting(update):
            update({'stage': 'Preparing weekly series', 'detail': 'Checking chronology and reporting completeness.'})
            result = (runner or run)(request['dataset'], request['disease'], request['config'])
        error = result.get('failure_reason') if not (result.get('hybrid') or result.get('sarima')) else None
        queue.finish(identity, attempt, result, error)
    except InterruptedError:
        pass
    except Exception as exc:
        queue.finish(identity, attempt, error=str(exc))


def supervise(queue, idle_seconds=300):
    owner = secrets.token_hex(16)
    if not queue.acquire_worker(owner):
        return
    last_work = time.monotonic()
    child = None
    try:
        while queue.heartbeat(owner):
            claimed = queue.claim()
            if not claimed:
                if idle_seconds and time.monotonic() - last_work >= idle_seconds:
                    return
                time.sleep(1)
                continue
            identity, attempt = claimed
            try:
                child = spawn(['execute', '--database', str(queue.path), '--job', identity, '--attempt', attempt],
                              queue.path.parent / 'worker.log')
                while child.poll() is None:
                    state = queue.status(identity, include_result=False)['status']
                    if not queue.heartbeat(owner) or state != 'running':
                        child.terminate()
                        try:
                            child.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            child.kill()
                            child.wait()
                        break
                    time.sleep(.5)
                with queue.connect() as db:
                    db.execute("UPDATE jobs SET status='cancelled',updated=?,progress=? WHERE id=? AND attempt=? AND status='cancelling'",
                               (time.time(), json.dumps({'stage': 'Cancelled', 'detail': 'Stopped. Generate Forecast starts a new attempt.'}), identity, attempt))
                if queue.status(identity, include_result=False)['status'] == 'running':
                    queue.finish(identity, attempt, error=f'Forecast worker exited before saving a result (exit {child.returncode}). Generate again to retry.')
            except Exception as exc:
                queue.finish(identity, attempt, error=str(exc))
            finally:
                if child and child.poll() is None:
                    child.terminate()
                    child.wait(timeout=5)
                child = None
            last_work = time.monotonic()
    finally:
        queue.release_worker(owner)


def remote_request(action, payload=None):
    base = os.environ.get('WEEKLY_JOB_SERVICE_URL', '').rstrip('/')
    parsed = urlparse(base)
    if parsed.scheme != 'https' and not (parsed.scheme == 'http' and parsed.hostname in ('127.0.0.1', 'localhost')):
        raise JobError('The forecast worker service must use HTTPS (localhost HTTP is allowed for development).')
    token = os.environ.get('WEEKLY_JOB_SERVICE_TOKEN')
    if not token:
        raise JobError('The forecast worker service token is not configured.')
    request = Request(base + '/jobs/' + action, data=json.dumps(payload or {}, allow_nan=False).encode(),
                      headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token}, method='POST')
    try:
        with urlopen(request, timeout=15) as response:
            return json.load(response)
    except HTTPError as exc:
        try:
            body = json.loads(exc.read())
            message = body.get('error', f'Worker service returned {exc.code}.')
        except (ValueError, AttributeError):
            body = {}
            message = f'Worker service returned {exc.code}.'
        if body.get('code') == 'job_not_found':
            raise JobNotFound(message) from exc
        raise JobError(message) from exc
    except (URLError, TimeoutError) as exc:
        raise JobError('The forecast worker service could not be reached. The job may still be running; retry status shortly.') from exc


def local_queue():
    if os.environ.get('VERCEL'):
        raise JobError('Forecasting needs a persistent worker. Configure WEEKLY_JOB_SERVICE_URL and WEEKLY_JOB_SERVICE_TOKEN for this Vercel deployment.')
    return Queue()


def submit(dataset, disease, config):
    if os.environ.get('WEEKLY_JOB_SERVICE_URL'):
        return remote_request('submit', {'dataset': dataset, 'disease': disease, 'config': config})
    queue = local_queue()
    state = queue.submit(dataset, disease, config)
    if state['status'] not in TERMINAL:
        ensure_worker(queue)
    return state


def poll(identity):
    if os.environ.get('WEEKLY_JOB_SERVICE_URL'):
        return remote_request('status', {'id': identity})
    queue = local_queue()
    state = queue.status(identity)
    if state['status'] not in TERMINAL:
        ensure_worker(queue)
    return state


def cancel(identity):
    if os.environ.get('WEEKLY_JOB_SERVICE_URL'):
        return remote_request('cancel', {'id': identity})
    queue = local_queue()
    state = queue.cancel(identity)
    if state['status'] not in TERMINAL:
        ensure_worker(queue)
    return state


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['worker', 'execute'])
    parser.add_argument('--database', default=str(database_path()))
    parser.add_argument('--job')
    parser.add_argument('--attempt')
    parser.add_argument('--idle-seconds', type=int, default=300, help='0 keeps a standalone worker running indefinitely')
    args = parser.parse_args()
    queue = Queue(args.database)
    if args.command == 'worker':
        supervise(queue, args.idle_seconds)
    else:
        execute_job(queue, args.job, args.attempt)


if __name__ == '__main__':
    main()
