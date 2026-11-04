"""All candidates reach modeling; coverage never selects research participants."""
import json
from dataclasses import replace

import numpy as np
import pandas as pd
import pytest
from plotly.utils import PlotlyJSONEncoder

from dashboard.monthly.data_quality import refresh_dataset
from dashboard.monthly.domain import normalize
from dashboard.monthly.forecasting.config import CANDIDATE_BLOCKS, PrototypeModelConfig
from dashboard.monthly.forecasting.errors import ForecastComponentError
from dashboard.monthly.forecasting.hybrid import HybridModel
from dashboard.monthly.forecasting.pipeline import PrototypeWorkflow
from dashboard.monthly.forecast import ForecastService, ModelFailure
from dashboard.monthly.reports import build_report, export_html
from dashboard.monthly.store import Store
from dashboard.monthly.views import page_content
from tests import test_monthly_system as acceptance
from tests.test_hybrid_forecast import workflow


def test_all_seven_attempted_even_with_twelve_or_no_observations(tmp_path):
    store = Store(tmp_path / 'all-seven.sqlite3', model_config=replace(PrototypeModelConfig(), min_evaluation_observations=999))
    admin, _ = acceptance.users.__wrapped__(store)
    source = acceptance.frame().query('year == 2025')  # Only 12 A00-A09 observations.
    candidate = store.stage(admin, source.to_csv(index=False).encode(), 'short.csv')
    dataset = store.activate(admin, candidate['candidate_id'])
    calls = []
    def record(rows, dates):
        calls.append((rows, dates))
        return workflow(rows, dates)
    ranking = ForecastService(store, HybridModel(record)).run_all(admin)
    assert len(calls) == 7
    assert len([r for r in calls[0][0] if r['consultation_count'] is not None]) == 12
    assert ranking['attempted_blocks'] == list(CANDIDATE_BLOCKS)
    assert ranking['model_statuses']['A00-A09'] == 'hybrid_completed'
    assert ranking['failed_blocks'] == list(CANDIDATE_BLOCKS[1:])
    assert set(ranking['model_statuses'].values()) == {'hybrid_completed', 'xgboost_insufficient_history'}
    assert ranking['top_five_status'] == 'unavailable'
    with store.connect() as db:
        assert db.execute('SELECT count(*) FROM forecasts').fetchone()[0] == 7
        assert db.execute('SELECT count(*) FROM forecast_values').fetchone()[0] == 12
    assert store.active()['dataset_signature'] == dataset['dataset_signature']


def test_short_history_reaches_prophet_then_reports_residual_failure(monkeypatch):
    from dashboard.monthly.forecasting import pipeline
    dataset = normalize(acceptance.frame().query('year == 2025'), 'short.csv')
    calls = []
    def base(frame, dates, config):
        observed = frame.loc[frame.consultation_count.notna()]
        calls.append(observed)
        return pd.Series(np.zeros(len(observed)), index=observed.actual_timestamp), np.zeros(len(dates))
    monkeypatch.setattr(pipeline, 'generate_prophet_base', base)
    with pytest.raises(ForecastComponentError) as error:
        PrototypeWorkflow(PrototypeModelConfig())(dataset['observations'], [f'2026-{m:02}-01' for m in range(1, 13)])
    assert len(calls) == 1 and len(calls[0]) == 12
    assert error.value.status == 'xgboost_insufficient_history'


def test_old_derived_classifications_are_rebuilt_without_changing_source():
    dataset = normalize(acceptance.frame(), 'synthetic.csv')
    signature = dataset['dataset_signature']
    dataset['blocks'][0].update(eligible=False, readiness_status='not_ready', reason='Old classification')
    dataset['warnings'].append('A00-A09: Old classification')
    result = refresh_dataset(dataset)
    assert result['dataset_signature'] == signature
    assert result['observations'] == dataset['observations']
    assert 'eligible' not in result['blocks'][0] and 'readiness_status' not in result['blocks'][0]
    assert 'A00-A09: Old classification' not in result['warnings']
    assert result['blocks'][0]['observed_zero_count'] == 8
    assert result == refresh_dataset(result)


def test_failed_latest_attempt_is_visible_in_pages_and_reports(tmp_path):
    store = Store(tmp_path / 'latest.sqlite3')
    admin, viewer = acceptance.users.__wrapped__(store)
    dataset = acceptance.activate(store, admin)
    success = ForecastService(store, HybridModel(workflow)).run(admin, 'A00-A09')
    def fail(rows, dates):
        raise ForecastComponentError('xgboost_failed', 'Deliberate test failure')
    with pytest.raises(ModelFailure):
        ForecastService(store, HybridModel(fail)).run(admin, 'A00-A09')
    assert store.latest_forecast(dataset['dataset_signature'], 'A00-A09') == success  # Archive access remains possible.
    assert store.latest_model_run(dataset['dataset_signature'], 'A00-A09')['forecast_status'] == 'xgboost_failed'
    report = build_report(store, viewer, 'A00-A09')
    assert report['forecast'] is None and report['model_status'] == 'xgboost_failed'
    assert 'xgboost_failed' in export_html(report)
    for page in ('Dashboard', 'Forecasting', 'Model Performance & Insights'):
        rendered = json.dumps(page_content(store, viewer, page, dataset, 'A00-A09'), cls=PlotlyJSONEncoder)
        assert 'xgboost_failed' in rendered
        assert 'Estimated consultations' not in rendered


def test_evaluation_unavailable_does_not_prevent_future_forecast(monkeypatch):
    from dashboard.monthly.forecasting import pipeline
    dataset = normalize(acceptance.frame().query('year == 2025'), 'short.csv')
    monkeypatch.setattr(pipeline, 'forecast_components', lambda frame, dates, config: dict(
        baseline=[2.] * len(dates), hybrid=[2.1] * len(dates), correction=[.1] * len(dates), residual_training_rows=5))
    result = HybridModel(PrototypeWorkflow(PrototypeModelConfig())).generate(
        dataset['observations'], [f'2026-{m:02}-01' for m in range(1, 13)])
    assert len(result['selected_output']['forecast']) == 12
    assert result['evaluation']['status'] == 'evaluation_unavailable'
    assert result['evaluation']['component_status'] == 'xgboost_insufficient_history'
