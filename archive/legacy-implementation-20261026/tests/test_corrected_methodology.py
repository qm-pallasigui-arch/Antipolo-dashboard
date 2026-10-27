"""Regression evidence for the October methodology handoff (no research data)."""
import copy
import threading
import time

import numpy as np
import pytest
from statsmodels.stats.diagnostic import acorr_ljungbox

from dashboard.weekly import estimators, jobs, model, selection
from dashboard.weekly.data import digest


def locked(values, index):
    train, val, _, periods = selection.chronological_split(values, index)
    c = selection.base_config()
    c.update(candidates=[selection.candidates()[0]], selection_status='locked', periods=periods,
             selection_data_fingerprint=selection.selection_fingerprint(train, val))
    c['locked_configuration_id'] = digest(c)
    return c


def test_candidate_space_and_common_state_dimension():
    grid = selection.candidates()
    assert len(grid) == 144 == len({str(c) for c in grid})
    dimensions = [estimators.SARIMAX(np.ones(300), order=c['order'], seasonal_order=c['seasonal_order']).k_states for c in grid]
    assert max(dimensions) <= estimators.COMMON_BURN


def test_split_and_no_randomization():
    v = np.arange(530.)
    index = [(2016 + i // 53, i % 53 + 1) for i in range(530)]
    train, val, test, periods = selection.chronological_split(v, index)
    np.testing.assert_array_equal(train, v[:426])
    np.testing.assert_array_equal(val, v[426:478])
    np.testing.assert_array_equal(test, v[478:])
    assert periods['final_test'][-1] == [2025, 53]
    with pytest.raises(ValueError, match='insufficient'):
        selection.chronological_split(v[:200], index[:200])


def test_wrong_target_and_metric_coverage():
    assert selection.score_cases([100], np.array([100]) + [0])['rmse'] == 0
    assert selection.score_cases([100], [100])['rmse'] == 0
    m = selection.score_cases([0, np.nan, 2], [1.25, 500, 1])
    assert m['n'] == 2 and m['mape_n'] == 1 and m['mape'] == 50
    assert m['mae'] == 1.125 and m['rmse'] == pytest.approx(np.sqrt((1.25**2 + 1)/2))
    assert m['zero_actuals_excluded_from_mape'] == m['missing_actuals_excluded'] == 1
    with pytest.raises(ValueError, match='Invalid forecast'):
        selection.score_cases([1, 2], [1, np.nan])


def test_adf_and_adjusted_ljung_box():
    assert estimators.adf_diagnostic(np.zeros(300))['status'] == 'unavailable'
    residuals = np.random.default_rng(3).normal(size=300)
    candidate = {'order': [2, 1, 1], 'seasonal_order': [1, 1, 1, 52]}
    adf = estimators.adf_diagnostic(residuals)
    assert adf['status'] == 'available' and adf['observations'] and adf['selected_lags'] is not None
    for row in estimators.ljung_box(residuals, candidate):
        expected = acorr_ljungbox(residuals, lags=[row['lag']], model_df=5, return_df=True)
        assert row['model_df'] == 5
        assert row['pvalue'] == pytest.approx(expected.lb_pvalue.iloc[0])
    residuals[40] = np.nan
    assert all(r['status'] == 'unavailable' for r in estimators.ljung_box(residuals, candidate))


def test_real_shared_sarima_likelihood_and_burn():
    v = np.random.default_rng(7).normal(size=300)
    v[150] = np.nan
    c = selection.base_config()
    prediction, residuals, r = estimators.fit_sarima(v, 52, selection.candidates()[0], c)
    assert np.isfinite(prediction).all() and len(prediction) == 52
    assert np.isnan(residuals[:108]).all() and np.isnan(residuals[150])
    assert r['likelihood_burn'] == 108 and r['effective_observation_count'] == 191
    assert r['aic'] == pytest.approx(-2*r['log_likelihood'] + 2*r['parameter_count'])


def test_nnar_scaler_samples_and_recursion(monkeypatch):
    seen = {}
    real_scaler = estimators.StandardScaler
    class Scaler(real_scaler):
        def fit(self, X, y=None, **kwargs):
            seen['X'] = np.asarray(X).copy()
            return super().fit(X, y, **kwargs)
    class Network:
        def __init__(self, **kwargs):
            seen['settings'] = kwargs
        def fit(self, X, y):
            seen['y'] = y.copy()
        def predict(self, X):
            # Deterministic output makes recursive use visible after inverse scaling.
            seen.setdefault('forecast_X', []).append(X.copy())
            return [50.]
    monkeypatch.setattr(estimators, 'StandardScaler', Scaler)
    monkeypatch.setattr(estimators, 'MLPRegressor', Network)
    residuals = np.arange(200.)
    residuals[:108] = np.nan
    residuals[160] = np.nan
    c = selection.base_config()
    prediction, _ = estimators.nnar(residuals, 3, c)
    X, y = estimators.nnar_samples(residuals, c['nnar_lags'])
    np.testing.assert_array_equal(seen['X'], X)
    np.testing.assert_array_equal(seen['y'], y)
    assert 160 not in y and 161 not in y and 162 not in y
    scaler = real_scaler().fit(X)
    np.testing.assert_allclose(scaler.inverse_transform(seen['forecast_X'][1]), [[50, 199]])
    assert seen['settings']['activation'] == 'relu' and seen['settings']['solver'] == 'lbfgs'
    np.testing.assert_array_equal(prediction, [50, 50, 50])
    assert model.nnar is estimators.nnar


def test_selection_has_only_training_fits_and_case_targets(monkeypatch):
    train = np.full(300, 100.)
    val = np.full(52, 100.)
    calls = []
    def fit(values, steps, candidate, c):
        np.testing.assert_array_equal(values, train)
        calls.append(candidate)
        if len(calls) == 1:
            raise ValueError('deliberate nonconvergence')
        return np.full(52, 100.), np.zeros(300), {**candidate, 'fit_status': 'available', 'aic': float(len(calls)),
                                                 'likelihood_burn': 108, 'effective_observation_count': 192}
    neural_calls = []
    def neural(residuals, steps, c):
        assert np.array_equal(residuals, np.zeros(300))
        neural_calls.append(c['seed'])
        return np.zeros(52), []
    monkeypatch.setattr(selection, 'fit_sarima', fit)
    monkeypatch.setattr(selection, 'nnar', neural)
    periods = {'training': [[2016, 1], [2021, 40]], 'validation': [[2021, 41], [2022, 40]]}
    c, audit = selection.select_configuration(train, val, 'Dengue', periods)
    selection.verify_lock(c)
    assert len(calls) == 144 and len(neural_calls) == 96*3
    assert set(neural_calls) == set(estimators.SEEDS)
    assert audit['sarima_candidates'][0]['fit_status'] == 'failed'
    assert c['selection_diagnostics']['nnar']['median_validation']['rmse'] == 0
    assert c['nnar_helps_baseline'] is False
    c['alpha'] = 100
    with pytest.raises(ValueError, match='locked'):
        selection.verify_lock(c)


def test_final_test_refit_and_lock_immutability(monkeypatch):
    values = np.arange(400.)
    index = [(2016+i//52, i%52+1) for i in range(400)]
    c = locked(values, index)
    before = copy.deepcopy(c)
    def fit(v, steps, config, progress=None):
        np.testing.assert_array_equal(v, values[:-52])
        return {'hybrid': [1.]*52, 'sarima': [2.]*52, 'hybrid_status': 'Available',
                'sarima_status': 'Available', 'diagnostics': {}}
    monkeypatch.setattr(model, 'fit_models', fit)
    result = model.retrospective_evaluation({'metrics': {}, 'warnings': []}, values, index, c, 'Dengue')
    assert c == before and result['evaluation']['configuration_hash_before'] == result['evaluation']['configuration_hash_after']
    assert result['metrics']['hybrid']['n'] == result['metrics']['sarima']['n'] == 52
    for horizon in (4, 13, 26, 52):
        assert result['horizon_metrics'][str(horizon)]['scored_weeks'] == horizon


def wait_job(run_id):
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        value = jobs.read(run_id)
        if value['status'] != 'running':
            return value
        time.sleep(.01)
    pytest.fail('Job did not finish')


def test_progress_duplicate_warning_and_success(tmp_path, monkeypatch):
    monkeypatch.setattr(jobs, 'ROOT', tmp_path)
    release = threading.Event()
    def work(emit):
        emit('sarima', 'Fitting SARIMA')
        release.wait(3)
        emit('nnar', 'Fitting NNAR')
        return {'warnings': ['Missing observations preserved.'], 'hybrid': [1.]*52}
    metadata = {'kind': 'forecast', 'disease': 'Dengue', 'dataset_id': 'a'}
    run_id = jobs.submit('key', metadata, work)
    assert jobs.submit('key', metadata, work) == run_id
    release.set()
    done = wait_job(run_id)
    assert done['status'] == 'complete' and done['warning_count'] == 1
    assert all(e['status'] == 'complete' for e in done['events'])
    assert done['result']['run_metadata']['forecast_run_id'] == run_id


def test_progress_failure_and_stale_ui(tmp_path, monkeypatch):
    from dashboard.weekly import ui
    monkeypatch.setattr(jobs, 'ROOT', tmp_path)
    def work(emit):
        emit('sarima', 'Fitting SARIMA')
        raise ValueError('SARIMA optimizer did not converge.')
    run_id = jobs.submit('key', {'kind': 'forecast', 'disease': 'Dengue', 'dataset_id': 'a'}, work)
    failed = wait_job(run_id)
    assert failed['events'][-1]['status'] == 'failed' and 'result' not in failed
    prior = {'Dengue': {'hybrid': [2.]*52}}
    output = ui.poll_model_job(1, {'run_id': run_id}, {'id': 'a'}, 'Dengue', prior)
    assert output[0] is ui.no_update and output[-2:] == (False, False)
    output = ui.poll_model_job(1, {'run_id': run_id}, {'id': 'newer'}, 'Dengue', prior)
    assert output[0] is ui.no_update and output[1] == ''


def test_unverified_data_and_combined_category_rejected():
    with pytest.raises(ValueError, match='combined categories'):
        selection.require_research_data({}, 'Measles-Rubella')
    with pytest.raises(ValueError, match='eligibility'):
        selection.require_research_data({'metadata': {}, 'eligible': False}, 'Dengue')


def test_missing_configuration_is_not_labeled_as_dataset_failure():
    from dashboard.weekly import ui
    d, _ = research_fixture()
    events = []
    result = model.run(d, 'Measles', {'version': 'weekly-3', 'configurations': {}},
                       progress=lambda stage, message: events.append((stage, message)))
    assert events[-1][0] == 'configuration'
    assert result['failure_reason'].startswith('No validated locked')
    panel = ui.job_details({'kind': 'forecast', 'status': 'failed', 'events': [],
                            'failure_reason': result['failure_reason'],
                            'warnings': ['Week 53 present and preserved; statistical treatment pending unless explicitly configured.']})
    assert panel[1].role == 'alert'
    assert 'Generate Forecast determines the appropriate validation workflow' in str(panel[1])
    assert 'Advanced Options' in str(panel[1])
    assert 'Data notices' in str(panel[-1])
    assert 'statistical treatment pending' not in str(panel[-1])


def test_performance_without_configuration_reports_failure(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from dashboard.weekly import ui
    monkeypatch.setattr(jobs, 'ROOT', tmp_path)
    monkeypatch.setattr(ui, 'ctx', SimpleNamespace(triggered_id='w-evaluate'))
    monkeypatch.setattr(ui, 'model_configuration', lambda: {'version': 'weekly-3', 'configurations': {}})
    d, _ = research_fixture()
    current = ui.start_model_job(0, 1, d, 'Measles', {}, None)
    failed = wait_job(current['run_id'])
    assert failed['status'] == 'failed' and failed['current_stage'] == 'configuration'
    assert 'No validated locked' in failed['failure_reason']


def test_older_completed_job_cannot_replace_newer_result(monkeypatch):
    from dashboard.weekly import ui
    job = {'forecast_run_id': 'old', 'kind': 'forecast', 'dataset_id': 'a', 'disease': 'Measles',
           'status': 'complete', 'started_at': '2026-10-17T00:00:00', 'result': {'hybrid': [1.]}}
    monkeypatch.setattr(jobs, 'read', lambda _: job)
    prior = {'Measles': {'hybrid': [2.], 'run_metadata': {'started_at': '2026-10-17T01:00:00'}}}
    out = ui.poll_model_job(1, {'run_id': 'old'}, {'id': 'a'}, 'Measles', prior)
    assert out[0] is ui.no_update


def research_fixture():
    """Fabricated unit-test records; never used as research performance evidence."""
    from tests.test_weekly import dataset
    records = [{'disease': 'Measles', 'year': 2016+i//52, 'morbidity_week': i%52+1,
                'case_count': int(10 + i % 7)} for i in range(400)]
    d = dataset(records, year_lengths={str(y): 52 for y in range(2016, 2026)})
    values, index = model.training_series(d, 'Measles')
    return d, locked(values, index)


def test_operational_all_history_single_path_no_search(monkeypatch):
    d, c = research_fixture()
    calls = []
    def fit(values, steps, config):
        calls.append((len(values), steps, copy.deepcopy(config)))
        return {'hybrid': list(np.arange(52.)), 'sarima': [2.]*52, 'hybrid_status': 'Available',
                'sarima_status': 'Available', 'diagnostics': {}}
    monkeypatch.setattr(model, 'fit_models', fit)
    monkeypatch.setattr(selection, 'select_configuration', lambda *a: pytest.fail('Runtime must not search'))
    result = model.run(d, 'Measles', c, defer_evaluation=True)
    assert len(calls) == 1 and calls[0][:2] == (400, 52)
    assert len(result['forecast_index']) == len(result['hybrid']) == 52
    assert result['evaluation']['status'] == 'Pending'
    assert result['configuration'] == c


@pytest.mark.parametrize('failure', ['convergence', 'parameters', 'forecast'])
def test_sarima_rejects_invalid_fits(monkeypatch, failure):
    from types import SimpleNamespace
    class Fake:
        def __init__(self, *args, **kwargs):
            assert kwargs['initialization'] == 'approximate_diffuse'
            assert kwargs['loglikelihood_burn'] == 108
        def fit(self, **kwargs):
            return SimpleNamespace(mle_retvals={'converged': failure != 'convergence'},
                                   params=np.array([np.nan if failure == 'parameters' else 1.]),
                                   aic=10., llf=-4., forecast=lambda steps: np.full(steps, np.nan))
    monkeypatch.setattr(estimators, 'SARIMAX', Fake)
    with pytest.raises(ValueError):
        estimators.fit_sarima(np.ones(300), 52, selection.candidates()[0], selection.base_config())
