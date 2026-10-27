"""Acceptance contracts for the revised study; fixtures are synthetic, never official data."""
import base64
import io

import pandas as pd
import pytest
from dash import Dash

from dashboard.monthly.domain import (AVAILABLE_YEARS, DataError, annual_history,
                                     evaluate_forecast_eligibility, normalize, parse_upload)
from dashboard.monthly.forecast import ForecastService, MethodologyPending, ModelFailure, NotEligible
from dashboard.monthly.reports import build_report, export_csv, export_html
from dashboard.monthly.security import change_user, create_user
from dashboard.monthly.store import Store
from dashboard.monthly.ui import install, page_content, trend_chart


def frame(count=4):
    return pd.DataFrame([dict(year=y, month=m, icd10_block=code, icd10_description=description,
                             consultation_count=0 if m == 1 else count)
        for code, description, years in [('A00-A09', 'Intestinal infectious diseases', AVAILABLE_YEARS),
                                         ('A15-A19', 'Tuberculosis', AVAILABLE_YEARS[:-1])]
        for y in years for m in range(1, 13)])


@pytest.fixture
def store(tmp_path):
    return Store(tmp_path / 'monthly.sqlite3')


@pytest.fixture
def users(store):
    admin_id = create_user(store, 'researcher', 'a-long-test-password', bootstrap=True)
    admin = dict(id=admin_id, username='researcher', role='admin', active=1)
    viewer_id = create_user(store, 'health-user', 'another-long-password', actor=admin)
    return admin, dict(id=viewer_id, username='health-user', role='viewer', active=1)


def activate(store, admin, count=4):
    candidate = store.stage(admin, frame(count).to_csv(index=False).encode(), 'synthetic-test.csv')
    return store.activate(admin, candidate['candidate_id'])


def test_semantics_and_eligibility():
    dataset = normalize(frame(), 'synthetic-test.csv')
    a, b = dataset['blocks']
    assert a['eligible'] and a['top5_year_count'] == 8 and a['reported_month_count'] == 96
    assert not b['eligible'] and b['top5_year_count'] == 7
    assert len(dataset['blocks']) == 2
    for r in dataset['observations']:
        if r['year'] in (2020, 2022):
            assert r['consultation_count'] is None and r['observation_status'] == 'city_report_unavailable'
        elif r['icd10_block'] == 'A15-A19' and r['year'] == 2025:
            assert r['consultation_count'] is None and r['observation_status'] == 'outside_annual_top5'
        elif r['month_number'] == 1:
            assert r['consultation_count'] == 0 and r['observation_status'] == 'observed_zero'
    rows = [r for r in dataset['observations'] if r['icd10_block'] == 'A00-A09']
    incomplete = [r for r in rows if (r['year'], r['month_number']) != (2025, 12)]
    assert evaluate_forecast_eligibility(incomplete)['reported_month_count'] == 95
    assert not evaluate_forecast_eligibility(incomplete)['eligible']
    assert evaluate_forecast_eligibility(rows + rows) == evaluate_forecast_eligibility(rows)
    assert not a['missing_years'] and not a['missing_months']
    assert annual_history(dataset, 'A15-A19')[-1]['annual_total'] is None
    figure = trend_chart(dataset, 'A15-A19').figure
    assert not figure.data[0].connectgaps and None in figure.data[0].y
    assert len(figure.layout.shapes) == 3


@pytest.mark.parametrize('mutation', ['negative', 'fraction', 'duplicate', 'missing', 'null', 'bad_month', 'bad_year', 'bad_code', 'unavailable_count', 'status_conflict', 'description'])
def test_invalid_data(mutation):
    source = frame()
    if mutation == 'negative': source.loc[0, 'consultation_count'] = -1
    if mutation == 'fraction':
        source['consultation_count'] = source['consultation_count'].astype(float)
        source.loc[0, 'consultation_count'] = 1.5
    if mutation == 'duplicate': source = pd.concat([source, source.iloc[:1]])
    if mutation == 'missing': source = source.iloc[1:]
    if mutation == 'null': source.loc[0, 'consultation_count'] = None
    if mutation == 'bad_month': source.loc[0, 'month'] = 13
    if mutation == 'bad_year': source.loc[0, 'year'] = 2030
    if mutation == 'bad_code': source.loc[0, 'icd10_block'] = 'DENGUE'
    if mutation == 'unavailable_count': source.loc[0, 'year'] = 2020
    if mutation == 'status_conflict': source['observation_status'] = 'outside_annual_top5'
    if mutation == 'description': source.loc[0, 'icd10_description'] = 'Conflicting label'
    with pytest.raises(DataError): normalize(source, 'invalid.csv')


