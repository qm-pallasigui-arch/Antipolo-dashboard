"""Deterministic orchestration evidence; fabricated data, not accuracy results."""
import copy
import json
from types import SimpleNamespace

import pytest

from dashboard.weekly import model, selection, workflow, ui, jobs
from dashboard.weekly.data import demo, digest
from tests.test_corrected_methodology import research_fixture, wait_job


@pytest.fixture
def research(monkeypatch, tmp_path):
    dataset, c = research_fixture()
    c['disease'] = 'Measles'
    c['locked_configuration_id'] = digest({k: v for k, v in c.items() if k != 'locked_configuration_id'})
    monkeypatch.setattr(workflow, 'ROOT', tmp_path)
    monkeypatch.setattr(workflow.settings, 'model_configuration', lambda: {'configurations': {'Measles': c}})
    fits = []
    def fit(values, steps, config, progress=None):
        fits.append(len(values))
        return {'hybrid': [3.] * steps, 'sarima': [2.] * steps, 'range': None,
                'hybrid_status': 'Available', 'sarima_status': 'Available', 'diagnostics': {},
                'components': {'raw_sarima': [2.] * steps, 'nnar_correction': [1.] * steps, 'hybrid': [3.] * steps}}
    monkeypatch.setattr(model, 'fit_models', fit)
    return dataset, c, fits


