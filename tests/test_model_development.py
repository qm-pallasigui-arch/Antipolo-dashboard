import copy
import json
import subprocess
import sys
from types import SimpleNamespace

import pytest

from dashboard.weekly import model, registry, outputs, ui
from dashboard.weekly.preparedness import summarize
from tests.test_weekly import dataset, protocol


def history(n=156):
    return dataset([{'disease': 'Measles', 'year': 2022 + i // 52,
                     'morbidity_week': i % 52 + 1, 'case_count': i % 7}
                    for i in range(n)], year_lengths={str(y): 52 for y in range(2022, 2028)})


def fake_fit(values, steps, c):
    prediction = float(c['candidates'][0]['order'][0])
    return {'hybrid': [prediction] * steps, 'sarima': [prediction] * steps,
            'hybrid_status': 'Available', 'sarima_status': 'Available', 'diagnostics': {}}


def evaluate(d, c=None):
    return model.deferred_evaluation(d, model.empty_result(d, 'Measles', c or protocol()))


def test_test_outcomes_cannot_select_configuration_and_lock_precedes_test(monkeypatch):
    d = history()
    for r in d['records'][52:104]:
        r['case_count'] = 2
    c = protocol()
    c['candidates'] = [{'order': [n, 0, 0], 'seasonal_order': [0, 0, 0, 0]} for n in (0, 2)]
    calls = []

    def fit(values, steps, config):
        calls.append(len(values))
        if len(values) == 104:
            saved = registry.load(model.selection_key(d, 'Measles', c))
            assert saved['status'] == 'Locked'
            assert saved['performance'] is None
            assert config['candidates'][0]['order'][0] == 2
        return fake_fit(values, steps, config)

    monkeypatch.setattr(model, 'fit_models', fit)
    first = evaluate(d, c)
    assert calls == [52, 52, 104]
    assert first['selection']['periods']['validation']['positions'] == 52
    assert first['selection']['periods']['final_test']['positions'] == 52
    before = copy.deepcopy(first['selection']['selected'])
    for r in d['records'][-52:]:
        r['case_count'] = 10000
    second = evaluate(d, c)
    assert second['selection']['selected'] == before
    assert second['metrics']['hybrid'] != first['metrics']['hybrid']


def test_no_operational_search_and_persisted_performance_reused(monkeypatch):
    d = history()
    calls = []

    def fit(values, steps, c):
        calls.append(len(values))
        return fake_fit(values, steps, c)

    monkeypatch.setattr(model, 'fit_models', fit)
    initial = model.run(d, 'Measles', protocol())
    assert not calls and 'Compute Model Performance' in initial['failure_reason']
    evaluated = evaluate(d)
    assert calls == [52, 104]
    repeated = evaluate(d)
    assert calls == [52, 104]
    assert evaluated['metrics'] == repeated['metrics']
    future = model.run(d, 'Measles', protocol())
    assert calls == [52, 104, 156]
    assert len(future['hybrid']) == 52
    assert future['operational_training_period']['positions'] == 156
    assert future['selection']['status'] == 'Locked'
    assert future['range'] is None
    assert future['preparedness']['status'] == 'Available'
    # Upload bookkeeping changes do not repeat selection.
    d['metadata']['uploaded_at'] = 'later'
    assert registry.load(model.selection_key(d, 'Measles', protocol()))
    d['records'][0]['case_count'] += 1
    assert registry.load(model.selection_key(d, 'Measles', protocol())) is None


def test_zero_missing_and_trailing_missing_test_positions(monkeypatch):
    d = history()
    for r in d['records'][-52:]:
        r['case_count'] = 0
    d['records'][-1]['case_count'] = None
    d['records'][-2]['case_count'] = 4
    monkeypatch.setattr(model, 'fit_models', fake_fit)
    scored = evaluate(d)
    e = scored['evaluation']
    assert e['scored_weeks'] == 51 and e['excluded_missing_actuals'] == 1
    assert e['zero_actuals_excluded_from_mape'] == 50
    assert e['mape_valid_observations'] == 1
    assert scored['metrics']['hybrid']['mae'] == pytest.approx(4 / 51)
    assert scored['metrics']['hybrid']['mape'] == 100
    assert scored['selection']['periods']['final_test']['end'] == [2024, 52]


