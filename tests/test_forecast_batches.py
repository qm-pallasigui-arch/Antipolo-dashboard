"""Batch coordination, recovery and honest progress across browser sessions."""
import json
import threading
import time
import sys
import os
from concurrent.futures import ThreadPoolExecutor

import pytest

from dashboard.monthly.repositories.batch_repository import BatchRepository, BatchBusy, BatchInterrupted
from dashboard.monthly.repositories.ranking_repository import RankingRepository
from dashboard.monthly.forecast import ForecastService
from dashboard.monthly.forecasting.hybrid import HybridModel
from dashboard.monthly.forecasting.prophet_model import check_model_workspace
from dashboard.monthly.forecasting.errors import ForecastComponentError
from tests import test_monthly_system as acceptance


@pytest.fixture
def store(tmp_path):
    return acceptance.store.__wrapped__(tmp_path)


@pytest.fixture
def users(store):
    return acceptance.users.__wrapped__(store)


activate = acceptance.activate
from tests.test_hybrid_forecast import workflow


def test_unchanged_progress_updates_timer_without_replacing_live_notice(store, users):
    from dash import Dash
    from dashboard.monthly.ui import install
    app = Dash(__name__)
    install(app, store)
    client = app.server.test_client()
    acceptance.login(client)
    dataset = activate(store, users[0])
    batches = BatchRepository(store)
    batch = batches.claim(dataset['dataset_signature'])
    key = next(k for k in app.callback_map if 'm-generation-summary.children' in k)
    callback = app.callback_map[key]

    def poll(previous):
        result = client.post('/_dash-update-component', json={
            'output': key,
            'outputs': [{'id': o.component_id, 'property': o.component_property} for o in callback['output']],
            'inputs': [{'id': 'm-batch-poll', 'property': 'n_intervals', 'value': 1}],
            'state': [{'id': 'm-batch-state', 'property': 'data', 'value': previous}],
            'changedPropIds': ['m-batch-poll.n_intervals']})
        assert result.status_code == 200
        return result.get_json()['response']

    initial = poll(None)
    token = initial['m-batch-state']['data']
    unchanged = poll(token)
    assert 'm-generation-summary' not in unchanged
    assert 'm-generation-elapsed' in unchanged
    batches.update(batch, status='failed', error='Actionable failure')
    changed = poll(token)
    assert 'Actionable failure' in json.dumps(changed['m-generation-summary'])


def test_two_workers_cannot_claim_same_batch(store, users):
    dataset = activate(store, users[0])
    gate = threading.Barrier(2)
    def claim():
        gate.wait()
        try:
            return BatchRepository(store).claim(dataset['dataset_signature'])['id']
        except BatchBusy:
            return 'busy'
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: claim(), range(2)))
    assert results.count('busy') == 1


def test_expired_worker_is_recovered_and_cannot_save_late_results(store, users):
    dataset = activate(store, users[0])
    repo = BatchRepository(store)
    batch = repo.claim(dataset['dataset_signature'])
    service = ForecastService(store, HybridModel(workflow))
    original = service.model.generate
    def expire(rows, dates):
        with store.connect() as db:
            db.execute('UPDATE forecast_batches SET heartbeat=0 WHERE id=?', (batch['id'],))
        assert repo.latest(dataset['dataset_signature'])['status'] == 'interrupted'
        return original(rows, dates)
    service.model.generate = expire
    with pytest.raises(BatchInterrupted):
        service.run(users[0], 'A00-A09', group_id=batch['id'], batch=batch)
    with store.connect() as db:
        assert db.execute('SELECT count(*) FROM forecast_values').fetchone()[0] == 0
        assert db.execute('SELECT status FROM forecasts').fetchone()[0] == 'forecast_failed'
    fresh = repo.claim(dataset['dataset_signature'])
    assert fresh['id'] != batch['id']
    with pytest.raises(BatchInterrupted):
        repo.update(batch, status='completed')


