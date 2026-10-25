import copy
import json

import numpy as np
import pytest

from dashboard.weekly import model, provisional, selection
from dashboard.weekly.data import digest
from dashboard.weekly.result_schema import current_result
from tests.test_corrected_methodology import research_fixture


def provisional_fixture(monkeypatch, tmp_path):
    dataset, _ = research_fixture()
    dataset['metadata'].pop('population', None)
    dataset['metadata'].pop('case_classification', None)
    dataset['eligible'] = False
    original = copy.deepcopy(dataset)
    calls = []
    def select(training, validation, disease, periods, checkpoint=None, progress=None):
        assert len(training) == len(dataset['records']) - 104
        assert len(validation) == 52
        c = selection.base_config()
        candidate = selection.candidates()[0]
        metrics = selection.score_cases(validation, np.full(52, 2.))
        c.update(candidates=[candidate], nnar_lags=[1, 2, 3, 4], hidden_nodes=4, alpha=.1,
                 selection_status='locked', selection_run_id='selection-test', selection_timestamp='test',
                 periods=periods, selection_data_fingerprint=selection.selection_fingerprint(training, validation),
                 selection_diagnostics={'adf': {'status': 'unavailable'},
                   'sarima': {**candidate, 'validation': metrics, 'ljung_box': []},
                   'nnar': {'median_validation': {k: metrics[k] for k in ('rmse', 'mae', 'mape')},
                            'seeds': [{'seed': s, 'metrics': metrics} for s in (42, 137, 2026)]}})
        c['locked_configuration_id'] = digest(c)
        audit = {'sarima_candidates': [{'fit_status': 'available', 'shortlisted': True}],
                 'nnar_candidates': [{'status': 'available'}]}
        checkpoint(audit)
        return c, audit
    def fit(values, steps, config, progress=None):
        lock = json.loads((tmp_path / 'locked.json').read_text())
        assert lock == config  # Lock is persisted before either test or future refit.
        selection.verify_lock(lock)
        calls.append(len(values))
        return {'hybrid': [3.] * 52, 'sarima': [2.] * 52, 'range': None,
                'hybrid_status': 'Available', 'sarima_status': 'Available', 'diagnostics': {},
                'components': {'raw_sarima': [2.] * 52, 'nnar_correction': [1.] * 52, 'hybrid': [3.] * 52}}
    monkeypatch.setattr(selection, 'select_configuration', select)
    monkeypatch.setattr(model, 'fit_models', fit)
    events = []
    result = provisional.run_provisional(dataset, 'Measles', tmp_path, lambda *e: events.append(e))
    assert dataset == original
    assert calls == [len(dataset['records']) - 52, len(dataset['records'])]
    return dataset, result, events


def test_provisional_locks_before_test_then_refits_all_history(monkeypatch, tmp_path):
    dataset, result, events = provisional_fixture(monkeypatch, tmp_path)
    assert result['configuration']['research_validated'] is False
    assert result['configuration']['status'] == 'PROVISIONAL'
    assert result['configuration']['nnar_lags'] == [1, 2, 3, 4]
    assert len(result['hybrid']) == len(result['forecast_index']) == 52
    assert result['evaluation']['configuration_hash_before'] == result['evaluation']['configuration_hash_after']
    assert result['metrics']['sarima']['n'] == result['metrics']['hybrid']['n']
    assert [e[0] for e in events].index('lock') < [e[0] for e in events].index('refit')
    assert [e[0] for e in events].index('test') < [e[0] for e in events].index('future_refit')
    report = json.loads((tmp_path / 'report.json').read_text(encoding='utf-8'))
    assert report['title'].endswith('Not Thesis-Validated')
    assert report['dataset_fingerprint'] == result['dataset_fingerprint']
    assert current_result(result) == result
    # Even eligible data cannot promote this signed provisional lock to research.
    dataset['eligible'] = True
    rejected = model.run(dataset, 'Measles', result['configuration'])
    assert 'provisional configuration cannot' in rejected['failure_reason']