def test_upload_normalization_and_roundtrip():
    source = frame()
    source['month'] = source['month'].map(lambda m: __import__('calendar').month_abbr[m])
    source['icd10_block'] = source['icd10_block'].str.replace('-', ' – ')
    dataset = normalize(source, 'source.csv')
    exported = pd.DataFrame(dataset['observations'])
    assert normalize(exported, 'export.csv')['dataset_signature'] == dataset['dataset_signature']
    buffer = io.BytesIO()
    source.to_excel(buffer, index=False)
    assert parse_upload(buffer.getvalue(), 'source.xlsx')['dataset_signature'] == dataset['dataset_signature']
    with pytest.raises(DataError): parse_upload(b'', 'empty.csv')
    with pytest.raises(DataError): parse_upload(b'abc', 'source.pdf')
    with pytest.raises(DataError): normalize(source.drop(columns='month'), 'bad.csv')


def workbook_bytes(sheets):
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        for name, sheet in sheets.items():
            sheet.to_excel(writer, sheet_name=name, index=False)
    return buffer.getvalue()


def test_workbook_supporting_sheets_do_not_become_observations():
    source = frame().rename(columns={'month': 'month_number'})
    sheets = {'Canonical Data': source,
              'Annual Top5 Audit': source.groupby(['year', 'icd10_block'], as_index=False)['consultation_count'].sum(),
              'Eligibility Summary': pd.DataFrame([{'icd10_block': 'A15-A19', 'forecast_eligible': True}]),
              'Metadata': pd.DataFrame([{'Field': 'Source', 'Value': 'Synthetic test'}])}
    result = parse_upload(workbook_bytes(sheets), 'test.xlsx')
    assert result['dataset_signature'] == parse_upload(source.to_csv(index=False).encode(), 'test.csv')['dataset_signature']
    assert not result['blocks'][1]['eligible']  # Never trust workbook eligibility claims.
    assert 'Annual Top5 Audit, Eligibility Summary, Metadata' in result['warnings'][-1]


def test_workbook_combines_monthly_sheets_and_rejects_bad_data():
    source = frame()
    split = {'First': source[source.year < 2021], 'Second': source[source.year >= 2021]}
    assert parse_upload(workbook_bytes(split), 'test.xlsx')['dataset_signature'] == normalize(source, 'test.csv')['dataset_signature']
    with pytest.raises(DataError, match='Duplicate'):
        parse_upload(workbook_bytes({'First': source, 'Duplicate': source}), 'test.xlsx')
    with pytest.raises(DataError, match='Worksheet "Broken".*consultation_count'):
        parse_upload(workbook_bytes({'Valid': source, 'Broken': source.drop(columns='consultation_count')}), 'test.xlsx')
    source.loc[0, 'month'] = 13
    with pytest.raises(DataError, match='Month'):
        parse_upload(workbook_bytes({'Canonical Data': source}), 'test.xlsx')
    with pytest.raises(DataError, match='No monthly-data worksheet'):
        parse_upload(workbook_bytes({'Metadata': pd.DataFrame([{'Field': 'Source', 'Value': 'Synthetic'}])}), 'test.xlsx')


def test_activation_is_explicit_atomic_and_persistent(store, users):
    admin, viewer = users
    first = activate(store, admin)
    with pytest.raises(DataError): store.stage(admin, b'invalid', 'bad.csv')
    assert store.active()['dataset_signature'] == first['dataset_signature']
    for state in ('cancelled', 'rejected'):
        candidate = store.stage(admin, frame(9).to_csv(index=False).encode(), 'candidate.csv')
        assert store.active()['dataset_signature'] == first['dataset_signature']
        store.discard(admin, candidate['candidate_id'], state)
        with pytest.raises(DataError): store.activate(admin, candidate['candidate_id'])
        assert store.active()['dataset_signature'] == first['dataset_signature']
    second = activate(store, admin, 12)
    assert second['dataset_signature'] != first['dataset_signature']
    assert Store(store.path).active()['dataset_signature'] == second['dataset_signature']
    with pytest.raises(PermissionError): store.stage(viewer, b'', 'test.csv')
    with pytest.raises(PermissionError): store.activate(viewer, 'anything')
    with pytest.raises(PermissionError): store.discard(viewer, 'anything')
    with pytest.raises(PermissionError): store.add_note(viewer, 'change')
    store.add_note(admin, 'Official zeros retained; clarification requested.')
    assert store.notes(second['dataset_signature'])


