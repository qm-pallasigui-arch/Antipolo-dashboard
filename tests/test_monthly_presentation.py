"""Presentation contracts that protect interpretation and authorization."""
from dashboard.monthly.charts import trend_figure
from dashboard.monthly.components import format_number
from dashboard.monthly.store import Store
from dashboard.monthly.security import create_user


def test_intervals_are_never_invented():
    values = [{'month': '2026-01', 'consultation_count': 10}]
    figure = trend_figure({'observations': []}, 'A00-A09', {'forecast_values': values})
    assert not any(trace.fill == 'tonexty' for trace in figure.data)
    values[0].update(lower=7, upper=14)
    figure = trend_figure({'observations': []}, 'A00-A09', {'forecast_values': values})
    assert any(trace.fill == 'tonexty' for trace in figure.data)
    values[0]['lower'] = 12
    figure = trend_figure({'observations': []}, 'A00-A09', {'forecast_values': values})
    assert not any(trace.fill == 'tonexty' for trace in figure.data)


def test_read_selection_cannot_mark_hidden_notifications(tmp_path):
    store = Store(tmp_path / 'state.sqlite3')
    uid = create_user(store, 'researcher', 'long-test-password', bootstrap=True)
    viewer_id = create_user(store, 'viewer', 'long-viewer-password', actor={'id': uid, 'role': 'admin', 'active': 1})
    viewer = {'id': viewer_id, 'role': 'viewer', 'active': 1}
    store.notify('report', 'Report ready', 'Your report is ready.', 'Reports', user_id=viewer_id)
    store.notify('data', 'Dataset updated', 'The dataset changed.', 'Data & Quality')
    visible = store.notifications(viewer)
    store.mark_read(viewer, [visible[0]['id'], 1])
    assert sum(bool(n['read_at']) for n in store.notifications(viewer)) == 1
    with store.connect() as db:
        assert db.execute('SELECT count(*) FROM notification_reads WHERE notification_id=1 AND user_id=?', (viewer_id,)).fetchone()[0] == 0


def test_counts_are_readable_without_rounding_small_errors_to_zero():
    assert format_number(662.9724112233368, 'projected_total') == '663.0'
    assert format_number(.0001, 'mae') == '<0.001'
    assert format_number(None) == 'Unavailable'