def test_components_are_raw_and_clipping_is_explicit(monkeypatch):
    from dashboard.weekly.sample import sample_configuration
    monkeypatch.setattr(model, 'fit_sarima', lambda *a: (np.array([-2., 3.]), np.zeros(200), {}))
    monkeypatch.setattr(model, 'nnar', lambda *a: (np.array([1., -1.]), []))
    result = model.fit_models(np.arange(300.), 2, sample_configuration())
    assert result['sarima'] == [0., 3.]
    assert result['components']['raw_sarima'] == [-2., 3.]
    assert result['hybrid'] == [0., 2.]


def test_shape_directions_do_not_bridge_missing_and_peaks_use_common_mask():
    actual = [0, 10, None, 100, 20]
    predicted = {'sarima': [0, 8, 999, 60, 10], 'hybrid': [0, 8, 999, 5, 10]}
    d = provisional.shape_diagnostics(actual, predicted, [[2025, i] for i in range(1, 6)])
    assert d['actual_peak']['position'] == 4
    assert d['models']['sarima']['peak_position'] == 4
    assert d['models']['sarima']['direction_pairs_scored'] == 2
    assert d['models']['sarima']['directional_agreement_rate'] == 1
    assert d['models']['hybrid']['directional_agreement_rate'] == .5
    assert d['models']['hybrid']['missed_surge']


def test_provisional_graphs_export_and_components(monkeypatch, tmp_path):
    from dashboard.weekly import provisional_ui, ui
    dataset, result, _ = provisional_fixture(monkeypatch, tmp_path)
    figures = provisional_ui.comparison_figures(result)
    assert len(figures[0].data) == 3
    assert all(len(t.x) == 52 for t in figures[0].data)
    assert len(provisional_ui.component_rows(result)) == 104
    assert all(figure.layout.xaxis.nticks == 12 for figure in figures)
    panel = provisional_ui.panel(result)
    assert panel is not None
    download = ui.export_provisional_report(1, dataset, 'Measles', {'Measles': result})
    from dash import no_update
    for clicks in (None, 0):
        assert ui.export_provisional_report(clicks, dataset, 'Measles', {'Measles': result}) is no_update
    report = json.loads(download['content'])
    assert report['components'] == result['components']
    assert report['configuration']['status'] == 'PROVISIONAL'
    rendered = ui.render('Forecast', dataset, 'Measles', {'Measles': result}, 13, 'Weekly')
    assert 'Not Thesis-Validated' in rendered[1]
    from dashboard.weekly.outputs import export_frame
    exported = export_frame(dataset, result)
    assert exported['provisional_validation'].all()
    assert not exported['research_validated'].any()


def test_invalid_structure_and_synthetic_demo_cannot_enter_search(monkeypatch, tmp_path):
    from dashboard.weekly.data import demo
    with pytest.raises(ValueError, match='uploaded dataset'):
        provisional.run_provisional(demo(), 'Dengue', tmp_path)
    dataset, _ = research_fixture()
    dataset['records'].append(copy.deepcopy(dataset['records'][0]))
    with pytest.raises(ValueError, match='validation errors'):
        provisional.run_provisional(dataset, 'Measles', tmp_path)


def test_minimum_observed_training_enforced_before_search():
    with pytest.raises(ValueError, match='156 observed'):
        selection.select_configuration(np.full(300, np.nan), np.ones(52), 'Dengue', {})


def test_final_test_failure_retains_lock_and_stops_before_future(monkeypatch, tmp_path):
    dataset, _, _ = provisional_fixture(monkeypatch, tmp_path)
    def fail(*args, **kwargs):
        raise ValueError('Terminal residual lag window contains missing observations.')
    monkeypatch.setattr(model, 'retrospective_evaluation', fail)
    def forbidden(*args, **kwargs):
        pytest.fail('Future forecasting must not run after failed Final Test.')
    monkeypatch.setattr(model, 'fit_models', forbidden)
    target = tmp_path / 'failed'
    with pytest.raises(ValueError, match='Provisional Final Test blocked'):
        provisional.run_provisional(dataset, 'Measles', target)
    assert (target / 'locked.json').exists()
    assert (target / 'search.json').exists()
    failure = json.loads((target / 'failure.json').read_text(encoding='utf-8'))
    assert failure['status'] == 'failed' and not failure['research_validated']
    assert not (target / 'result.json').exists()
