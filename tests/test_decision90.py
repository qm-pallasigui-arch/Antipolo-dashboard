"""Decision 90 building-block contracts, independent of expensive grid execution."""
import numpy as np
import pytest

from dashboard.weekly import selection as s
from dashboard.weekly import evaluation as e
from dashboard.weekly import model, outputs, ui
from dashboard.weekly.charts import forecast_chart
from tests.test_weekly import dataset


def test_exact_grid_and_configuration_isolation():
    c = s.approved_configuration()
    assert len(c['candidates']) == 144
    assert len({str(x) for x in c['candidates']}) == 144
    assert all(x['seasonal_order'][-1] == 52 for x in c['candidates'])
    assert c['lag_windows'] == [3, 6, 12, 26, 52]
    assert c['hidden_nodes_grid'] == [2, 3, 5, 8]
    c['candidates'].clear()
    assert len(s.approved_configuration()['candidates']) == 144


def test_fixed_expanding_splits():
    windows, holdout = s.evaluation_splits(364)
    assert windows == [(156, 208), (208, 260), (260, 312)]
    assert holdout == (312, 364)
    with pytest.raises(ValueError, match='insufficient initial'):
        s.evaluation_splits(363)


def test_shortlist_bounds_and_invalid_candidates():
    def record(aic, status='available'):
        return dict(aic=aic, status=status, order=[0, 0, 0], seasonal_order=[0, 0, 0, 52])
    assert len(s.shortlist([record(i * 10) for i in range(8)])) == 3
    assert len(s.shortlist([record(i / 10) for i in range(8)])) == 5
    assert len(s.shortlist([record(1), record(2), record(-100, 'unavailable')])) == 2
    assert s.shortlist([record(float('nan'))]) == []


def test_shared_scoring_clips_and_preserves_zero_missing():
    actual = np.array([0., 2., np.nan, 4.])
    result = s.score(actual, {'hybrid': [-10, 2, 0, 4], 'sarima': [1, 3, 0, 4]})
    assert result['metrics']['hybrid']['rmse'] == 0
    assert result['scored_weeks'] == 3
    assert result['excluded_missing_actuals'] == 1
    assert result['mape_n'] == 2 and result['mape_zero_excluded'] == 1
    assert all(m['n'] == 3 for m in result['metrics'].values())
    assert actual[0] == 0 and np.isnan(actual[2])
    assert 'wape' not in result['metrics']['hybrid']
    with pytest.raises(ValueError, match='finite predictions'):
        s.score(actual, {'hybrid': [0, np.nan, 0, 4]})


def test_residual_windows_do_not_compress_gaps():
    X, y, audit = s.residual_windows([0, 1, 2, np.nan, 4, 5, 6, 7], 3)
    assert X.tolist() == [[6, 5, 4]] and y.tolist() == [7]
    assert audit == dict(candidate_windows=5, complete_windows=1, excluded_incomplete_windows=4)
    path, evidence = s.fit_nnar(np.arange(54.), 52, 3, 2, s.approved_configuration())
    assert path is None and evidence['complete_windows'] == 51


def test_nnar_five_logistic_fits_best_loss_and_signed_recursion(monkeypatch):
    seeds = []
    class Network:
        def __init__(self, **kwargs):
            assert kwargs['activation'] == 'logistic'
            self.seed = kwargs['random_state']
            seeds.append(self.seed)
        def fit(self, X, y):
            self.loss_ = abs(self.seed - 44)
        def predict(self, X):
            return np.array([-2.])
    monkeypatch.setattr(s, 'MLPRegressor', Network)
    path, audit = s.fit_nnar(np.arange(100.), 52, 3, 2, s.approved_configuration())
    assert seeds == [42, 43, 44, 45, 46]
    assert audit['selected_seed'] == 44 and audit['output_activation'] == 'identity'
    assert len(path) == 52 and np.all(path == -2)


def test_equal_window_means_rank_and_simplicity():
    rows = [dict(lag_window=lag, hidden_nodes=nodes,
                 window_metrics=[dict(rmse=x, mae=x, mape=x) for x in [1, 2, 6]])
            for lag, nodes in [(6, 3), (3, 2)]]
    ranked = s.rank_candidates(rows, hybrid=True)
    assert ranked[0]['lag_window'] == 3
    assert ranked[0]['mean_metrics']['rmse'] == 3
    assert ranked[0]['average_rank'] == 1.5