def test_insufficient_history_is_explicit_and_does_not_fit(monkeypatch):
    monkeypatch.setattr(model, 'fit_models', lambda *args: pytest.fail('Must not fit'))
    with pytest.raises(ValueError, match='insufficient historical data'):
        evaluate(history(110))


def test_locked_hybrid_failure_never_substitutes_sarima(monkeypatch):
    d = history()
    monkeypatch.setattr(model, 'fit_models', fake_fit)
    evaluate(d)

    def failure(values, steps, c):
        return {**fake_fit(values, steps, c), 'hybrid': None, 'hybrid_status': 'Hybrid unavailable',
                'failure_reason': 'Insufficient residual observations.'}

    monkeypatch.setattr(model, 'fit_models', failure)
    result = model.run(d, 'Measles', protocol())
    assert result['hybrid'] is None and result['sarima'] is not None
    assert result['preparedness']['model'] == 'sarima'
    assert 'SARIMA-only' in result['preparedness']['text']
    assert 'Insufficient residual' in result['failure_reason']


def test_mixed_or_invalid_dates_use_derived_for_summary_options_and_filter():
    d = history(2)
    d['records'][0]['week_start_date'] = '2030-07-01'
    d['records'][1]['week_start_date'] = 'invalid'
    labels, totals, explanation = outputs.historical_summary(d, 'Measles', 'Monthly')
    assert all('2030' not in label for label in labels)
    assert 'derived' in explanation
    assert ui.history_options(d, 'Measles', 'Monthly')[0] == labels
    rendered = str(ui.render('Historical Trends', d, 'Measles', None, 13, 'Monthly', labels[0], labels[-1])[0])
    assert 'derived' in rendered and '2030-07' not in rendered
    d['records'][1]['week_start_date'] = '2030-07-08'
    assert outputs.historical_summary(d, 'Measles', 'Monthly')[0] == ['2030-07']


def test_preparedness_is_reproducible_and_zero_reference_is_not_a_percentage():
    result = {'hybrid': [2.] * 51 + [9.], 'context': 'Technical',
              'forecast_index': [{'year': 2026, 'morbidity_week': i + 1, 'horizon_week': i + 1} for i in range(52)]}
    summary = summarize(result, [0] * 13)
    assert summary == summarize(result, [0] * 13)
    assert summary['peak_week']['morbidity_week'] == 52
    assert summary['peak_forecast_count'] == 9
    assert summary['longest_elevated_run'] == 52
    assert summary['windows']['4']['percent_change'] is None
    assert summary['trend_direction'] == 'increase'
    assert 'not an outbreak declaration' in summary['label']


def test_exports_sections_no_intervals_and_evaluation_cached(monkeypatch):
    d = history()
    monkeypatch.setattr(model, 'fit_models', fake_fit)
    evaluate(d)
    result = model.run(d, 'Measles', protocol())
    result['range'] = {'lower': [0] * 52, 'upper': [99] * 52}
    frame = outputs.export_frame(d, result)
    assert not any('range_' in c for c in frame.columns)
    assert 'preparedness_summary' in frame.columns
    monkeypatch.setattr(ui, 'ctx', SimpleNamespace(triggered_id='w-export-json'))
    payload = json.loads(ui.export(0, 1, d, {'Measles': result}, 'Measles')['content'])
    for section in ('future_forecast_results', 'historical_model_performance', 'model_metadata', 'preparedness_summary'):
        assert section in payload
    assert len(payload['future_forecast_results']) == 104  # two separately named models
    assert 'range' not in payload['forecast']


def test_compute_button_bootstraps_selection_without_forecast(monkeypatch):
    d = history()
    monkeypatch.setattr(model, 'fit_models', fake_fit)
    monkeypatch.setattr(ui, 'model_configuration', protocol)
    monkeypatch.setattr(ui, 'ctx', SimpleNamespace(triggered_id='w-evaluate'))
    result = ui.evaluate_retrospective(1, d, 'Measles', None)['Measles']
    assert result['selection']['status'] == 'Locked'
    assert result['hybrid'] is None
    assert result['evaluation']['status'] == 'Retrospective evaluation'


