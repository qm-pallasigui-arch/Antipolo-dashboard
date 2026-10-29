# LEGACY RESEARCH CODE
# Not part of the finalized Prophet-XGBoost thesis implementation.
# Retained only for historical/reproducibility purposes.
"""Prototype integration tests; historical outputs are never live forecast storage."""
import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from dashboard.monthly.forecast import ForecastService, ModelFailure, NotEligible
from dashboard.monthly.forecasting.prototype_adapter import PrototypeForecastAdapter
from dashboard.monthly.reports import build_report, export_csv, export_html
from dashboard.monthly.views import page_content
from tests.test_monthly_system import activate, frame, login, dash_action

pytest_plugins = ['tests.test_monthly_system']


def fixture(name='a00'):
    return json.loads(Path(f'tests/fixtures/prototype/icd_inference_{name}.json').read_text())


@pytest.mark.parametrize('name,n', [('a00', 96), ('b25', 84)])
def test_historical_normalization(name, n):
    raw = fixture(name)
    result = PrototypeForecastAdapter.normalize(raw, n, 12)
    assert result['prototype'] is result['is_prototype'] is True
    assert not result['model_metadata']['corrector_applied']
    assert result['selected_output']['forecast'] == raw['prophet']['forecast']
    assert 'Residual correction not applied in this prototype run.' in result['warnings']
    assert 'cases' not in json.dumps(result)


@pytest.mark.parametrize('mode', ['base', 'accepted', 'failed', 'zero'])
def test_correction_selection(mode):
    raw = fixture()
    if mode == 'base':
        raw.pop('hybrid')
    else:
        raw['hybrid'].update({'lambda': 0 if mode == 'zero' else .5,
                              'abstained': False, 'forecast': [99] * 12,
                              'reason': 'failure' if mode == 'failed' else None})
    result = PrototypeForecastAdapter.normalize(raw, 96, 12)
    assert result['model_metadata']['corrector_applied'] == (mode == 'accepted')
    assert result['selected_output']['forecast'] == ([99] * 12 if mode == 'accepted' else raw['prophet']['forecast'])


def test_service_eligibility_and_active_dataset(store, users):
    admin, viewer = users
    data = frame().replace('A15-A19', 'B25-B34')
    candidate = store.stage(admin, data.to_csv(index=False).encode(), 'synthetic.csv')
    dataset = store.activate(admin, candidate['candidate_id'])
    inference = Mock(return_value=fixture())
    service = ForecastService(store, {'prototype': PrototypeForecastAdapter(inference)})
    with pytest.raises(NotEligible):
        service.generate_forecast(admin, 'B25-B34', 12)
    inference.assert_not_called()
    result = service.generate_forecast(admin, 'A00-A09', 12)
    values = inference.call_args.args[0]
    assert len(values) == 96 and values[:2] == [0, 4]
    assert result['prototype'] and result['model_status'] == 'prototype_available'
    assert result['dataset_signature'] == dataset['dataset_signature']
    assert result['forecast_values'][-1]['month'] == '2026-12'
    assert any('Prototype forecast completed for A00-A09.' in n['message'] for n in store.notifications(viewer))
    report = build_report(store, viewer, 'A00-A09')
    assert 'Prototype Forecast' in export_html(report)
    assert 'Prototype Forecast' in export_csv(report)
    assert 'methodology is still under evaluation' in export_html(report)
    for page in ('Dashboard', 'Forecasting', 'Model Performance & Insights'):
        rendered = str(page_content(store, viewer, page, dataset, 'A00-A09'))
        assert 'Prototype' in rendered
        assert 'case count' not in rendered.lower()
        assert 'Hybrid improved' not in rendered
    # A persisted artifact cannot override current eligibility in any view.
    fake = {**result, 'forecast_run_id': 'historical', 'icd10_block': 'B25-B34'}
    service._save(fake)
    assert build_report(store, viewer, 'B25-B34')['forecast'] is None
    for page in ('Dashboard', 'Forecasting', 'Model Performance & Insights'):
        assert '29.33' not in str(page_content(store, viewer, page, dataset, 'B25-B34'))


@pytest.mark.parametrize('bad', [[1], [float('nan')] * 12, [-1] * 12, [True] * 12])
def test_bad_output_preserves_completed_run(store, users, bad):
    admin, _ = users
    dataset = activate(store, admin)
    inference = Mock(return_value=fixture())
    service = ForecastService(store, {'prototype': PrototypeForecastAdapter(inference)})
    good = service.run(admin, 'A00-A09', 12)
    raw = fixture()
    raw['prophet']['forecast'] = bad
    inference.return_value = raw
    with pytest.raises(ModelFailure):
        service.run(admin, 'A00-A09', 12)
    assert store.latest_forecast(dataset['dataset_signature'], 'A00-A09')['forecast_run_id'] == good['forecast_run_id']
    with store.connect() as db:
        failed = json.loads(db.execute("SELECT payload FROM forecasts WHERE status='failed'").fetchone()[0])
    assert failed['prototype'] and failed['model_status'] == 'failed'


def test_generic_replacement_adapter(store, users):
    admin, viewer = users
    dataset = activate(store, admin)
    adapter = Mock(identifier='replacement-test', is_prototype=True)
    adapter.generate.return_value = dict(model_label='Prototype Forecast', n_observations=96,
        horizon_months=1, selected_output={'forecast': [8]}, model_metadata={'engine': 'test'},
        evaluation={}, warnings=['Prototype test double'])
    result = ForecastService(store, {'test': adapter}).generate_forecast(admin, 'A00-A09', 1)
    assert 'prophet' not in json.dumps(result).lower()
    assert page_content(store, viewer, 'Forecasting', dataset, 'A00-A09')
    assert export_html(build_report(store, viewer, 'A00-A09'))


def test_ui_calls_generic_service(store, users):
    from dash import Dash
    from dashboard.monthly.ui import install
    admin, _ = users
    activate(store, admin)
    service = Mock(registry={'test': object()})
    service.generate_forecast.return_value = {'model_label': 'Prototype Forecast'}
    app = Dash('prototype_callback_test')
    install(app, store, service)
    client = app.server.test_client()
    login(client)
    response = dash_action(app, client, 'm-run', **{'m-block': 'A00-A09', 'm-horizon': 3})
    assert 'Prototype Forecast completed for A00-A09.' in response.get_data(as_text=True)
    assert service.generate_forecast.call_args.args[1:] == ('A00-A09', 3)


def test_missing_dependency_is_actionable(store, users, monkeypatch):
    import sys
    admin, _ = users
    activate(store, admin)
    monkeypatch.setitem(sys.modules, 'icd_forecast', None)
    with pytest.raises(ModelFailure, match='install icd_forecast'):
        ForecastService(store).run(admin, 'A00-A09', 12)
