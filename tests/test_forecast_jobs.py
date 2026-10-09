"""Durable queue, subprocess cancellation, remote boundary and UI polling contracts."""
from concurrent.futures import ThreadPoolExecutor
import json
import os
import subprocess
import sys
import threading
from types import SimpleNamespace

import pytest
from dash import no_update

from dashboard.weekly import jobs, model, ui
from dashboard.weekly.progress import report
from dashboard.weekly.selection import approved_configuration
from tests.test_weekly import dataset


def active_data():
    return dataset([{'disease': 'Measles', 'year': 2019 + i // 52, 'morbidity_week': i % 52 + 1,
                     'case_count': i % 5} for i in range(364)],
                   year_lengths={str(y): 52 for y in range(2019, 2028)})


def result_for(active, config):
    return {'dataset_id': active['id'], 'disease': 'Measles', 'model_version': model.VERSION,
            'context': active['context'], 'hybrid_status': 'Available', 'sarima_status': 'Available',
            'cache_key': model.cache_key(active, 'Measles', config), 'hybrid': [1] * 52, 'sarima': [2] * 52,
            'forecast_index': [{'year': 2026, 'morbidity_week': i + 1} for i in range(52)], 'metrics': {}}


def test_duplicate_submissions_are_atomic_and_reuse_disk_cache(tmp_path):
    q, active, c = jobs.Queue(tmp_path / 'jobs.db'), active_data(), approved_configuration()
    with ThreadPoolExecutor(max_workers=4) as pool:
        states = list(pool.map(lambda _: q.submit(active, 'Measles', c), range(4)))
    assert len({state['id'] for state in states}) == 1
    identity, attempt = q.claim()
    q.finish(identity, attempt, result_for(active, c))
    fresh = jobs.Queue(q.path)
    reused = fresh.submit(active, 'Measles', c)
    assert reused['status'] == 'completed' and reused['id'] == identity
    assert reused['cached'] is True
    assert reused['result']['hybrid'] == [1] * 52
    assert fresh.claim() is None
    changed = {**c, 'maxiter': c['maxiter'] + 1}
    assert fresh.submit(active, 'Measles', changed)['id'] != identity


def test_cancelled_attempt_cannot_publish_or_cancel_a_retry(tmp_path):
    q, active, c = jobs.Queue(tmp_path / 'jobs.db'), active_data(), approved_configuration()
    original = q.submit(active, 'Measles', c)
    identity, attempt = q.claim()
    assert q.cancel(identity)['status'] == 'cancelling'
    q.finish(identity, attempt, result_for(active, c))
    assert 'result' not in q.status(identity)
    with q.connect() as db:
        db.execute("UPDATE jobs SET status='cancelled' WHERE id=?", (identity,))
    replacement = q.submit(active, 'Measles', c)
    assert replacement['id'] != original['id']
    q.finish(identity, attempt, result_for(active, c))
    assert q.status(replacement['id'])['status'] == 'queued'
    with pytest.raises(jobs.JobError, match='not found'):
        q.cancel(identity)


def test_queued_cancellation_and_worker_lease_recovery(tmp_path):
    q, active, c = jobs.Queue(tmp_path / 'jobs.db'), active_data(), approved_configuration()
    state = q.submit(active, 'Measles', c)
    assert q.cancel(state['id'])['status'] == 'cancelled'
    assert q.claim() is None
    state = q.submit(active, 'Measles', c)
    assert q.acquire_worker('first')
    assert not q.acquire_worker('second')
    q.claim()
    with q.connect() as db:
        db.execute('UPDATE worker SET heartbeat=0')
    assert q.acquire_worker('second')
    recovered = q.status(state['id'])
    assert recovered['status'] == 'failed'
    assert 'interrupted' in recovered['progress']['stage'].lower()
    assert not q.heartbeat('first')


def test_worker_progress_and_complete_result_persist(tmp_path):
    q, active, c = jobs.Queue(tmp_path / 'jobs.db'), active_data(), approved_configuration()
    q.submit(active, 'Measles', c)
    identity, attempt = q.claim()
    def runner(dataset, disease, config):
        report('NNAR validation', 1, 3, 'Window 2/3')
        report('NNAR initialization', 2, 5, 'Initialization 3/5')
        progress = q.status(identity)['progress']
        assert progress['stage'] == 'NNAR validation'
        assert 'Window 2/3' in progress['detail'] and 'Initialization 3/5' in progress['detail']
        return result_for(dataset, config)
    jobs.execute_job(q, identity, attempt, runner)
    assert q.status(identity)['status'] == 'completed'
    assert jobs.Queue(q.path).status(identity)['result']['cache_key'] == model.cache_key(active, 'Measles', c)


def test_worker_exception_is_failed_not_cached_success(tmp_path):
    q, active, c = jobs.Queue(tmp_path / 'jobs.db'), active_data(), approved_configuration()
    q.submit(active, 'Measles', c)
    identity, attempt = q.claim()
    def fail(*args):
        raise RuntimeError('numerical worker failure')
    jobs.execute_job(q, identity, attempt, fail)
    assert q.status(identity)['status'] == 'failed'
    assert 'numerical worker failure' in q.status(identity)['progress']['detail']
    assert q.submit(active, 'Measles', c)['id'] != identity


