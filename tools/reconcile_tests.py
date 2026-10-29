"""Replace obsolete forecast contracts while retaining source/security acceptance checks."""
from pathlib import Path

p = Path(__file__).resolve().parents[1] / 'tests/test_monthly_system.py'
s = p.read_text(encoding='utf-8')
s = s.replace('from dashboard.monthly.forecast import ForecastService, MethodologyPending, ModelFailure, NotEligible', 'from dashboard.monthly.forecast import ForecastService, MethodologyPending\nfrom dashboard.monthly.forecasting.config import CANDIDATE_BLOCKS')
s = s.replace("    a, b = dataset['blocks']", "    a, b = dataset['blocks'][:2]")
s = s.replace("assert a['eligible'] and", "assert not a['eligible'] and")
s = s.replace("assert len(dataset['blocks']) == 2", "assert tuple(b['icd10_block'] for b in dataset['blocks']) == CANDIDATE_BLOCKS\n    assert all(b['readiness_status'] == 'no_observations' for b in dataset['blocks'][2:])")
start = s.index('class ContractEngine:')
end = s.index('def test_reports_and_notification_visibility', start)
s = s[:start] + '''def test_default_forecast_requires_approved_methodology(store, users):
    admin, viewer = users
    activate(store, admin)
    with pytest.raises(MethodologyPending, match='Prophet'):
        ForecastService(store).run(admin, 'A00-A09', 12)
    with pytest.raises(PermissionError):
        ForecastService(store).run(viewer, 'A00-A09', 12)


''' + s[end:]
s = s.replace("assert 'absent' in report['forecast_explanation']", "assert 'awaits approved' in report['forecast_explanation']")
s = s.replace("assert 'TO FINALIZE' in eligible_report['forecast_explanation']", "assert 'Prophet + XGBoost' in eligible_report['forecast_explanation']")
s = s.replace("    ForecastService(store, {'test': ContractEngine()}).run(admin, 'A00-A09', 3)\n    assert ',forecast' in export_csv(build_report(store, viewer, 'A00-A09'))\n", '')
s = s.replace("assert store.active()['blocks'][0]['eligible']", "assert store.active()['blocks'][0]['readiness_status'] == 'methodology_pending'")
p.write_text(s, encoding='utf-8')