class ContractEngine:
    """Generic adapter test double; never imported by the application."""
    identifier = 'test-double'
    is_prototype = True

    def generate(self, observations, horizon):
        assert len(observations) == 120
        assert sum(r['consultation_count'] is None for r in observations) == 24
        return dict(model_label='Prototype Forecast', n_observations=96,
                    horizon_months=horizon, selected_output={'forecast': [3.5] * horizon},
                    model_metadata={'engine': self.identifier},
                    evaluation={'method': 'synthetic contract test only'}, warnings=[])


def test_forecast_contract_isolation_and_failure(store, users):
    admin, viewer = users
    dataset = activate(store, admin)
    service = ForecastService(store, {'test-double': ContractEngine()})
    with pytest.raises(NotEligible): service.run(admin, 'A15-A19', 12)
    with pytest.raises(PermissionError): service.run(viewer, 'A00-A09', 12)
    with pytest.raises(MethodologyPending): ForecastService(store, {}).run(admin, 'A00-A09', 12)
    for horizon in (0, 13, 1.2, True, '12'):
        with pytest.raises(DataError): service.run(admin, 'A00-A09', horizon)
    result = service.run(admin, 'A00-A09', 12)
    assert result['dataset_signature'] == dataset['dataset_signature']
    assert result['icd10_block'] == 'A00-A09'
    assert result['forecast_values'][0]['month'] == '2026-01'
    assert result['forecast_values'][-1]['month'] == '2026-12'
    assert store.latest_forecast(dataset['dataset_signature'], 'A15-A19') is None
    class FailingEngine(ContractEngine):
        def generate(self, observations, horizon): raise RuntimeError('deliberate failure')
    with pytest.raises(ModelFailure): ForecastService(store, {'other': FailingEngine()}).run(admin, 'A00-A09', 12)
    assert store.latest_forecast(dataset['dataset_signature'], 'A00-A09')['forecast_run_id'] == result['forecast_run_id']
    second = activate(store, admin, 22)
    assert store.latest_forecast(second['dataset_signature'], 'A00-A09') is None
    assert store.latest_forecast(dataset['dataset_signature'], 'A00-A09') is not None


def test_reports_and_notification_visibility(store, users):
    admin, viewer = users
    dataset = activate(store, admin)
    with pytest.raises(DataError): store.stage(admin, b'invalid', 'bad.csv')
    report = build_report(store, viewer, 'A15-A19')
    assert not report['block']['eligible'] and report['forecast'] is None
    assert 'absent' in report['forecast_explanation']
    assert report['provenance']['source_database'].startswith('Field Health')
    csv = export_csv(report)
    assert '2020-01,,city_report_unavailable' in csv
    assert '2025-01,,outside_annual_top5' in csv
    assert '2016-01,0,observed_zero' in csv
    html = export_html(report)
    assert '<h2>Forecast</h2>' in html and 'Tuberculosis' in html and 'Model performance' in html
    eligible_report = build_report(store, viewer, 'A00-A09')
    assert 'TO FINALIZE' in eligible_report['forecast_explanation']
    ForecastService(store, {'test': ContractEngine()}).run(admin, 'A00-A09', 3)
    assert ',forecast' in export_csv(build_report(store, viewer, 'A00-A09'))
    assert any(n['title'] == 'Dataset validation failed' for n in store.notifications(admin))
    assert not any(n['title'] == 'Dataset validation failed' for n in store.notifications(viewer))
    assert any(n['type'] == 'eligibility' for n in store.notifications(viewer))
    store.mark_read(viewer)
    assert all(n['read_at'] for n in Store(store.path).notifications(viewer))
    assert any(not n['read_at'] for n in store.notifications(admin))
    for page in ('Dashboard', 'Disease Trends', 'Forecasting', 'Model Performance & Insights', 'Data & Quality', 'Reports', 'Notifications', 'Help & About'):
        assert page_content(store, viewer, page, dataset, 'A15-A19')


@pytest.fixture
def webapp(store, users):
    app = Dash('monthly_acceptance')
    install(app, store)
    app.server.config['TESTING'] = True
    return app


def login(client, username='researcher', password='a-long-test-password'):
    client.get('/login')
    with client.session_transaction() as session:
        csrf = session['csrf']
    return client.post('/login', data=dict(username=username, password=password, csrf=csrf))