def test_sarima_failure_is_recorded(monkeypatch):
    def fail(*args, **kwargs):
        raise ValueError('fixture fitting failure')
    monkeypatch.setattr(s, 'SARIMAX', fail)
    c = s.approved_configuration()
    path, residuals, evidence = s.fit_sarima(np.arange(156.), 52, c['candidates'][0], c)
    assert path is residuals is None
    assert evidence['status'] == 'unavailable' and 'fixture fitting failure' in evidence['reason']
    assert s.shortlist([evidence]) == []


def test_chart_ignores_legacy_uncertainty_and_slices_one_path():
    active = dataset()
    result = {'hybrid': list(range(52)), 'sarima': list(range(52)),
              'forecast_index': [dict(year=2026, morbidity_week=i + 1) for i in range(52)],
              'range': {'lower': [0] * 52, 'upper': [100] * 52}}
    for horizon in (4, 13, 26, 52):
        figure = forecast_chart(active, 'Measles', result, horizon)
        assert len(figure.data) == 3
        assert list(figure.data[-2].y) == list(range(horizon))
        assert all(trace.fill is None for trace in figure.data)


@pytest.mark.parametrize('applicable', [0, 1, 2, 3])
def test_mape_averages_only_applicable_windows(applicable):
    windows = [dict(rmse=2, mae=1, mape=10 * (i + 1) if i < applicable else None,
                    mape_n=5 if i < applicable else 0, mape_zero_excluded=47 if i < applicable else 52)
               for i in range(3)]
    row = dict(order=[0, 0, 0], seasonal_order=[0, 0, 0, 52], aic=1, window_metrics=windows)
    winner = s.rank_candidates([row])[0]
    assert winner['mape_window_count'] == applicable
    assert winner['mape_observation_count'] == 5 * applicable
    assert winner['mape_selection_unavailable'] == (applicable == 0)
    assert winner['ranking_metrics'] == ['rmse', 'mae'] + (['mape'] if applicable else [])
    assert winner['mean_metrics']['mape'] == (5 * (applicable + 1) if applicable else None)


def fake_models(monkeypatch, fail_candidate=None, fail_hybrid=False, fail_operational=False):
    c = s.approved_configuration()
    keys = {e.candidate_key(candidate): i for i, candidate in enumerate(c['candidates'])}
    calls, nnar_calls = [], []
    def sarima(values, steps, candidate, config):
        number = keys[e.candidate_key(candidate)]
        cutoff = len(values)
        calls.append((cutoff, number, values.copy()))
        window = {156: 0, 208: 1, 260: 2}.get(cutoff, 0)
        # Each screening window chooses a different group of three candidates.
        aic = float(((number - 3 * window) % 144) * 10)
        record = {**candidate, 'aic': aic, 'status': 'available'}
        if (number == fail_candidate and cutoff == 208) or (fail_operational and cutoff == 364):
            return None, None, {**record, 'status': 'unavailable', 'reason': 'fixture failure'}
        return np.full(steps, number + 1.), np.full(cutoff, float(cutoff)), record
    def nnar(residuals, steps, lag, nodes, config):
        nnar_calls.append((len(residuals), float(residuals[-1]), lag, nodes))
        evidence = dict(complete_windows=len(residuals) - lag, excluded_incomplete_windows=0)
        if fail_hybrid:
            return None, {**evidence, 'reason': 'insufficient complete NNAR residual windows'}
        return np.full(steps, -2.), evidence
    monkeypatch.setattr(s, 'fit_sarima', sarima)
    monkeypatch.setattr(s, 'fit_nnar', nnar)
    return c, calls, nnar_calls


