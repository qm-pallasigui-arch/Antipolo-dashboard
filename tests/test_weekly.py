"""Weekly research-integrity and operational acceptance contracts."""
import base64
import copy
import io
import subprocess
import sys
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from dashboard.weekly import data, model, outputs


def dataset(rows=None, **metadata):
    rows = rows if rows is not None else [
        {'disease': 'Measles', 'year': 2025, 'morbidity_week': w, 'case_count': w % 3}
        for w in range(1, 21)]
    meta = {'population': '5–19', 'case_classification': 'confirmed', 'location': 'Antipolo City',
            'source_system': 'CESU/PIDSAR', 'source_file': 'source.csv', 'provenance': 'CHO supplied; test fixture',
            'dataset_type': 'real', 'reporting_status': 'complete', 'year_lengths': {'2025': 52, '2026': 52},
            'approved_diseases': ['Measles', 'Measles-Rubella'],
            'weekly_protocol': {'approved': True, 'approval_reference': 'TEST ONLY', 'minimum_complete_weeks': 10}}
    return data.validate(pd.DataFrame(rows), {**meta, **metadata})


def protocol():
    return {**model.PENDING_CONFIG, 'version': 'test-only', 'candidates': [{'order': [0, 0, 0], 'seasonal_order': [0, 0, 0, 0], 'trend': 'c'}],
            'nnar_lags': [1, 2], 'hidden_nodes': 2, 'minimum_training_weeks': 8, 'minimum_residual_examples': 4,
            'residual_burn': 1, 'diagnostic_lag': 2, 'holdout_weeks': 4, 'nnar_maxiter': 2000}


def row(week, count=1, **extra):
    return {'disease': 'Measles', 'year': 2025, 'morbidity_week': week, 'case_count': count, **extra}


@pytest.mark.parametrize('week', [0, 54, -1, 1.5, 'x'])
def test_invalid_week(week):
    with pytest.raises(ValueError, match='morbidity_week'):
        dataset([row(week)])


@pytest.mark.parametrize('year', [0, 2025.5, 'x', None])
def test_invalid_year(year):
    with pytest.raises(ValueError, match='year'):
        dataset([row(1, year=year)])


@pytest.mark.parametrize('count', [-1, 'x', float('inf'), 1.2])
def test_invalid_counts(count):
    with pytest.raises(ValueError, match='Case counts'):
        dataset([row(1, count)])


def test_zero_blank_gap_and_no_imputation():
    d = dataset([row(1, 0), row(2, ''), row(4, 2)])
    assert [r['case_count'] for r in d['records']] == [0, None, 2]
    assert d['quality']['missing_weeks'] == [{'disease': 'Measles', 'year': 2025, 'morbidity_week': 3}]
    values, index = model.training_series(d, 'Measles')
    assert values[0] == 0 and np.isnan(values[1:3]).all() and values[-1] == 2
    assert index == [(2025, i) for i in range(1, 5)]
    assert not d['quality']['errors']


def test_week53_preserved_and_calendar_conflict():
    d = dataset([row(52), row(53, 7)], year_lengths={'2025': 53})
    assert d['records'][-1]['morbidity_week'] == 53
    assert d['records'][-1]['case_count'] == 7
    assert d['quality']['week53']
    conflicting = dataset([row(53)])
    assert conflicting['quality']['errors'] and conflicting['records'][0]['morbidity_week'] == 53


def test_duplicates_block_activation_without_modifying_current():
    current = dataset()
    before = copy.deepcopy(current)
    with pytest.raises(ValueError, match='validation'):
        data.activate(dataset([row(1), row(1)]), current)
    assert current == before


def test_distinct_labels_and_inconsistent_labels():
    d = dataset([row(1), row(1, disease='Measles-Rubella')])
    assert d['quality']['diseases'] == ['Measles', 'Measles-Rubella']
    assert dataset([row(1), row(2, disease='measles')])['quality']['errors']


@pytest.mark.parametrize('metadata', [
    {'population': 'all-age'}, {'case_classification': 'suspected'}, {'case_classification': 'probable'},
    {'case_classification': None}, {'source_system': 'FHSIS'}, {'provenance': None},
    {'approved_diseases': []}, {'weekly_protocol': {}}, {'location': None},
])
def test_technical_context_for_ineligible(metadata):
    d = dataset(**metadata)
    assert not d['eligible'] and d['context'] == data.TECHNICAL


