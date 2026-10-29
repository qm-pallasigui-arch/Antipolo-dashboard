"""Calendar, leakage, configuration and result-scope contracts for the new prototype."""
from dataclasses import replace
import copy
import numpy as np
import pandas as pd
import pytest

from dashboard.monthly.forecasting.adapter import modeling_frame
from dashboard.monthly.forecasting.config import PrototypeModelConfig
from dashboard.monthly.forecasting.evaluation import build_chronological_split, training_mase_scale
from dashboard.monthly.forecasting.features import generate_residual_training_data, lag_features
from dashboard.monthly.forecasting.errors import ForecastComponentError
from dashboard.monthly.forecasting.pipeline import PrototypeWorkflow
from dashboard.monthly.forecasting.hybrid import HybridModel
from dashboard.monthly.forecast import ForecastService, ModelFailure, MethodologyPending
from dashboard.monthly.domain import normalize
from dashboard.monthly.repositories.forecast_repository import ForecastRepository
from dashboard.monthly.repositories.database import postgres_sql, Record
from dashboard.monthly.store import Store
from tests.test_monthly_system import frame, activate
from tests import test_monthly_system as acceptance


@pytest.fixture
def state(tmp_path):
    store = Store(tmp_path / 'state.sqlite3')
    admin, viewer = acceptance.users.__wrapped__(store)
    activate(store, admin)
    return store, admin, viewer


def sample_rows():
    dataset = normalize(frame(), 'synthetic')
    return [r for r in dataset['observations'] if r['icd10_block'] == 'A00-A09']


def test_actual_dates_and_calendar_lags_preserve_unknowns():
    rows = sample_rows()
    original = copy.deepcopy(rows)
    data = modeling_frame(rows)
    assert data.actual_timestamp.min() == pd.Timestamp('2016-01-01')
    gap = data.loc[data.year.isin([2020, 2022])]
    assert gap.consultation_count.isna().all()
    assert set(gap.observation_status) == {'city_report_unavailable'}
    assert (data.loc[data.observation_status == 'observed_zero', 'consultation_count'] == 0).all()
    history = {pd.Timestamp('2019-12-01'): 3.0, pd.Timestamp('2021-01-01'): 4.0}
    assert np.isnan(lag_features(history, pd.Timestamp('2021-01-01'), 12)).all()
    assert lag_features(history, pd.Timestamp('2021-02-01'), 12)[0] == 4
    assert rows == original


def test_split_is_generic_and_scale_uses_only_training():
    data = modeling_frame(sample_rows())
    config = PrototypeModelConfig()
    train, test = build_chronological_split(data, config)
    assert train.year.max() == 2024 and set(test.year) == {2025}
    assert training_mase_scale(train, 12) is None  # Constant year-to-year values: undefined scale.
    data.loc[data.year == 2025, 'consultation_count'] = 1_000_000
    changed_train, _ = build_chronological_split(data, config)
    pd.testing.assert_frame_equal(train, changed_train)
    short = data[data.year >= 2025]
    with pytest.raises(ForecastComponentError) as error:
        build_chronological_split(short, config)
    assert error.value.status == 'xgboost_insufficient_history'


def test_residual_history_status():
    data = modeling_frame(sample_rows()).query('year == 2025')
    fitted = pd.Series(np.zeros(len(data)), index=data.actual_timestamp)
    with pytest.raises(ForecastComponentError) as error:
        generate_residual_training_data(data, fitted, PrototypeModelConfig())
    assert error.value.status == 'xgboost_insufficient_history'


@pytest.mark.parametrize('status', ['prophet_failed', 'xgboost_failed', 'xgboost_insufficient_history'])
def test_failures_are_persisted_without_substitution(state, status):
    store, admin, _ = state
    def failed(rows, dates):
        raise ForecastComponentError(status, 'deliberate test error')
    with pytest.raises(ModelFailure):
        ForecastService(store, HybridModel(failed)).run(admin, 'A00-A09')
    with store.connect() as db:
        assert db.execute('SELECT status FROM forecasts').fetchone()[0] == status
        assert db.execute('SELECT count(*) FROM forecast_values').fetchone()[0] == 0
    assert store.latest_forecast(store.active()['dataset_signature'], 'A00-A09') is None


def test_prototype_persistence_and_final_isolation(state):
    from tests.test_hybrid_forecast import workflow
    store, admin, _ = state
    result = ForecastService(store, HybridModel(workflow)).run(admin, 'A00-A09')
    assert result['is_prototype'] and result['methodology_status'] == 'provisional'
    assert result['forecast_status'] == 'hybrid_completed'
    assert 'Prototype' in result['model_label']
    with store.connect() as db:
        assert db.execute('SELECT count(*) FROM forecast_values').fetchone()[0] == 12
        total = db.execute('SELECT sum(forecast_value) FROM forecast_values').fetchone()[0]
    assert total == result['projected_total']
    assert ForecastRepository(store).completed(result['dataset_signature'], final_only=True) == []
    changed = Store(store.path, model_config=replace(store.model_config, correction_weight=0.2))
    assert changed.latest_forecast(result['dataset_signature'], 'A00-A09') is None
    final = Store(store.path, is_prototype=False)
    assert final.latest_forecast(result['dataset_signature'], 'A00-A09') is None
    with pytest.raises(MethodologyPending):
        ForecastService(final).run(admin, 'A00-A09')


def test_postgres_adapter_transactions_and_types():
    assert 'pg_advisory_xact_lock' in postgres_sql('BEGIN IMMEDIATE')
    assert postgres_sql('INSERT OR IGNORE INTO notification_reads VALUES (?,?,?)').endswith('ON CONFLICT DO NOTHING')
    ddl = postgres_sql('CREATE TABLE a(id INTEGER PRIMARY KEY, payload BLOB, expires REAL)')
    assert 'IDENTITY' in ddl and 'BYTEA' in ddl and 'DOUBLE PRECISION' in ddl
    row = Record(id=7, name='synthetic')
    assert row[0] == row['id'] == 7 and dict(row)['name'] == 'synthetic'


def test_workflow_invokes_both_models_and_evaluation(monkeypatch):
    from dashboard.monthly.forecasting import pipeline
    calls = []
    def components(data, dates, config):
        calls.append((data.actual_timestamp.max(), list(dates)))
        return dict(baseline=[2.0] * len(dates), hybrid=[2.1] * len(dates),
                    correction=[0.1] * len(dates), residual_training_rows=30)
    monkeypatch.setattr(pipeline, 'forecast_components', components)
    result = PrototypeWorkflow(PrototypeModelConfig())(sample_rows(), [f'2026-{m:02}-01' for m in range(1,13)])
    assert len(calls) == 2
    assert calls[1][0] == pd.Timestamp('2024-12-01')
    assert result['evaluation']['methodology_status'] == 'provisional'
    assert result['residual_model'] == 'XGBoost'