def test_supervisor_cancels_a_real_process_mid_fit(tmp_path, monkeypatch):
    q, active, c = jobs.Queue(tmp_path / 'jobs.db'), active_data(), approved_configuration()
    state = q.submit(active, 'Measles', c)
    started = threading.Event()
    children = []
    def spawn(*args):
        options = {'creationflags': subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {}
        child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'], **options)
        children.append(child)
        started.set()
        return child
    monkeypatch.setattr(jobs, 'spawn', spawn)
    supervisor = threading.Thread(target=jobs.supervise, args=(q, 1), daemon=True)
    supervisor.start()
    try:
        assert started.wait(10)
        assert q.cancel(state['id'])['status'] == 'cancelling'
        supervisor.join(timeout=10)
        assert not supervisor.is_alive()
        assert children[0].poll() is not None
        assert q.status(state['id'])['status'] == 'cancelled'
        assert q.status(state['id'])['progress']['stage'] == 'Cancelled'
        assert 'result' not in q.status(state['id'])
    finally:
        for child in children:
            if child.poll() is None:
                child.terminate()
                child.wait(timeout=5)


def test_serverless_requires_remote_worker(monkeypatch):
    monkeypatch.setenv('VERCEL', '1')
    monkeypatch.delenv('WEEKLY_JOB_SERVICE_URL', raising=False)
    with pytest.raises(jobs.JobError, match='persistent worker'):
        jobs.poll('opaque-job-id')


def test_remote_service_auth_and_queue(tmp_path, monkeypatch):
    from dashboard.weekly.job_service import app
    monkeypatch.setenv('WEEKLY_JOB_DIR', str(tmp_path))
    monkeypatch.setenv('WEEKLY_JOB_AUTOSTART', '0')
    monkeypatch.setenv('WEEKLY_JOB_SERVICE_TOKEN', 'fixture-secret')
    client = app.test_client()
    assert client.post('/jobs/status', json={'id': 'x'}).status_code == 401
    headers = {'Authorization': 'Bearer fixture-secret'}
    response = client.post('/jobs/submit', headers=headers,
                           json={'dataset': active_data(), 'disease': 'Measles', 'config': approved_configuration()})
    assert response.status_code == 200
    identity = response.json['id']
    assert client.post('/jobs/status', headers=headers, json={'id': identity}).json['status'] == 'queued'
    assert client.post('/jobs/cancel', headers=headers, json={'id': identity}).json['status'] == 'cancelled'
    assert client.post('/jobs/status', headers=headers, json={}).status_code == 400


def test_remote_transport_calls_short_api_not_model(monkeypatch):
    import io
    monkeypatch.setenv('WEEKLY_JOB_SERVICE_URL', 'https://worker.example')
    monkeypatch.setenv('WEEKLY_JOB_SERVICE_TOKEN', 'fixture-secret')
    requests = []
    def open_request(request, timeout):
        requests.append(request)
        assert timeout == 15
        assert request.headers['Authorization'] == 'Bearer fixture-secret'
        return io.BytesIO(json.dumps({'status': 'queued'}).encode())
    monkeypatch.setattr(jobs, 'urlopen', open_request)
    assert jobs.poll('opaque')['status'] == 'queued'
    assert requests[0].full_url == 'https://worker.example/jobs/status'
    monkeypatch.setenv('WEEKLY_JOB_SERVICE_URL', 'http://worker.example')
    with pytest.raises(jobs.JobError, match='HTTPS'):
        jobs.poll('opaque')


def test_ui_submits_polls_and_cancels_without_training(tmp_path, monkeypatch):
    q, active, c = jobs.Queue(tmp_path / 'jobs.db'), active_data(), approved_configuration()
    monkeypatch.setattr(ui, 'model_configuration', lambda: c)
    monkeypatch.setattr(ui.jobs, 'submit', q.submit)
    monkeypatch.setattr(ui.jobs, 'poll', q.status)
    monkeypatch.setattr(ui.jobs, 'cancel', q.cancel)
    monkeypatch.setattr(model, 'run', lambda *args: pytest.fail('Web request must not fit models'))
    monkeypatch.setattr(ui, 'ctx', SimpleNamespace(triggered_id='w-run'))
    pending = ui.forecast(1, active, 'Measles')
    assert pending['job_status'] == 'queued'
    assert ui.forecast_job_controls(pending)[:3] == (False, True, False)
    content = str(ui.render('Forecast', active, 'Measles', pending, 13, 'Weekly')[0])
    assert 'running in the background' in content
    assert 'currently unavailable for this dataset' not in content
    identity, attempt = q.claim()
    q.progress(identity, attempt, {'stage': 'SARIMA screening', 'detail': 'Window 1/3'})
    monkeypatch.setattr(ui, 'ctx', SimpleNamespace(triggered_id='w-job-poll'))
    running = ui.forecast(1, active, 'Measles', prior=pending)
    assert running['job_status'] == 'running'
    assert 'Window 1/3' in ui.forecast_job_controls(running)[3]
    monkeypatch.setattr(ui, 'ctx', SimpleNamespace(triggered_id='w-cancel-forecast'))
    stopping = ui.forecast(1, active, 'Measles', prior=running)
    assert stopping['job_status'] == 'cancelling'


def test_ui_completion_stale_isolation_and_network_retry(tmp_path, monkeypatch):
    q, active, c = jobs.Queue(tmp_path / 'jobs.db'), active_data(), approved_configuration()
    monkeypatch.setattr(ui, 'model_configuration', lambda: c)
    monkeypatch.setattr(ui.jobs, 'submit', q.submit)
    monkeypatch.setattr(ui.jobs, 'poll', q.status)
    monkeypatch.setattr(ui, 'ctx', SimpleNamespace(triggered_id='w-run'))
    pending = ui.forecast(1, active, 'Measles')
    identity, attempt = q.claim()
    q.finish(identity, attempt, result_for(active, c))
    monkeypatch.setattr(ui, 'ctx', SimpleNamespace(triggered_id='w-job-poll'))
    done = ui.forecast(1, active, 'Measles', prior=pending)
    assert done['job_status'] == 'completed' and len(done['hybrid']) == 52
    assert ui.forecast_job_controls(done)[:3] == (True, False, True)
    assert ui.forecast_job_controls(done)[4] == 'action-progress job-finished'
    assert ui.forecast(1, active, 'Measles', prior=done) is no_update
    changed = active_data()
    changed['records'][0]['case_count'] = 999
    assert ui.forecast(1, changed, 'Measles', prior=pending) is no_update
    def offline(*args):
        raise jobs.JobError('temporary connection issue')
    monkeypatch.setattr(ui.jobs, 'poll', offline)
    retry = ui.forecast(1, active, 'Measles', prior=pending)
    assert retry['job_id'] == pending['job_id'] and retry['job_status'] == 'queued'
    assert 'temporary connection' in retry['job_connection_notice']


def test_saved_result_message_and_completed_render(tmp_path, monkeypatch):
    q, active, c = jobs.Queue(tmp_path / 'jobs.db'), active_data(), approved_configuration()
    state = q.submit(active, 'Measles', c)
    identity, attempt = q.claim()
    q.finish(identity, attempt, result_for(active, c))
    monkeypatch.setattr(ui.jobs, 'submit', q.submit)
    monkeypatch.setattr(ui, 'model_configuration', lambda: c)
    monkeypatch.setattr(ui, 'ctx', SimpleNamespace(triggered_id='w-run'))
    cached = ui.forecast(1, active, 'Measles')
    assert cached['job_id'] == state['id'] and cached['job_cached']
    assert ui.forecast_job_controls(cached)[3].startswith('Saved forecast loaded.')
    content = str(ui.render('Forecast', active, 'Measles', cached, 13, 'Weekly')[0])
    assert 'Hybrid SARIMA' in content and 'Demo projection' not in content
    assert q.claim() is None


def test_preflight_rejects_short_history_before_queueing(tmp_path):
    q = jobs.Queue(tmp_path / 'jobs.db')
    with pytest.raises(ValueError, match='insufficient initial'):
        q.submit(dataset(), 'Measles', approved_configuration())
    assert q.claim() is None


def test_real_worker_cli_reports_invalid_stored_request_without_hanging(tmp_path):
    q = jobs.Queue(tmp_path / 'jobs.db')
    state = q.submit(active_data(), 'Measles', approved_configuration())
    # Corrupt the saved protocol to exercise a real subprocess failure without a full grid fit.
    with q.connect() as db:
        request = json.loads(db.execute('SELECT request FROM jobs').fetchone()['request'])
        request['config']['candidates'] = []
        db.execute('UPDATE jobs SET request=?', (json.dumps(request),))
    child = jobs.spawn(['worker', '--database', str(q.path), '--idle-seconds', '1'], tmp_path / 'worker.log')
    try:
        child.wait(timeout=25)
        assert child.returncode == 0
        failed = q.status(state['id'])
        assert failed['status'] == 'failed'
        assert 'fixed candidates' in failed['progress']['detail']
    finally:
        if child.poll() is None:
            child.terminate()
            child.wait(timeout=5)


def test_missing_job_unlocks_ui_and_stale_job_does_not_disable_new_dataset(monkeypatch):
    active, c = active_data(), approved_configuration()
    pending = {'dataset_id': active['id'], 'disease': 'Measles', 'cache_key': model.cache_key(active, 'Measles', c),
               'job_id': 'gone', 'job_status': 'running'}
    monkeypatch.setattr(ui, 'ctx', SimpleNamespace(triggered_id='w-job-poll'))
    def missing(*args):
        raise jobs.JobNotFound('Job was removed')
    monkeypatch.setattr(ui.jobs, 'poll', missing)
    failed = ui.forecast(1, active, 'Measles', prior=pending)
    assert ui.forecast_job_controls(failed)[:3] == (True, False, True)
    changed = active_data()
    changed['records'][0]['case_count'] = 999
    assert ui.forecast_job_controls(pending, changed, 'Measles')[:3] == (True, False, True)