def test_browser_numeric_round_trip_preserves_persisted_selection(monkeypatch):
    d = history()
    monkeypatch.setattr(model, 'fit_models', fake_fit)
    pending = model.run(d, 'Measles', protocol())
    assert isinstance(pending['configuration']['alpha'], float)
    # JavaScript serializes a JSON number 1.0 as 1 on the next callback request.
    from_browser = registry.canonical(pending)
    assert isinstance(from_browser['configuration']['alpha'], int)
    model.deferred_evaluation(d, from_browser)
    future = model.run(d, 'Measles', protocol())
    assert future['hybrid'] is not None


def test_appended_history_reuses_lock_but_corrections_do_not(monkeypatch):
    original = history()
    calls = []

    def fit(values, steps, c):
        calls.append(len(values))
        return fake_fit(values, steps, c)

    monkeypatch.setattr(model, 'fit_models', fit)
    evaluated = evaluate(original)
    extended = history(160)
    future = model.run(extended, 'Measles', protocol())
    assert calls == [52, 104, 160]
    assert future['metrics'] == evaluated['metrics']
    assert future['selection']['dataset_id'] == original['id']
    assert future['operational_training_period']['positions'] == 160
    assert future['evaluation']['periods']['final_test']['end'] == [2024, 52]
    rescored = model.deferred_evaluation(extended, future)
    assert rescored['forecast_refresh_required']
    assert rescored['operational_selection_run'] == future['operational_selection_run']
    assert rescored['selection']['selection_run'] != future['operational_selection_run']
    assert rescored['hybrid'] == future['hybrid']
    assert outputs.export_sections(extended, rescored)['model_metadata']['selected_configurations'] == future['operational_configurations']
    extended['records'][0]['case_count'] = 999
    rejected = model.run(extended, 'Measles', protocol())
    assert rejected['hybrid'] is None and calls == [52, 104, 160, 56, 108]


def test_real_small_fit_selection_refit_and_operational_path():
    d = history(130)
    result = evaluate(d)
    assert result['metrics']['sarima']['n'] == 52
    future = model.run(d, 'Measles', protocol())
    assert len(future['sarima']) == 52
    assert future['metrics'] == result['metrics']


def test_selection_survives_new_process(monkeypatch):
    d = history()
    monkeypatch.setattr(model, 'fit_models', fake_fit)
    evaluated = evaluate(d)
    key = model.selection_key(d, 'Measles', protocol())
    script = 'import json, sys; from dashboard.weekly.registry import load; print(json.dumps(load(sys.argv[1])))'
    process = subprocess.run([sys.executable, '-c', script, key], capture_output=True, text=True, check=True)
    saved = json.loads(process.stdout)
    assert saved['status'] == 'Locked'
    assert saved['performance']['metrics'] == evaluated['metrics']


def test_failed_test_refit_does_not_reselect_and_exports_no_invented_metrics(monkeypatch):
    d = history()
    calls = []

    def fit(values, steps, c):
        calls.append(len(values))
        if len(values) == 104:
            raise ValueError('Forced selected-refit failure')
        return fake_fit(values, steps, c)

    monkeypatch.setattr(model, 'fit_models', fit)
    scored = evaluate(d)
    assert calls == [52, 104, 104]  # independently attempt the two locked models
    assert scored['evaluation']['status'] == 'Model performance unavailable'
    assert scored['metrics'] == {'hybrid': None, 'sarima': None}
    future = model.run(d, 'Measles', protocol())
    assert len(future['hybrid']) == 52
    assert calls[-1] == 156
    sections = outputs.export_sections(d, future)
    assert len(sections['future_forecast_results']) == 104
    assert sections['historical_model_performance']['scored_test_observations'] == 0
    assert sections['historical_model_performance']['metrics']['hybrid'] is None


def test_old_model_session_is_not_presented_as_new_methodology():
    assert ui.stored_forecast({'Measles': {'model_version': 'weekly-2', 'hybrid': [1]}}, 'Measles') is None


def test_per_disease_protocol_normalization_is_idempotent():
    from dashboard.weekly.settings import model_configuration
    configured = model_configuration()
    for disease in ('Dengue', 'Leptospirosis', 'Measles-Rubella'):
        resolved = model.validate_config(configured, disease)
        assert model.validate_config(resolved, disease) == resolved