def test_progress_partial_failures_and_old_rankings(store, users):
    dataset = activate(store, users[0])
    repo = BatchRepository(store)
    progress = []
    def record(rows, dates):
        progress.append(repo.latest(dataset['dataset_signature']))
        return workflow(rows, dates)
    ranking = ForecastService(store, HybridModel(record)).run_all(users[0])
    assert [p['completed'] for p in progress] == list(range(7))
    batch = repo.latest(dataset['dataset_signature'])
    assert batch['status'] == 'partial'
    assert batch['completed'] == 7 and batch['successes'] == 2 and len(batch['failures']) == 5
    assert ranking['forecast_months'] == [f'2026-{m:02}' for m in range(1, 13)]
    repo.claim(dataset['dataset_signature'])
    previous = RankingRepository(store).latest(dataset['dataset_signature'])
    assert previous['forecast_run_group_id'] == batch['id']
    assert any('earlier batch' in w for w in previous['warnings'])
    from dashboard.monthly.reports import build_report, export_html
    report = export_html(build_report(store, users[1], 'A00-A09'))
    assert 'earlier batch' in report and 'Forecast period: 2026-01 to 2026-12' in report
    assert 'Last observed month: 2025-12' in report


def test_deadline_recovery_even_with_fresh_heartbeat(store, users):
    dataset = activate(store, users[0])
    repo = BatchRepository(store)
    batch = repo.claim(dataset['dataset_signature'])
    batch['deadline'] = 0
    with store.connect() as db:
        db.execute('UPDATE forecast_batches SET payload=? WHERE id=?', (json.dumps(batch), batch['id']))
    assert repo.latest(dataset['dataset_signature'])['status'] == 'interrupted'


def test_temp_access_failure_is_immediate_and_actionable(tmp_path, monkeypatch):
    from pathlib import Path
    def denied(*args, **kwargs):
        raise PermissionError('denied')
    monkeypatch.setattr(Path, 'open', denied)
    with pytest.raises(ForecastComponentError, match='temporary folder is not writable'):
        check_model_workspace(tmp_path)


def test_dataset_activation_during_fit_discards_result(store, users):
    dataset = activate(store, users[0])
    def replace_dataset(rows, dates):
        activate(store, users[0], count=9)
        return workflow(rows, dates)
    with pytest.raises(BatchInterrupted, match='Dataset changed'):
        ForecastService(store, HybridModel(replace_dataset)).run_all(users[0])
    assert BatchRepository(store).latest(dataset['dataset_signature'])['status'] == 'failed'
    with store.connect() as db:
        assert db.execute('SELECT count(*) FROM forecast_values').fetchone()[0] == 0
        assert db.execute('SELECT status FROM forecasts').fetchone()[0] == 'forecast_failed'


def test_queue_survives_new_store_and_retains_history(store, users):
    from dashboard.monthly.store import Store
    dataset = activate(store, users[0])
    service = ForecastService(store)
    first = service.submit(users[0])
    repo = BatchRepository(Store(store.path, is_prototype=True))
    assert repo.latest(dataset['dataset_signature'])['status'] == 'queued'
    with pytest.raises(PermissionError):
        repo.cancel(users[1], first['id'])
    repo.cancel(users[0], first['id'])
    second = service.submit(users[0])
    with pytest.raises(ValueError):
        repo.cancel(users[0], first['id'])
    assert repo.get(second['id'])['status'] == 'queued'
    assert [b['status'] for b in repo.history(dataset['dataset_signature'])] == ['queued', 'cancelled']
    claimed = repo.take_next()
    assert claimed['id'] == second['id'] and claimed['status'] == 'running'
    assert repo.take_next() is None


