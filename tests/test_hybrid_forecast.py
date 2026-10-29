"""Synthetic software contracts; these tests do not approve thesis methodology."""
import ast
import copy
import json
from pathlib import Path

import pytest

from tests.test_monthly_system import activate
from tests import test_monthly_system as acceptance
from dashboard.monthly.forecast import ForecastService, ModelFailure, NotEligible
from dashboard.monthly.forecasting.config import CANDIDATE_BLOCKS
from dashboard.monthly.forecasting.features import validate_error_rows
from dashboard.monthly.forecasting.hybrid import HybridModel
from dashboard.monthly.repositories.forecast_repository import ForecastRepository
from dashboard.monthly.repositories.ranking_repository import RankingRepository
from dashboard.monthly.services.ranking_service import rank_forecasts
from dashboard.monthly.reports import build_report, export_csv, export_html
from dashboard.monthly.store import Store


@pytest.fixture
def store(tmp_path):
    return Store(tmp_path / 'hybrid.sqlite3')


@pytest.fixture
def users(store):
    return acceptance.users.__wrapped__(store)


def workflow(rows, dates):
    assert dates == [f'2026-{m:02}-01' for m in range(1, 13)]
    assert any(r['year'] == 2020 and r['consultation_count'] is None for r in rows)
    return dict(base_model='Prophet', residual_model='XGBoost', correction_status='completed',
                base_forecast=[2.0] * 12, correction=[-3.0] + [1.0] * 11,
                evaluation={'status': 'synthetic test only'})


def configured(store):
    # Explicit synthetic policy, not a production coverage threshold.
    store.readiness_policy = lambda rows: {'eligible': True, 'reason': 'Synthetic software test policy'}
    return ForecastService(store, HybridModel(workflow))


def test_hybrid_chronology_persistence_failure_and_activation(store, users):
    admin, viewer = users
    dataset = activate(store, admin)
    service = configured(store)
    with pytest.raises(PermissionError):
        service.run_all(viewer)
    with pytest.raises(NotEligible):
        service.run(admin, 'B90-B94')
    for horizon in (0, 3, 13, True, 12.0):
        with pytest.raises(ValueError):
            service.run(admin, 'A00-A09', horizon)
    result = service.run(admin, 'A00-A09')
    assert result['forecast_values'][0]['month'] == '2026-01'
    assert result['forecast_values'][-1]['month'] == '2026-12'
    assert result['forecast_values'][0]['consultation_count'] == 0
    assert result['forecast_values'][1]['consultation_count'] == 3
    assert result['model_name'] == 'Prophet + XGBoost'
    assert Store(store.path).latest_forecast(dataset['dataset_signature'], 'A00-A09') == result
    assert ',forecast' in export_csv(build_report(store, viewer, 'A00-A09'))

    def failed(rows, dates):
        raw = workflow(rows, dates)
        raw['correction_status'] = 'failed'
        return raw
    with pytest.raises(ModelFailure, match='No substitute'):
        ForecastService(store, HybridModel(failed)).run(admin, 'A00-A09')
    assert store.latest_forecast(dataset['dataset_signature'], 'A00-A09') == result
    with store.connect() as db:
        failed_result = json.loads(db.execute("SELECT payload FROM forecasts WHERE status='xgboost_failed'").fetchone()[0])
    assert 'forecast_values' not in failed_result
    second = activate(store, admin, 22)
    assert store.latest_forecast(second['dataset_signature'], 'A00-A09') is None


def test_batch_ranking_and_report(store, users):
    admin, viewer = users
    dataset = activate(store, admin)
    ranking = configured(store).run_all(admin)
    assert len(ranking['rankings']) == 2
    assert ranking['top_five'] == [] and ranking['top_five_status'] == 'unavailable'
    assert ranking['rankings'][0]['projected_total'] == 33
    assert ranking['warnings'] and len(ranking['excluded_blocks']) == 5
    assert RankingRepository(Store(store.path)).latest(dataset['dataset_signature']) == ranking
    report = build_report(store, viewer, 'A00-A09')
    assert report['projected_ranking'] == ranking
    assert 'Projected Top Five' in export_html(report)
    second = activate(store, admin, 8)
    assert RankingRepository(store).latest(second['dataset_signature']) is None


def test_rank_all_seven_and_reject_incomparable_results(store, users):
    admin, _ = users
    dataset = activate(store, admin)
    template = configured(store).run(admin, 'A00-A09', group_id='group')
    results = []
    for i, code in enumerate(CANDIDATE_BLOCKS):
        result = copy.deepcopy(template)
        result.update(icd10_block=code, forecast_run_id=code)
        for value in result['forecast_values']:
            value['consultation_count'] = i
        results.append(result)
    ranking = rank_forecasts(results, dataset['dataset_signature'], 'group')
    assert len(ranking['rankings']) == 7 and len(ranking['top_five']) == 5
    assert ranking['rankings'][0]['icd10_block'] == 'B90-B94'
    assert ranking['rankings'][0]['projected_total'] == 72
    for field, value in [('dataset_signature', 'stale'), ('forecast_run_group_id', 'other'), ('model_name', 'Legacy'), ('forecast_status', 'failed')]:
        altered = copy.deepcopy(results)
        altered[0][field] = value
        with pytest.raises(ValueError):
            rank_forecasts(altered, dataset['dataset_signature'], 'group')
    altered = copy.deepcopy(results)
    altered[0]['forecast_values'][0]['month'] = '2025-01'
    with pytest.raises(ValueError):
        rank_forecasts(altered, dataset['dataset_signature'], 'group')
    assert rank_forecasts([], dataset['dataset_signature'], 'empty')['top_five'] == []


def test_legacy_records_never_become_live(store, users):
    admin, _ = users
    dataset = activate(store, admin)
    with store.connect() as db:
        db.execute('INSERT INTO forecasts VALUES (?,?,?,?,?,?)', ('legacy', dataset['dataset_signature'], 'A00-A09', 'completed', json.dumps({'prototype': True}), '2099'))
    assert ForecastRepository(store).completed(dataset['dataset_signature']) == []


def test_error_training_rejects_in_sample_targets():
    with pytest.raises(ValueError, match='after'):
        validate_error_rows([{'training_cutoff': '2025-12-01', 'target_month': '2025-12-01'}])
    assert validate_error_rows([{'training_cutoff': '2024-12-01', 'target_month': '2025-01-01'}])


def test_no_legacy_production_imports():
    forbidden = ('archive', 'icd_forecast', 'icd_inference', 'prototype_adapter')
    for path in Path('dashboard').rglob('*.py'):
        tree = ast.parse(path.read_text(encoding='utf-8'))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [n.name for n in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or '']
            else:
                continue
            assert not any(part in name.split('.') for name in names for part in forbidden), path
