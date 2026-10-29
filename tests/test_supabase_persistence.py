"""Optional real Supabase integration. Requires a dedicated test connection, never the app URL."""
import os
import secrets

import pytest

from dashboard.monthly.store import Store
from dashboard.monthly.repositories.ranking_repository import RankingRepository
from dashboard.monthly.repositories.forecast_repository import ForecastRepository
from dashboard.monthly.forecast import ForecastService
from dashboard.monthly.forecasting.hybrid import HybridModel
from dashboard.monthly.reports import build_report
from tests import test_monthly_system as acceptance
from tests.test_hybrid_forecast import workflow


@pytest.mark.skipif(not os.environ.get('TEST_SUPABASE_DATABASE_URL'), reason='Dedicated Supabase test connection not configured')
def test_supabase_restart_persistence_and_rbac(tmp_path, monkeypatch):
    import psycopg
    from psycopg import sql
    url = os.environ['TEST_SUPABASE_DATABASE_URL']
    schema = 'antipolo_test_' + secrets.token_hex(8)
    monkeypatch.setenv('MONTHLY_DATABASE_SCHEMA', schema)
    try:
        store = Store(tmp_path / 'cloud-test', database_url=url, is_prototype=True)
        admin, viewer = acceptance.users.__wrapped__(store)
        dataset = acceptance.activate(store, admin)
        service = ForecastService(store, HybridModel(workflow))
        with pytest.raises(PermissionError):
            service.run_all(viewer)
        ranking = service.run_all(admin)
        report = build_report(store, viewer, 'A00-A09')
        reopened = Store(tmp_path / 'cloud-test', database_url=url, is_prototype=True)
        assert reopened.active()['dataset_signature'] == dataset['dataset_signature']
        assert len(ForecastRepository(reopened).completed(dataset['dataset_signature'])) == 2
        assert RankingRepository(reopened).latest(dataset['dataset_signature']) == ranking
        with reopened.connect() as db:
            assert db.execute('SELECT count(*) FROM forecast_values').fetchone()[0] == 24
            assert db.execute('SELECT id FROM reports WHERE id=?', (report['report_id'],)).fetchone()
        assert reopened.notifications(viewer)
        second = acceptance.activate(reopened, admin, 44)
        assert reopened.latest_forecast(second['dataset_signature'], 'A00-A09') is None
    finally:
        # Only the random schema created by this test is removed, never the app schema.
        assert schema.startswith('antipolo_test_') and len(schema) == len('antipolo_test_') + 16
        with psycopg.connect(url, sslmode='require') as db:
            db.execute(sql.SQL('DROP SCHEMA IF EXISTS {} CASCADE').format(sql.Identifier(schema)))
