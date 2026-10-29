"""Guard against oversized component trees and unnecessary database work."""
import json
from plotly.utils import PlotlyJSONEncoder
from dash import dash_table
from dashboard.monthly.components import table
from dashboard.monthly.security import create_user
from dashboard.monthly.store import Store
from dashboard.monthly.views import page_content
from tests.test_monthly_system import frame


def test_large_tables_keep_all_values_but_bound_rendered_rows():
    rows = [dict(year=2025, consultation_count=i + .1234567, observation_status='observed') for i in range(840)]
    component = table(rows)
    grid = next(c for c in component.children if isinstance(c, dash_table.DataTable))
    assert grid.page_size == 25
    assert grid.data[-1]['consultation_count'] == rows[-1]['consultation_count']
    assert len(grid.data) == 840
    payload = json.dumps(component, cls=PlotlyJSONEncoder)
    assert len(payload) < 130000
    assert payload.count('dash_html_components') < 10


def test_non_forecast_pages_do_not_read_forecast_history(tmp_path, monkeypatch):
    store = Store(tmp_path / 'state.sqlite3')
    uid = create_user(store, 'researcher', 'long-test-password', bootstrap=True)
    user = dict(id=uid, username='researcher', role='admin', active=1)
    pending = store.stage(user, frame().to_csv(index=False).encode(), 'synthetic.csv')
    store.activate(user, pending['candidate_id'])
    dataset = store.active()
    def unexpected(*args):
        raise AssertionError('Unrelated page loaded forecast history')
    monkeypatch.setattr(store, 'latest_forecast', unexpected)
    for page in ('Data & Quality', 'Disease Trends', 'Reports', 'Notifications', 'Help & About'):
        page_content(store, user, page, dataset, 'A00-A09')


def test_poll_signal_changes_on_updates_but_not_reads(tmp_path):
    store = Store(tmp_path / 'state.sqlite3')
    uid = create_user(store, 'researcher', 'long-test-password', bootstrap=True)
    user = dict(id=uid, username='researcher', role='admin', active=1)
    token = store.state_token(user)
    assert token == store.state_token(user)
    store.notify('report', 'Ready', 'Report ready.', 'Reports', user_id=uid)
    assert token != store.state_token(user)
    token = store.state_token(user)
    store.mark_read(user)
    assert token != store.state_token(user)
    assert store.unread_count(user) == 0