def test_eligible_and_demo_separate():
    assert dataset()['eligible']
    assert dataset()['context'] == data.THESIS
    assert not data.demo()['eligible'] and data.demo()['context'] == data.DEMO
    mixed = dataset([row(1, dataset_type='synthetic'), row(2, dataset_type='real')])
    assert mixed['quality']['errors']


def test_row_metadata_conflict():
    assert not dataset([row(1, population='all-age')])['eligible']
    assert not dataset([row(1, case_classification='mixed')])['eligible']


@pytest.mark.parametrize('extension', ['csv', 'xlsx'])
def test_four_column_upload(extension):
    frame = pd.DataFrame([row(1, 0), row(2, '')])
    buffer = io.BytesIO()
    if extension == 'xlsx':
        frame.to_excel(buffer, index=False)
        raw = buffer.getvalue()
    else:
        raw = frame.to_csv(index=False).encode()
    contents = 'data:application/octet-stream;base64,' + base64.b64encode(raw).decode()
    parsed = data.parse_upload(contents, 'weekly.' + extension)
    d = data.validate(parsed)
    assert d['records'][0]['case_count'] == 0 and d['records'][1]['case_count'] is None
    assert not d['eligible']


def test_pdf_rejected():
    with pytest.raises(ValueError, match='CSV or XLSX'):
        data.parse_upload('data:;base64,' + base64.b64encode(b'pdf').decode(), 'source.pdf')


def test_activation_audit_and_pending_isolation():
    current, pending = dataset(), dataset(population='all-age')
    before = copy.deepcopy(current)
    result = data.activate(pending, current)
    assert current == before
    assert result['id'] == pending['id'] and result['context'] == data.TECHNICAL
    assert [r['event'] for r in result['audit']][-2:] == ['confirmed', 'activated']
    assert any(r['event'] == 'replaced' for r in result['audit'])
    assert [r['event'] for r in pending['audit']] == ['uploaded', 'validated']


def test_incomplete_and_unknown_reporting_excluded():
    d = dataset([row(1, 4), row(2, 900, reporting_status='incomplete')])
    values, index = model.training_series(d, 'Measles')
    assert list(values) == [4] and index[-1] == (2025, 1)
    assert d['records'][-1]['case_count'] == 900
    unknown = dataset(reporting_status='unknown')
    with pytest.raises(ValueError, match='No complete'):
        model.training_series(unknown, 'Measles')


def test_internal_incomplete_not_compressed():
    d = dataset([row(1), row(2, 100, reporting_status='incomplete'), row(3)])
    values, _ = model.training_series(d, 'Measles')
    assert len(values) == 3 and np.isnan(values[1])


def test_pending_model_explicitly_unavailable():
    result = model.run(dataset(), 'Measles', {})
    assert result['hybrid'] is None and result['sarima'] is None
    assert 'pending' in result['failure_reason']


def test_weekly_full_path_and_same_evaluation_period(monkeypatch):
    monkeypatch.setattr(model, 'nnar', lambda residuals, steps, c: (np.ones(steps), []))
    result = model.run(dataset(), 'Measles', protocol())
    assert len(result['hybrid']) == len(result['sarima']) == 52
    assert result['metrics']['hybrid']['n'] == result['metrics']['sarima']['n'] == 4
    assert result['evaluation']['period'] == [[2025, w] for w in range(17, 21)]
    assert result['hybrid'] != result['sarima']
    assert result['context'] == data.TECHNICAL  # unapproved protocol cannot be thesis evidence
    assert result['forecast_index'][0] == {'horizon_week': 1, 'year': 2025, 'morbidity_week': 21}


def test_real_nnar_weekly_path():
    d = data.demo()
    c = protocol()
    c['holdout_weeks'] = None
    c['nnar_maxiter'] = 5000
    result = model.run(d, 'Demo disease', c)
    assert result['hybrid_status'] == 'Available', result
    assert len(result['hybrid']) == 52


def test_hybrid_failure_keeps_separate_sarima(monkeypatch):
    def fail(*args):
        raise ValueError('test NNAR failure')
    monkeypatch.setattr(model, 'nnar', fail)
    result = model.run(dataset(), 'Measles', protocol())
    assert result['hybrid'] is None and result['hybrid_status'] == 'Hybrid unavailable'
    assert len(result['sarima']) == 52
    assert result['metrics']['hybrid'] is None
    assert 'NNAR failed' in result['failure_reason']