def chronology(n=364):
    return [(2019 + i // 52, i % 52 + 1) for i in range(n)]


def test_union_refits_every_candidate_every_cutoff_and_excludes_failure(monkeypatch):
    c, calls, nnar_calls = fake_models(monkeypatch, fail_candidate=5)
    locked, audit = e.select(np.ones(312), c, [(156, 208), (208, 260), (260, 312)])
    # Failure during screening makes candidate 6 enter the second-window shortlist.
    union = {e.candidate_key(r): r for r in c['candidates'][:9]}
    assert set(audit['union']) == set(union) - {e.candidate_key(c['candidates'][5])}
    assert len(calls) == 3 * 144 + 3 * len(audit['union'])
    assert locked['sarima']['order'] == c['candidates'][0]['order']
    assert locked['sarima']['seasonal_order'] == c['candidates'][0]['seasonal_order']
    assert all(cutoff == residual_marker for cutoff, residual_marker, _, _ in nnar_calls)
    assert all(len(r['windows']) == 3 for r in audit['sarima_candidates'])


def test_candidate_in_union_but_failed_refit_cannot_rank(monkeypatch):
    c, _, _ = fake_models(monkeypatch)
    original = s.fit_sarima
    counts = {}
    def fail_on_refit(values, steps, candidate, config):
        key = (len(values), e.candidate_key(candidate))
        counts[key] = counts.get(key, 0) + 1
        if candidate == c['candidates'][0] and len(values) == 208 and counts[key] == 2:
            return None, None, {**candidate, 'status': 'unavailable', 'reason': 'refit failed', 'aic': None}
        return original(values, steps, candidate, config)
    monkeypatch.setattr(s, 'fit_sarima', fail_on_refit)
    _, audit = e.select(np.ones(312), c, [(156, 208), (208, 260), (260, 312)])
    key = e.candidate_key(c['candidates'][0])
    assert key in audit['union']
    assert all(r['candidate_id'] != key for r in audit['sarima_ranking'])
    assert all(r['candidate_id'] != key for r in audit['hybrid_ranking'])


def test_locked_pipeline_holdout_isolation_raw_clipping_and_operational_refit(monkeypatch):
    c, calls, _ = fake_models(monkeypatch)
    values = np.ones(364)
    values[-52:] = 900
    result = e.execute(values, chronology(), c)
    assert all(900 not in values for cutoff, _, values in calls if cutoff < 364)
    assert any(cutoff == 312 for cutoff, _, _ in calls)
    assert any(cutoff == 364 for cutoff, _, _ in calls)
    assert result['selection']['locked_configuration'] == result['locked_configuration']
    assert result['evaluation']['predictions']['raw_residual_forecast'] == [-2.] * 52
    assert result['hybrid'] == np.maximum(0, np.array(result['raw_hybrid_base']) - 2).tolist()
    assert len(result['hybrid']) == len(result['sarima']) == 52
    assert result['metrics'] == result['horizon_metrics']['52']['metrics']
    original_lock = result['locked_configuration']
    values[-52:] = 0
    changed = e.execute(values, chronology(), c)
    assert changed['locked_configuration'] == original_lock
    assert changed['evaluation']['predictions'] == result['evaluation']['predictions']
    assert changed['metrics'] != result['metrics']


def test_all_zero_validation_keeps_formal_selection(monkeypatch):
    c, _, _ = fake_models(monkeypatch)
    result = e.execute(np.zeros(364), chronology(), c)
    assert result['hybrid'] is not None
    for selected in result['locked_configuration'].values():
        assert selected['ranking_metrics'] == ['rmse', 'mae']
        assert selected['mape_selection_unavailable']
    assert any('MAPE was unavailable' in w for w in result['protocol_warnings'])


def test_operational_failure_preserves_retrospective_metrics_and_lock(monkeypatch):
    c, _, _ = fake_models(monkeypatch, fail_operational=True)
    result = e.execute(np.ones(364), chronology(), c)
    assert result['hybrid'] is result['sarima'] is None
    assert result['metrics']['hybrid'] is not None and result['metrics']['sarima'] is not None
    assert result['evaluation']['hybrid_status'] == 'Available'
    assert result['locked_configuration']['hybrid'] is not None


def test_hybrid_failure_keeps_sarima_explicitly_separate(monkeypatch):
    c, _, _ = fake_models(monkeypatch, fail_hybrid=True)
    result = e.execute(np.ones(364), chronology(), c)
    assert result['hybrid'] is None and result['sarima'] is not None
    assert result['hybrid_status'] == 'Hybrid unavailable'
    assert result['metrics']['hybrid'] is None
    assert result['metrics']['sarima'] is not None


def test_end_to_end_active_dataset_audit_and_strict_json(monkeypatch):
    import json
    c, _, _ = fake_models(monkeypatch)
    active = dataset([dict(disease='Measles', year=y, morbidity_week=w, case_count=1)
                      for y, w in chronology()], year_lengths={str(y): 52 for y in range(2019, 2028)})
    result = model.run(active, 'Measles', c)
    assert len(result['hybrid']) == 52, result.get('failure_reason')
    assert result['model_version'] == model.VERSION
    assert result['cache_key'] == model.cache_key(active, 'Measles', c)
    exported = json.loads(outputs.technical_export(active, result))
    assert exported['model_run']['selection'] == result['selection']
    assert exported['model_run']['metrics']['hybrid']['mape_zero_excluded'] == 0
    assert 'range' not in result
    content = str(ui.render('About the Model', active, 'Measles', result, 4, 'Weekly')[-1])
    assert 'MAPE windows' in content and 'Training and evaluation coverage' in content


def test_insufficient_history_never_starts_grid(monkeypatch):
    monkeypatch.setattr(s, 'fit_sarima', lambda *args: pytest.fail('No fitting for insufficient history'))
    result = model.run(dataset(), 'Measles', s.approved_configuration())
    assert 'insufficient initial' in result['failure_reason']
    assert result['hybrid'] is None


def test_trailing_complete_blank_preserves_calendar_position():
    active = dataset([dict(disease='Measles', year=2025, morbidity_week=w, case_count=1 if w < 20 else None)
                      for w in range(1, 21)])
    values, index = model.training_series(active, 'Measles')
    assert index[-1] == (2025, 20) and np.isnan(values[-1])


def test_configuration_rejects_silent_protocol_changes():
    c = s.approved_configuration()
    c['lag_windows'] = [3]
    with pytest.raises(ValueError, match='fixed lag_windows'):
        s.validate_configuration(c)


def test_stale_model_version_and_mutated_dataset_are_hidden():
    active = dataset()
    c = s.approved_configuration()
    result = dict(dataset_id=active['id'], disease='Measles', model_version='weekly-2')
    assert not ui.result_matches(active, result)
    result.update(model_version=model.VERSION, cache_key=model.cache_key(active, 'Measles', c))
    assert ui.result_matches(active, result)
    active['records'][0]['case_count'] = 999
    assert not ui.result_matches(active, result)


def test_recursive_prediction_failure_is_recorded(monkeypatch):
    class BrokenPrediction:
        def __init__(self, **kwargs):
            self.loss_ = 1.
        def fit(self, X, y):
            return self
        def predict(self, X):
            raise ValueError('fixture prediction error')
    monkeypatch.setattr(s, 'MLPRegressor', BrokenPrediction)
    path, evidence = s.fit_nnar(np.arange(100.), 52, 3, 2, s.approved_configuration())
    assert path is None and 'fixture prediction error' in evidence['reason']


def test_recursive_predictions_feed_the_next_lag_and_remain_signed(monkeypatch):
    class IdentityScaler:
        def fit(self, X):
            return self
        def transform(self, X):
            return np.asarray(X)
    class Network:
        def __init__(self, **kwargs):
            self.loss_ = 1.
        def fit(self, X, y):
            return self
        def predict(self, X):
            return X[:, 0] - 1
    monkeypatch.setattr(s, 'StandardScaler', IdentityScaler)
    monkeypatch.setattr(s, 'MLPRegressor', Network)
    path, _ = s.fit_nnar(np.full(100, 5.), 52, 3, 2, s.approved_configuration())
    assert path.tolist() == list(range(4, -48, -1))


def test_stale_snapshot_is_rejected(monkeypatch):
    from types import SimpleNamespace
    monkeypatch.setattr(ui, 'ctx', SimpleNamespace(triggered_id='w-snapshot'))
    active = dataset()
    old = {'dataset_id': active['id'], 'model_version': 'weekly-2', 'hybrid': [1]}
    assert 'current dataset and model protocol' in str(ui.prospective(1, 0, active, old, None))


def test_sarima_rank_prefers_validation_over_aic():
    common = dict(order=[0, 0, 0], seasonal_order=[0, 0, 0, 52])
    rows = [{**common, 'aic': aic, 'window_metrics': [dict(rmse=error, mae=error, mape=error)] * 3}
            for aic, error in [(1, 10), (100, 1)]]
    assert s.rank_candidates(rows)[0]['aic'] == 100
