"""Durable local job status with atomic duplicate suppression and real stage events.

SQLite coordinates web workers on one host. Workers run in background threads;
an independent heartbeat lets polling identify interrupted workers. This is not
a distributed queue: multi-host deployment needs a shared job service.
"""
from copy import deepcopy
import json
import os
from pathlib import Path
import sqlite3
import threading
import time
import uuid

from dashboard.logging_config import get_logger
from dashboard.weekly.data import now

logger = get_logger(__name__)
ROOT = Path(os.environ.get('WEEKLY_JOB_DIR', '.forecast-jobs'))


def connection():
    ROOT.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(ROOT / 'jobs.sqlite3', timeout=10)
    db.execute('CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, job_key TEXT, status TEXT, heartbeat REAL, payload TEXT)')
    return db


def read(run_id):
    with connection() as db:
        row = db.execute('SELECT payload, heartbeat, status FROM jobs WHERE id=?', (run_id,)).fetchone()
    if not row:
        return None
    value = json.loads(row[0])
    if row[2] == 'running' and time.time() - row[1] > 120:
        value.update(status='failed', failure_reason='The model worker was interrupted. Please retry.', completed_at=now())
        if value['events']:
            value['events'][-1].update(status='failed', completed_at=now())
        _save(value)
    return value


def _save(value):
    with connection() as db:
        db.execute('UPDATE jobs SET status=?, heartbeat=?, payload=? WHERE id=?',
                   (value['status'], time.time(), json.dumps(value, allow_nan=False), value['forecast_run_id']))


def submit(job_key, metadata, work):
    """work(emit) returns a completed result. Never publish partial predictions."""
    with connection() as db:
        db.execute('BEGIN IMMEDIATE')
        rows = db.execute("SELECT id, heartbeat FROM jobs WHERE job_key=? AND status='running'", (job_key,)).fetchall()
        for run_id, heartbeat in rows:
            if time.time() - heartbeat <= 120:
                return run_id
            db.execute("UPDATE jobs SET status='failed' WHERE id=?", (run_id,))
        run_id = uuid.uuid4().hex
        value = {**metadata, 'forecast_run_id': run_id, 'started_at': now(), 'completed_at': None,
                 'status': 'running', 'current_stage': 'started', 'events': [], 'warnings': [],
                 'warning_count': 0, 'failure_reason': None}
        db.execute('INSERT INTO jobs VALUES (?,?,?,?,?)', (run_id, job_key, 'running', time.time(), json.dumps(value)))

    def worker():
        stopped = threading.Event()
        def heartbeat():
            while not stopped.wait(10):
                with connection() as db:
                    db.execute("UPDATE jobs SET heartbeat=? WHERE id=? AND status='running'", (time.time(), run_id))
        threading.Thread(target=heartbeat, daemon=True).start()
        def emit(stage, message):
            if value['events']:
                value['events'][-1].update(status='complete', completed_at=now())
            value['current_stage'] = stage
            value['events'].append({'stage': stage, 'message': message, 'started_at': now(),
                                    'completed_at': None, 'status': 'running'})
            _save(value)
        try:
            emit('started', 'Model performance computation started.' if metadata['kind'] == 'evaluation' else 'Forecast started.')
            result = work(emit)
            value['warnings'] = list(result.get('warnings') or [])
            value['warning_count'] = len(value['warnings'])
            if result.get('failure_reason'):
                raise ValueError(result['failure_reason'])
            emit('save', 'Saving completed model results.')
            value['events'][-1].update(status='complete', completed_at=now())
            value.update(status='complete', current_stage='complete', completed_at=now())
            config = result.get('configuration', {})
            value.update(model_version=result.get('model_version'), locked_configuration_id=config.get('locked_configuration_id'))
            index = result.get('forecast_index') or []
            value.update(forecast_start_week=index[0] if index else None,
                         forecast_end_week=index[-1] if index else None, forecast_horizon=len(index))
            result['run_metadata'] = {**result.get('run_metadata', {}), **deepcopy(value)}
            if result.get('provisional_validation'):
                result['run_metadata'].update(provisional_run_id=config.get('provisional_run_id'),
                                               selection_run_id=config.get('selection_run_id'), mode='provisional')
            value['result'] = result
        except Exception as exc:
            logger.exception('Model job %s failed at %s', run_id, value['current_stage'])
            # Backend logs retain full details; the UI never receives arbitrary exception strings.
            value.update(status='failed', completed_at=now(),
                         failure_reason='Model work could not complete at this stage. Check dataset eligibility and the locked configuration; fitting must converge.')
            if metadata['kind'] == 'sample':
                value['failure_reason'] = 'Sample forecasting could not complete at this stage. Check data quality and available history; the sample model must converge.'
            if metadata['kind'] == 'provisional':
                value['failure_reason'] = 'Provisional validation could not complete at this stage. Check structural data quality, sufficient observed history and convergence. No research configuration is required.'
            known = ('No validated locked', 'Research dataset eligibility', 'Research disease must', 'SARIMA optimizer did not converge', 'NNAR optimizer did not converge', 'Insufficient complete residual lag windows', 'Terminal residual lag window', 'Historical evaluation requires', 'Training or validation data changed', 'Insufficient historical observations', 'Unresolved data validation errors', 'No complete, reported weeks')
            if isinstance(exc, ValueError) and str(exc).startswith(known + ('Provisional', 'Research ', 'The installed research configuration', 'Synthetic data requires', 'Model selection unavailable', 'SARIMA fitting failed', 'Hybrid unavailable', 'Case counts must', 'The operational model requires')):
                value['failure_reason'] = str(exc)
            if value['events']:
                value['events'][-1].update(status='failed', completed_at=now())
        finally:
            stopped.set()
            _save(value)
    threading.Thread(target=worker, daemon=True, name='weekly-model-' + run_id[:8]).start()
    return run_id