def test_gap_forecast_allowed_without_zero_fill(monkeypatch):
    monkeypatch.setattr(model, 'nnar', lambda residuals, steps, c: (np.zeros(steps), []))
    d = dataset([row(i, i % 3) for i in range(1, 21) if i != 7])
    result = model.run(d, 'Measles', protocol())
    assert len(result['sarima']) == 52 and result['training_observed_count'] == 19
    assert any('Missing weeks' in w for w in result['warnings'])
    assert len(d['records']) == 19


def test_nnar_never_compresses_gap():
    c = protocol()
    c['minimum_residual_examples'] = 100
    with pytest.raises(ValueError, match='complete residual lag windows'):
        model.nnar(np.array([1, 2, np.nan, 3, 4, 5, 6]), 52, c)


@pytest.mark.parametrize('field,value', [('population', 'all-age'), ('case_classification', 'mixed'), ('frequency', 'monthly'), ('source_system', 'different')])
def test_cache_isolation_metadata(field, value):
    d = dataset()
    changed = copy.deepcopy(d)
    changed['metadata'][field] = value
    assert model.cache_key(d, 'Measles', {}) != model.cache_key(changed, 'Measles', {})


def test_cache_isolation_data_disease_and_version():
    d = dataset()
    assert model.cache_key(d, 'Measles', {}) != model.cache_key(d, 'Measles-Rubella', {})
    assert model.cache_key(d, 'Measles', {'version': 1}) != model.cache_key(d, 'Measles', {'version': 2})
    changed = copy.deepcopy(d)
    changed['records'][0]['case_count'] = 99
    assert model.cache_key(d, 'Measles', {}) != model.cache_key(changed, 'Measles', {})


def test_metrics_zero_handling():
    metrics = model.compute_metrics([0, 0], [0, 1])
    assert metrics['mape'] is None and 'wape' not in metrics and metrics['mae'] == .5
    mixed = model.compute_metrics([0, 2], [1, 2])
    assert mixed['mape_n'] == 1 and mixed['mae'] == .5 and 'wape' not in mixed


def test_export_provenance_and_failure():
    d = dataset()
    result = model.run(d, 'Measles', {})
    frame = outputs.export_frame(d, result)
    assert {'year', 'morbidity_week', 'population', 'case_classification', 'source', 'dataset_id', 'hybrid_status', 'model_configuration', 'evaluation_metrics', 'provenance'} <= set(frame.columns)
    assert set(frame.hybrid_status) == {'Hybrid unavailable'}
    assert set(frame.context) == {data.TECHNICAL}  # Pending model protocols cannot produce thesis evidence.


def test_snapshot_revisions_do_not_overwrite_original(tmp_path, monkeypatch):
    monkeypatch.setattr(model, 'nnar', lambda residuals, steps, c: (np.zeros(steps), []))
    d = dataset()
    result = model.run(d, 'Measles', protocol())
    identifier = outputs.save_snapshot(d, result, tmp_path)
    original = (tmp_path / f'{identifier}.json').read_bytes()
    observations = dataset([row(21, 8)])
    first = outputs.reconcile(identifier, observations, tmp_path)
    second = outputs.reconcile(identifier, dataset([row(21, 9)]), tmp_path)
    assert first['horizon_specific_results'][0]['observed'] == 8
    assert second['horizon_specific_results'][0]['observed'] == 9
    assert (tmp_path / f'{identifier}.json').read_bytes() == original
    assert len(list(tmp_path.glob('*.revision-*.json'))) == 2
    with pytest.raises(ValueError, match='context mismatch'):
        outputs.reconcile(identifier, dataset(population='all-age'), tmp_path)
    with pytest.raises(ValueError, match='row context mismatch'):
        outputs.reconcile(identifier, dataset([row(21, 8, population='all-age')]), tmp_path)


def test_aggregation_requires_source_calendar_and_does_not_mutate():
    d = dataset()
    original = copy.deepcopy(d)
    with pytest.raises(ValueError, match='week_start_date'):
        outputs.historical_summary(d, 'Measles', 'Monthly')
    assert d == original
    d = dataset([row(1, 2, week_start_date='2025-01-01'), row(2, '', week_start_date='2025-01-08')])
    assert outputs.historical_summary(d, 'Measles', 'Monthly')[1] == [None]


def test_operational_layout_and_forecast_controls():
    import app
    from dashboard.weekly import ui
    client = app.server.test_client()
    assert client.get('/healthz').status_code == 200
    response = client.get('/_dash-layout')
    assert response.status_code == 200
    text = response.get_data(as_text=True)
    for page in ui.PAGES:
        assert page in text
    assert 'Confirm & Use Data' in text
    assert '32.22' not in text and 'seasonal-naive' not in text.lower()
    callback = app.dash_app.callback_map['w-result.data']
    assert 'w-horizon' not in [x['id'] for x in callback['inputs']]
    assert 'w-aggregation' not in [x['id'] for x in callback['inputs']]
    for page in ui.PAGES:
        rendered = ui.render(page, dataset(), 'Measles', None, 13, 'Weekly')
        assert len(rendered) == 7