def test_research_reuses_performance_and_slices_original_window(research):
    dataset, c, fits = research
    original = copy.deepcopy(c)
    first = workflow.run_guided_forecast(dataset, 'Measles')
    assert fits == [348, 400]
    assert not first['performance_reused']
    assert 'Approval Pending' in first['context'] and not first['research_validated']
    second = workflow.run_guided_forecast(dataset, 'Measles')
    assert fits == [348, 400, 400] and second['performance_reused']
    # Append four weeks: retain original test window and refit all 404 positions.
    for i in range(400, 404):
        row = copy.deepcopy(dataset['records'][-1])
        row.update(year=2016 + i // 52, morbidity_week=i % 52 + 1, case_count=15)
        dataset['records'].append(row)
    dataset['id'] = 'new-upload-id'
    third = workflow.run_guided_forecast(dataset, 'Measles')
    assert third['performance_reused'] and fits[-1] == 404
    assert third['evaluation']['index'] == first['evaluation']['index']
    assert third['metrics'] == first['metrics']
    assert c == original


def test_revised_test_recomputes_but_training_change_stops(research):
    dataset, _, fits = research
    first = workflow.run_guided_forecast(dataset, 'Measles')
    dataset['records'][-1]['case_count'] += 100
    second = workflow.run_guided_forecast(dataset, 'Measles')
    assert not second['performance_reused']
    assert second['performance_provenance']['test_outcomes_revised']
    assert first['metrics'] != second['metrics']
    assert fits == [348, 400, 348, 400]
    dataset['records'][10]['case_count'] += 1
    with pytest.raises(ValueError, match='Training or validation data changed'):
        workflow.run_guided_forecast(dataset, 'Measles')
    assert len(fits) == 4


def test_preparation_change_stops_without_future_fit(research):
    dataset, _, fits = research
    workflow.run_guided_forecast(dataset, 'Measles')
    dataset['metadata']['calendar_rule'] = 'different rule'
    with pytest.raises(ValueError, match='preparation rules changed'):
        workflow.run_guided_forecast(dataset, 'Measles')
    assert fits == [348, 400]


def test_legacy_metrics_not_reused_and_version_invalid(research, monkeypatch):
    dataset, c, fits = research
    first = workflow.run_guided_forecast(dataset, 'Measles')
    _, root, _ = workflow.resolve_lock(dataset, 'Measles')
    path = root / 'performance' / (first['performance_provenance']['compatibility_key'] + '.json')
    path.write_text(json.dumps({'result': first, 'status': 'complete'}))
    workflow.run_guided_forecast(dataset, 'Measles')
    assert fits == [348, 400, 348, 400]
    c['version'] = 'old-model'
    c['locked_configuration_id'] = digest({k: v for k, v in c.items() if k != 'locked_configuration_id'})
    with pytest.raises(ValueError, match='integrity checks'):
        workflow.run_guided_forecast(dataset, 'Measles')


def test_ineligible_routes_provisional_and_invalid_config_never_falls_back(research, monkeypatch):
    dataset, c, fits = research
    dataset['eligible'] = False
    called = []
    monkeypatch.setattr(workflow, 'run_provisional', lambda *a, **k: called.append(True) or {})
    assert workflow.run_guided_forecast(dataset, 'Measles')['workflow_mode'] == 'provisional'
    assert called == [True] and not fits
    c['alpha'] = 999
    with pytest.raises(ValueError, match='integrity checks'):
        workflow.run_guided_forecast(dataset, 'Measles')
    assert called == [True]


def test_missing_registry_selects_then_retries_failed_evaluation_without_reselection(research, monkeypatch):
    dataset, c, fits = research
    monkeypatch.setattr(workflow.settings, 'model_configuration', lambda: {'configurations': {}})
    selections = []
    def select(train, val, disease, periods, checkpoint=None, progress=None):
        selections.append((len(train), len(val)))
        return copy.deepcopy(c), {'sarima_candidates': [], 'nnar_candidates': []}
    monkeypatch.setattr(selection, 'select_configuration', select)
    original_fit = model.fit_models
    def fail(*args, **kwargs):
        return {'hybrid': None, 'failure_reason': 'Terminal residual lag window contains missing observations.'}
    monkeypatch.setattr(model, 'fit_models', fail)
    with pytest.raises(ValueError, match='Terminal residual'):
        workflow.run_guided_forecast(dataset, 'Measles')
    saved, root, origin = workflow.resolve_lock(dataset, 'Measles')
    assert origin == 'runtime' and (root / 'snapshot.json').exists()
    assert not (root / 'results').exists()
    assert saved['approved'] is False
    monkeypatch.setattr(model, 'fit_models', original_fit)
    result = workflow.run_guided_forecast(dataset, 'Measles')
    assert len(selections) == 1 and len(result['hybrid']) == 52
    assert fits == [348, 400]
    assert list((root / 'attempts').glob('*.json'))


def test_synthetic_preview_only_and_provisional_failure_not_substituted(research, monkeypatch):
    dataset, _, fits = research
    with pytest.raises(ValueError, match='Synthetic data requires'):
        workflow.run_guided_forecast(demo(), 'Dengue')
    assert ui.disable_guided_action(0, None, demo(), 'Dengue')
    dataset['eligible'] = False
    def fail(*args, **kwargs):
        raise ValueError('Provisional Final Test blocked')
    monkeypatch.setattr(workflow, 'run_provisional', fail)
    with pytest.raises(ValueError, match='Provisional Final Test blocked'):
        workflow.run_guided_forecast(dataset, 'Measles')
    assert not fits


def test_job_catches_registry_failure_and_keeps_previous_output(research, monkeypatch, tmp_path):
    dataset, _, _ = research
    monkeypatch.setattr(jobs, 'ROOT', tmp_path / 'jobs')
    def invalid():
        raise ValueError('bad configuration')
    monkeypatch.setattr(workflow.settings, 'model_configuration', invalid)
    monkeypatch.setattr(ui, 'ctx', SimpleNamespace(triggered_id='w-run'))
    previous = {'Measles': {'dataset_id': dataset['id'], 'disease': 'Measles', 'hybrid': [1.] * 52}}
    job = ui.start_guided_job(1, dataset, 'Measles', previous, None)
    done = wait_job(job['run_id'])
    assert done['status'] == 'failed' and 'integrity checks' in done['failure_reason']
    from dash import no_update
    assert ui.poll_model_job(0, job, dataset, 'Measles', previous)[0] is no_update
    assert previous['Measles']['hybrid'] == [1.] * 52


def test_results_have_performance_diagnostics_and_preserve_lock(research):
    dataset, _, fits = research
    result = workflow.run_guided_forecast(dataset, 'Measles')
    from plotly.utils import PlotlyJSONEncoder
    before = len(fits)
    for horizon in (4, 13, 26, 52):
        content = ui.render('Forecast', dataset, 'Measles', {'Measles': result}, horizon, 'Weekly')[0]
        labels = json.dumps(content, cls=PlotlyJSONEncoder)
        for text in ('Future Forecast', 'Model Performance', 'Diagnostics', 'Download Methodology Report', 'Forecast Components'):
            assert text in labels
    assert len(fits) == before


def test_unchanged_workbook_week53_still_blocks_nnar_initialization():
    import base64
    from pathlib import Path
    import numpy as np
    from dashboard.weekly.transform import prepare, read_source
    from dashboard.weekly.sample import prepare_uploaded
    from dashboard.weekly.estimators import nnar
    path = Path(__file__).resolve().parents[1] / 'Antipolo_Disease_Surveillance_2016-2025.xlsx'
    dataset = prepare(read_source('data:application/octet-stream;base64,' + base64.b64encode(path.read_bytes()).decode(), path.name))
    prepared, _ = prepare_uploaded(dataset, 'Provisional')
    values, index = model.training_series(prepared, 'Dengue')
    assert index[-54] == (2024, 53) and np.isnan(values[-54])
    # Missing residual positions follow observed-count gaps; no numerical grid rerun required.
    residuals = np.where(np.isfinite(values[:-52]), 0., np.nan)
    residuals[:108] = np.nan
    with pytest.raises(ValueError, match='Terminal residual lag window'):
        nnar(residuals, 52, selection.base_config())


def test_explicit_null_configuration_is_malformed_not_missing(research, monkeypatch):
    dataset, _, fits = research
    monkeypatch.setattr(workflow.settings, 'model_configuration', lambda: {'configurations': {'Measles': None}})
    with pytest.raises(ValueError, match='integrity checks'):
        workflow.run_guided_forecast(dataset, 'Measles')
    assert not fits


def test_future_failure_retains_completed_performance_for_retry(research, monkeypatch):
    dataset, _, fits = research
    fit = model.fit_models
    def fail_future(values, *args, **kwargs):
        if len(values) == 400:
            return {'hybrid': None, 'failure_reason': 'SARIMA optimizer did not converge.'}
        return fit(values, *args, **kwargs)
    monkeypatch.setattr(model, 'fit_models', fail_future)
    with pytest.raises(ValueError, match='SARIMA optimizer'):
        workflow.run_guided_forecast(dataset, 'Measles')
    _, root, _ = workflow.resolve_lock(dataset, 'Measles')
    state = json.loads(next((root / 'attempts').glob('*.json')).read_text())
    assert state['evaluation'] == 'complete' and state['forecast'] == 'pending'
    monkeypatch.setattr(model, 'fit_models', fit)
    assert workflow.run_guided_forecast(dataset, 'Measles')['performance_reused']
    assert fits == [348, 400]
