import base64
import io

import pandas as pd
import pytest
from dash import no_update

from dashboard.callbacks.data_callbacks import load_data, confirm_pending_upload, transition_data_session
from dashboard.callbacks.view_callbacks import render_upload_summary, render_upload_confirmation, update_aggregate_section


def payload():
    return 'data:text/csv;base64,' + base64.b64encode(
        b'year,month,disease,cases\n2025,1,Dengue,10\n2025,1,Malaria,500\n').decode()


def test_upload_cannot_activate_without_explicit_confirmation():
    old, _, old_summary = load_data(None, None, None)
    store, _, summary, pending = transition_data_session('upload-csv', payload(), 'malaria.csv', old, old_summary)
    assert store is no_update and summary is no_update
    assert confirm_pending_upload(pending)[0] is no_update
    assert 'Malaria' not in set(pd.read_json(io.StringIO(old), orient='split').disease)
    new, _, active_summary, cleared = transition_data_session(
        'confirm-upload-catalog', payload(), 'malaria.csv', old, old_summary,
        pending=pending, confirm_clicks=1)
    assert cleared is None and 'pending_confirmation' not in active_summary
    frame = pd.read_json(io.StringIO(new), orient='split')
    assert frame.groupby('disease').cases.sum().idxmax() == 'Malaria'
    assert 'Malaria' in str(update_aggregate_section(new, [2025, 2025], 'all')[0])


def test_malaria_visible_in_full_confirmation_table_before_activation():
    store, _, pending = load_data(payload(), 'malaria.csv', None)
    assert store is no_update
    rendered = render_upload_summary(None, pending)
    tables = [c for c in rendered if getattr(c, 'data', None)]
    assert [row['disease'] for row in tables[0].data] == ['Dengue', 'Malaria']
    assert tables[0].page_size == 2
    assert 'Awaiting confirmation' in str(rendered)
    assert render_upload_confirmation(pending) == ('Use these 2 diseases', False)


@pytest.mark.parametrize('trigger', [None, 'reset-session-data', 'upload-csv'])
def test_old_confirmation_click_does_not_approve_new_upload(trigger):
    old, _, summary = load_data(None, None, None)
    _, _, pending = load_data(payload(), 'malaria.csv', old)
    store, _, _, staged = transition_data_session(trigger, payload(), 'malaria.csv', old, summary,
                                                   pending=pending, confirm_clicks=7)
    if store is not no_update:
        assert 'Malaria' not in set(pd.read_json(io.StringIO(store), orient='split').disease)
    if trigger == 'reset-session-data':
        assert staged is None


def test_rejected_replacement_clears_previous_candidate_and_preserves_active():
    old, _, summary = load_data(None, None, None)
    _, _, pending = load_data(payload(), 'malaria.csv', old)
    store, _, active, failed = transition_data_session('upload-csv', payload(), 'bad.pdf', old, summary,
                                                       pending=pending)
    assert store is no_update and active is no_update
    assert confirm_pending_upload(failed, confirmed=True)[0] is no_update
    assert render_upload_confirmation(failed)[1] is True


def test_upload_before_initial_load_keeps_sample_active():
    store, _, summary, pending = transition_data_session('upload-csv', payload(), 'malaria.csv', None, None)
    assert summary['uploaded'] is False
    assert 'Malaria' not in set(pd.read_json(io.StringIO(store), orient='split').disease)
    assert pending['pending_confirmation']


def test_xlsx_and_pdf_icd_categories_require_confirmation():
    frame = pd.DataFrame({'year':[2025]*12, 'month':[1]*12,
                          'disease':['Malaria', 'A90 Dengue', 'Pediculosis'] + [f'Category {i}' for i in range(9)],
                          'cases':[1]*12})
    buffer = io.BytesIO()
    frame.to_excel(buffer, index=False)
    contents = 'data:application/octet-stream;base64,' + base64.b64encode(buffer.getvalue()).decode()
    store, _, pending = load_data(contents, 'converted.xlsx', None)
    assert store is no_update
    rendered = render_upload_summary(None, pending)
    table = next(c for c in rendered if getattr(c, 'data', None))
    assert len(table.data) == 12 and table.page_size == 12
    assert {r['disease'] for r in table.data} == set(frame.disease)
    active, _, _ = confirm_pending_upload(pending, confirmed=True)
    assert set(pd.read_json(io.StringIO(active), orient='split').disease) == set(frame.disease)


def test_registered_http_flow_requires_confirmation(capsys):
    from evidence.reproduce_upload import run
    run()
    assert 'PASS: Malaria is visible for approval' in capsys.readouterr().out