def test_cautious_interpretation():
    result = {'hybrid': [1, 3], 'context': data.DEMO, 'forecast_index': [{'year': 2025, 'morbidity_week': 1}, {'year': 2025, 'morbidity_week': 2}]}
    text = model.interpretation(result, 2)
    assert 'projected' in text and 'Demo' in text and 'model-based' in text
    assert 'outbreak' not in text


def test_fresh_process_registers_only_weekly_callbacks():
    script = "import app; assert 'w-result.data' in app.dash_app.callback_map; assert all('w-' in key for key in app.dash_app.callback_map)"
    subprocess.run([sys.executable, '-c', script], check=True, capture_output=True, text=True)


def test_metadata_can_be_established_per_row():
    frame = pd.DataFrame([row(i, population='5-19', case_classification='confirmed',
                              source_system='CESU/PIDSAR', reporting_status='complete') for i in range(1, 21)])
    d = data.validate(frame, {'location': 'Antipolo City', 'dataset_type': 'real', 'source_file': 'rows.csv',
                             'provenance': 'test fixture', 'approved_diseases': ['Measles'],
                             'weekly_protocol': {'approved': True, 'approval_reference': 'test', 'minimum_complete_weeks': 10}})
    assert d['eligible']
    assert not dataset([row(1, source_system='FHSIS')])['eligible']


def test_forecast_offsets_do_not_invent_reporting_calendar(monkeypatch):
    monkeypatch.setattr(model, 'nnar', lambda residuals, steps, c: (np.zeros(steps), []))
    result = model.run(dataset(year_lengths={}), 'Measles', protocol())
    assert len(result['sarima']) == 52
    assert all(p['year'] is None and p['morbidity_week'] is None for p in result['forecast_index'])
    assert any('Future reporting calendar unresolved' in w for w in result['warnings'])


def test_missing_actual_evaluation_mask_shared(monkeypatch):
    monkeypatch.setattr(model, 'nnar', lambda residuals, steps, c: (np.zeros(steps), []))
    result = model.run(dataset([row(i, None if i == 18 else i % 3) for i in range(1, 21)]), 'Measles', protocol())
    assert result['metrics']['hybrid']['n'] == result['metrics']['sarima']['n'] == 3
    assert result['evaluation']['excluded_missing_actuals'] == 1
    assert [2025, 18] not in result['evaluation']['period']


def test_evaluation_never_fits_future_actuals(monkeypatch):
    calls = []
    def fit(values, steps, c):
        calls.append(values.copy())
        return {'hybrid': [1.] * steps, 'sarima': [1.] * steps, 'hybrid_status': 'Available',
                'sarima_status': 'Available', 'diagnostics': {}}
    monkeypatch.setattr(model, 'fit_models', fit)
    d = dataset([row(i, 900 if i >= 17 else 1) for i in range(1, 21)])
    model.run(d, 'Measles', protocol())
    assert len(calls) == 2
    assert len(calls[1]) == 16 and 900 not in calls[1]


def test_upload_callback_requires_confirm_and_clears_stale_preview(monkeypatch):
    from dashboard.weekly import ui
    current = dataset()
    active, pending, opened, _ = ui.transition('w-demo', None, None, current)
    assert active is current and pending['context'] == data.DEMO and opened
    active, cleared, opened, _ = ui.transition('w-cancel', None, pending, current)
    assert active is current and cleared is None and not opened
    active, cleared, _, _ = ui.transition('w-activate', None, pending, current)
    assert active['id'] == pending['id'] and cleared is None
    assert current['context'] == data.THESIS


def test_cached_path_reused_without_training(monkeypatch):
    from dashboard.weekly import ui
    d, c = dataset(), protocol()
    prior = {'cache_key': model.cache_key(d, 'Measles', c)}
    monkeypatch.setattr(ui, 'ctx', SimpleNamespace(triggered_id='w-run'))
    def unexpected(*args):
        pytest.fail('Matching path should have been reused')
    monkeypatch.setattr(ui, 'run', unexpected)
    monkeypatch.setattr(ui, 'model_configuration', lambda: c)
    assert ui.forecast(1, d, 'Measles', prior) == prior