def test_submission_returns_without_model_execution(store, users, monkeypatch):
    from dash import Dash
    from dashboard.monthly.ui import install
    app = Dash(__name__)
    service = ForecastService(store)
    def forbidden(*args, **kwargs):
        pytest.fail('HTTP request must not execute models')
    monkeypatch.setattr(service, 'run_all', forbidden)
    install(app, store, service)
    client = app.server.test_client()
    acceptance.login(client)
    dataset = activate(store, users[0])
    response = acceptance.dash_action(app, client, 'm-run')
    assert 'Forecast request accepted' in response.get_data(as_text=True)
    assert BatchRepository(store).latest(dataset['dataset_signature'])['status'] == 'queued'


def wait_for(predicate, timeout=20):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.05)
    raise AssertionError('Timed out waiting for worker evidence')


def process_alive(pid):
    if os.name == 'nt':
        import ctypes
        from ctypes import wintypes
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        handle = kernel.OpenProcess(0x1000, False, pid)
        if not handle:
            return False
        try:
            code = wintypes.DWORD()
            assert kernel.GetExitCodeProcess(handle, ctypes.byref(code))
            return code.value == 259
        finally:
            kernel.CloseHandle(handle)
    from pathlib import Path
    stat = Path(f'/proc/{pid}/stat')
    if stat.exists() and stat.read_text().split()[2] == 'Z':
        return False
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False


@pytest.mark.parametrize('cause', ['cancel', 'deadline', 'shutdown', 'dataset'])
def test_supervisor_stops_model_and_descendant(store, users, tmp_path, cause):
    from dashboard.monthly.worker import run_once
    activate(store, users[0])
    batch = ForecastService(store).submit(users[0])
    repo = BatchRepository(store)
    pid_file = tmp_path / 'processes.json'
    code = ("import sys,json,os,subprocess,time; from pathlib import Path; sys.stdin.readline(); "
            "child=subprocess.Popen([sys.executable,'-c','import time; time.sleep(120)']); "
            "Path(sys.argv[1]).write_text(json.dumps([os.getpid(),child.pid])); time.sleep(120)")
    stop = threading.Event()
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(run_once, store, stop, command=[sys.executable, '-c', code, str(pid_file)])
        try:
            wait_for(pid_file.exists)
            pids = json.loads(pid_file.read_text())
            assert all(process_alive(pid) for pid in pids)
            if cause == 'cancel':
                repo.cancel(users[0], batch['id'])
            elif cause == 'deadline':
                repo.update(batch, deadline=0)
            elif cause == 'dataset':
                activate(store, users[0], count=9)
            else:
                stop.set()
            assert future.result(timeout=20)
            wait_for(lambda: all(not process_alive(pid) for pid in pids))
        finally:
            stop.set()
    finished = repo.get(batch['id'])
    assert finished['status'] == ('cancelled' if cause == 'cancel' else 'interrupted')
    assert repo.history(batch['signature'])[0]['status'] == finished['status']


def test_crashed_child_is_interrupted_and_next_batch_can_run(store, users):
    from dashboard.monthly.worker import run_once
    activate(store, users[0])
    batch = ForecastService(store).submit(users[0])
    assert run_once(store, command=[sys.executable, '-c', 'import sys; sys.stdin.readline(); sys.exit(7)'])
    assert BatchRepository(store).get(batch['id'])['status'] == 'interrupted'
    assert ForecastService(store).submit(users[0])['id'] != batch['id']


def test_worker_rejects_changed_configuration_without_running_model(store, users):
    from dashboard.monthly.store import Store
    from dashboard.monthly.forecasting.config import PrototypeModelConfig
    activate(store, users[0])
    batch = ForecastService(store).submit(users[0])
    changed = Store(store.path, is_prototype=True, model_config=PrototypeModelConfig(seed=42))
    repo = BatchRepository(changed)
    assert repo.take_next() is None
    assert repo.get(batch['id'])['status'] == 'interrupted'


def test_two_supervisors_take_queue_only_once(store, users):
    activate(store, users[0])
    batch = ForecastService(store).submit(users[0])
    gate = threading.Barrier(2)
    def take():
        gate.wait()
        return BatchRepository(store).take_next()
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: take(), range(2)))
    assert results.count(None) == 1
    assert next(r for r in results if r)['id'] == batch['id']