def test_authentication_and_user_management(webapp, store, users):
    admin, viewer = users
    client = webapp.server.test_client()
    assert client.get('/').status_code == 302
    assert client.get('/_dash-layout').status_code == 401
    assert client.post('/_dash-update-component', json={}).status_code == 401
    assert login(client, password='wrong').status_code == 200
    assert client.get('/_dash-layout').status_code == 401
    assert login(client).status_code == 302
    assert client.get('/_dash-layout').status_code == 200
    assert client.get('/account').status_code == 200
    with store.connect() as db:
        assert db.execute('SELECT password_hash FROM users LIMIT 1').fetchone()[0] != 'a-long-test-password'
    with pytest.raises(PermissionError): create_user(store, 'forbidden', 'long-test-password', actor=viewer)
    with pytest.raises(PermissionError): change_user(store, viewer, admin['id'], 'viewer', 1)
    with pytest.raises(ValueError): change_user(store, admin, admin['id'], 'viewer', 1)
    with client.session_transaction() as session:
        old_token, csrf = session['token'], session['csrf']
    assert client.post('/logout', data={'csrf': csrf}).status_code == 302
    with store.connect() as db:
        assert not db.execute('SELECT * FROM sessions WHERE token=?', (old_token,)).fetchone()
    assert client.get('/_dash-layout').status_code == 401
    assert login(client, 'health-user', 'another-long-password').status_code == 302
    assert client.get('/account').status_code == 403
    assert client.post('/account', data={'csrf': 'bad'}).status_code == 403
    change_user(store, admin, viewer['id'], 'viewer', 0)
    assert client.get('/_dash-layout').status_code == 401
    assert login(client, 'health-user', 'another-long-password').status_code == 200
    assert client.get('/_dash-layout').status_code == 401


def dash_action(webapp, client, trigger, **states):
    key = next(k for k in webapp.callback_map if 'm-message.children' in k)
    callback = webapp.callback_map[key]
    inputs = [{**i, 'value': states.get(i['id'] + '.' + i['property'], states.get(i['id'], 1 if i['id'] == trigger else None))} for i in callback['inputs']]
    state = [{**s, 'value': states.get(s['id'] + '.' + s['property'], states.get(s['id']))} for s in callback['state']]
    return client.post('/_dash-update-component', json={'output': key,
        'outputs': [{'id': o.component_id, 'property': o.component_property} for o in callback['output']],
        'inputs': inputs, 'state': state, 'changedPropIds': [trigger + '.' + next(i['property'] for i in callback['inputs'] if i['id'] == trigger)]})


def test_forged_viewer_callbacks_and_admin_workflow(webapp, store, users):
    client = webapp.server.test_client()
    login(client, 'health-user', 'another-long-password')
    raw = 'data:text/csv;base64,' + base64.b64encode(frame().to_csv(index=False).encode()).decode()
    response = dash_action(webapp, client, 'm-upload', **{'m-upload': raw})
    assert 'Permission denied' in response.get_data(as_text=True)
    assert not store.pending()
    for action in ('m-activate', 'm-run', 'm-save-note', 'm-cancel', 'm-reject'):
        response = dash_action(webapp, client, action)
        assert 'Permission denied' in response.get_data(as_text=True)
    login(client)
    response = dash_action(webapp, client, 'm-upload', **{'m-upload.contents': raw, 'm-upload.filename': 'test.csv'})
    assert response.status_code == 200
    candidate = response.json['response']['m-pending-choice']['data']
    assert store.active() is None
    response = dash_action(webapp, client, 'm-activate', **{'m-candidate': candidate})
    assert 'Monthly dataset activated' in response.get_data(as_text=True)
    assert store.active()['blocks'][0]['eligible']
    assert client.post('/_dash-update-component', json={}, headers={'Origin': 'https://attacker.invalid'}).status_code == 403


def test_no_legacy_imports_in_entrypoint():
    from pathlib import Path
    content = Path('app.py').read_text()
    assert 'from dashboard.weekly' not in content
    assert 'from dashboard.monthly.ui import install' in content


def test_expired_login_form_recovers_without_authenticating(webapp):
    client = webapp.server.test_client()
    response = client.post('/login', data={'username': 'researcher', 'password': 'a-long-test-password', 'csrf': 'stale'})
    assert response.status_code == 303
    assert response.headers['Location'] == '/login?expired=1'
    assert client.get('/_dash-layout').status_code == 401
    fresh = client.get(response.headers['Location'])
    assert b'sign-in form expired' in fresh.data
    assert fresh.headers['Cache-Control'] == 'no-store'
    assert webapp.server.config['SESSION_COOKIE_NAME'] == 'antipolo_monthly_session'
    assert login(client).status_code == 302
    assert client.get('/_dash-layout').status_code == 200


def test_login_recovery_does_not_allow_cross_origin_posts(webapp):
    client = webapp.server.test_client()
    client.get('/login')
    with client.session_transaction() as session:
        csrf = session['csrf']
    response = client.post('/login', data={'username': 'researcher', 'password': 'a-long-test-password', 'csrf': csrf},
                           headers={'Origin': 'https://attacker.invalid'})
    assert response.status_code == 403
    assert client.get('/_dash-layout').status_code == 401