def test_cancel_preserves_completed_values_and_blocks_ranking(store, users):
    activate(store, users[0])
    repo = BatchRepository(store)
    batch = ForecastService(store).submit(users[0])
    repo.take_next()
    service = ForecastService(store, HybridModel(workflow))
    run = service.run(users[0], 'A00-A09', group_id=batch['id'], batch=batch)
    repo.cancel(users[0], batch['id'])
    with pytest.raises(BatchInterrupted):
        service.run(users[0], 'B25-B34', group_id=batch['id'], batch=batch)
    with pytest.raises(BatchInterrupted):
        RankingRepository(store).save({}, batch=batch, finish_batch=True)
    with store.connect() as db:
        assert db.execute('SELECT count(*) FROM forecast_values WHERE forecast_run_id=?', (run['forecast_run_id'],)).fetchone()[0] == 12
        assert db.execute('SELECT count(*) FROM rankings').fetchone()[0] == 0


def test_completed_ranking_cannot_be_cancelled(store, users):
    dataset = activate(store, users[0])
    result = ForecastService(store, HybridModel(workflow)).run_all(users[0])
    repo = BatchRepository(store)
    with pytest.raises(ValueError):
        repo.cancel(users[0], result['forecast_run_group_id'])
    assert repo.latest(dataset['dataset_signature'])['status'] == 'partial'


def test_forged_viewer_cancellation_callback(store, users):
    from dash import Dash
    from dashboard.monthly.ui import install
    app = Dash(__name__)
    install(app, store)
    client = app.server.test_client()
    acceptance.login(client, 'health-user', 'another-long-password')
    activate(store, users[0])
    batch = ForecastService(store).submit(users[0])
    response = client.post('/_dash-update-component', json={
        'output': 'm-stop-feedback.children',
        'outputs': {'id': 'm-stop-feedback', 'property': 'children'},
        'inputs': [{'id': 'm-stop', 'property': 'submit_n_clicks', 'value': 1},
                   {'id': 'm-run', 'property': 'submit_n_clicks', 'value': None}],
        'state': [{'id': 'm-stop-target', 'property': 'data', 'value': batch['id']}],
        'changedPropIds': ['m-stop.submit_n_clicks']})
    assert response.status_code == 200
    assert 'permission required' in response.get_data(as_text=True)
    assert BatchRepository(store).get(batch['id'])['status'] == 'queued'


@pytest.mark.skipif(os.name != 'nt', reason='Windows Job Object owner-loss contract')
def test_abrupt_supervisor_loss_kills_owned_descendants(tmp_path):
    import subprocess
    pid_file = tmp_path / 'owned-pids.json'
    child = ("import sys,json,os,subprocess,time; from pathlib import Path; sys.stdin.readline(); "
             "p=subprocess.Popen([sys.executable,'-c','import time; time.sleep(120)']); "
             "Path(sys.argv[1]).write_text(json.dumps([os.getpid(),p.pid])); time.sleep(120)")
    supervisor = ("import sys,time; from dashboard.monthly.process_tree import ProcessTree; "
                  "tree=ProcessTree([sys.executable,'-c',sys.argv[1],sys.argv[2]]); "
                  "tree.process.stdin.write('{}\\n'); tree.process.stdin.flush(); time.sleep(120)")
    owner = subprocess.Popen([sys.executable, '-c', supervisor, child, str(pid_file)], creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        wait_for(pid_file.exists)
        pids = json.loads(pid_file.read_text())
        assert all(process_alive(pid) for pid in pids)
        owner.kill()
        owner.wait(timeout=10)
        wait_for(lambda: all(not process_alive(pid) for pid in pids))
    finally:
        if owner.poll() is None:
            owner.kill()
        owner.wait(timeout=10)
