"""Revision 39 source recognition, review and activation integrity."""
import base64
import copy
import io
import json

import pandas as pd
import pytest

from dashboard.weekly.data import activate, demo
from dashboard.weekly.outputs import export_frame
from dashboard.weekly.transform import MappingNeeded, prepare, read_source, update_facts


def upload_csv(text):
    return read_source('data:text/csv;base64,' + base64.b64encode(text.encode()).decode(), 'records.csv')


def upload_book(sheets):
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        for name, rows in sheets.items():
            pd.DataFrame(rows).to_excel(writer, sheet_name=name, header=False, index=False)
    return read_source('data:;base64,' + base64.b64encode(buffer.getvalue()).decode(), 'surveillance.xlsx')


@pytest.mark.parametrize('header', ['disease,year,morbidity_week,case_count', 'Diagnosis,Reporting Year,Week No,Total Cases'])
def test_csv_automatic_mapping_and_values(header):
    d = prepare(upload_csv(header + '\nMeasles,2025,1,0\nMeasles,2025,2,\nMeasles,2025,4,8\nMeasles,2025,53,4'))
    assert [r['case_count'] for r in d['records']] == [0, None, 8, 4]
    assert d['records'][-1]['morbidity_week'] == 53
    assert d['quality']['missing_weeks'] and d['quality']['week53']
    assert d['transformation']['source']['sheets'][0]['original_row_count'] == 4
    assert d['transformation']['sheets'][0]['mapping']['case_count'] == header.split(',')[-1]


def test_legacy_week_by_year_multisheet():
    source = upload_book({'Leptospirosis': [['Surveillance report', '', ''], ['Morbidity Week', 2024, 2025],
                                          [1, 0, 2], [2, '', 3], [53, 4, 5], ['TOTAL', 4, 10]],
                          'Measles-Rubella': [['Week', 2025], [1, 9], [53, 0]]})
    d = prepare(source)
    assert len(d['records']) == 8
    assert set(d['quality']['diseases']) == {'Leptospirosis', 'Measles-Rubella'}
    assert len(d['quality']['week53']) == 3
    assert len(d['quality']['blank_observations']) == 1
    assert d['transformation']['sheets'][0]['excluded_rows'][0]['reason'].startswith('Source total')
    assert d['transformation']['sheets'][0]['method'] == 'week_by_year'
    assert not any('month' in r for r in d['records'])


def test_wide_table_with_total_column_not_double_counted():
    source = upload_book({'Measles': [['Week', 2024, 2025, 'Total'], [1, 2, 3, 5]]})
    d = prepare(source)
    assert len(d['records']) == 2 and sum(r['case_count'] for r in d['records']) == 5
    assert 'Total' in d['transformation']['sheets'][0]['unused_columns']


def test_sheet_disease_with_long_rows():
    source = upload_book({'Leptospirosis': [['Year', 'Week', 'Cases'], [2025, 1, 2]]})
    assert prepare(source)['records'][0]['disease'] == 'Leptospirosis'


def test_conflicting_sheet_name_requires_explicit_choice():
    source = upload_book({'Measles': [['Disease', 'Year', 'Week', 'Cases'], ['Measles-Rubella', 2025, 1, 2]]})
    with pytest.raises(MappingNeeded):
        prepare(source)
    d = prepare(source, {'0': {'mapping': {'disease': 'Disease'}}})
    assert d['records'][0]['disease'] == 'Measles-Rubella'
    assert d['transformation']['sheets'][0]['warnings']
    assert d['transformation']['sheets'][0]['choices']['mapping']['disease'] == 'Disease'


def test_generic_sheet_name_never_invents_disease():
    source = upload_book({'Sheet1': [['Year', 'Week', 'Cases'], [2025, 1, 2]]})
    with pytest.raises(MappingNeeded):
        prepare(source)
    d = prepare(source, {'0': {'mapping': {'disease': '__entered__'}, 'disease': 'Measles'}})
    assert d['records'][0]['disease'] == 'Measles'
    assert 'supplied during review' in ' '.join(d['transformation']['sheets'][0]['changes'])


def test_unknown_layout_manual_mapping_and_samples():
    source = upload_csv('A,B,C,D\nMeasles,2025,1,3')
    assert source['sheets'][0]['needs_mapping']
    assert source['sheets'][0]['rows'][0]['A'] == 'Measles'
    with pytest.raises(MappingNeeded):
        prepare(source)
    mapped = {'disease': 'A', 'year': 'B', 'morbidity_week': 'C', 'case_count': 'D'}
    d = prepare(source, {'0': {'mapping': mapped}})
    assert d['records'][0]['case_count'] == 3
    assert d['transformation']['source'] == source


def test_ambiguous_case_columns_not_silently_selected():
    source = upload_csv('Disease,Year,Week,Cases,Total Cases\nMeasles,2025,1,3,9')
    with pytest.raises(MappingNeeded):
        prepare(source)
    d = prepare(source, {'0': {'mapping': {'case_count': 'Cases'}}})
    assert d['records'][0]['case_count'] == 3
    assert 'Total Cases' in d['transformation']['sheets'][0]['unused_columns']


def test_mapping_cannot_reuse_source_column():
    source = upload_csv('A,B,C,D\nMeasles,2025,1,3')
    with pytest.raises(MappingNeeded, match='different source column'):
        prepare(source, {'0': {'mapping': {'disease': 'A', 'year': 'B', 'morbidity_week': 'C', 'case_count': 'C'}}})


@pytest.mark.parametrize('value', ['54', '0', '-1', 'not a week'])
def test_invalid_weeks_are_not_filtered_away(value):
    source = upload_book({'Measles': [['Week', 2025], [1, 2], [value, 3]]})
    with pytest.raises(ValueError, match='morbidity_week'):
        prepare(source)


def test_duplicate_weeks_detected_after_unpivot():
    d = prepare(upload_book({'Measles': [['Week', 2025], [1, 2], [1, 3]]}))
    assert d['quality']['duplicates']
    with pytest.raises(ValueError):
        activate(d)


def test_duplicate_year_headers_retain_both_counts_and_block_activation():
    d = prepare(upload_book({'Measles': [['Week', 2025, 2025], [1, 2, 3]]}))
    assert [r['case_count'] for r in d['records']] == [2, 3]
    assert d['quality']['duplicates']
    with pytest.raises(ValueError):
        activate(d)


def test_metadata_never_fabricated_by_recognition():
    d = prepare(upload_book({'Leptospirosis': [['Week', 2025], [1, 2]]}))
    for field in ('population', 'case_classification', 'source_system', 'dataset_type', 'reporting_status'):
        assert d['metadata'].get(field) is None
    assert not d['eligible'] and len(d['quality']['excluded_from_training']) == 1
    assert d['metadata']['source_file'] == 'surveillance.xlsx'


def test_optional_source_metadata_detected_without_broadening():
    d = prepare(upload_csv('Disease,Year,Week,Cases,Age Group,Classification,Reporting Status\nMeasles,2025,1,2,all-age,suspected,incomplete'))
    assert d['metadata']['population'] == 'all-age'
    assert d['metadata']['case_classification'] == 'suspected'
    assert not d['eligible'] and d['records'][0]['case_count'] == 2


def test_confirmation_cancellation_and_reopen():
    from dashboard.weekly import ui
    current = demo()
    original = copy.deepcopy(current)
    source = upload_csv('Disease,Year,Week,Cases\nMeasles,2025,1,2')
    active, pending, opened, _ = ui.transition('w-source', source, None, current)
    assert active == current == original and opened
    review = ui.review(opened, pending, current, source)
    assert 'Original Uploaded Data' in str(review[1]) and 'Prepared Weekly Data' in str(review[1])
    active, discarded, opened, _ = ui.transition('w-cancel', source, pending, current)
    assert active == original and discarded is None and not opened
    active, _, opened, _ = ui.transition('w-activate', source, pending, current)
    assert not opened and active['transformation']['source'] == source
    _, _, mode, _ = ui.transition('w-reopen', source, None, active)
    reopened = ui.review(mode, None, active, source)
    assert 'Original Uploaded Data' in str(reopened[1]) and reopened[4] is True


def test_manual_history_reopens_as_review_not_mapping():
    from dashboard.weekly import ui
    source = upload_csv('A,B,C,D\nMeasles,2025,1,2')
    d = prepare(source, {'0': {'mapping': dict(zip(LABELS_FOR_TEST, ['A', 'B', 'C', 'D']))}})
    active = activate(d)
    review = ui.review('history', None, active, source)
    assert review[2] == '' and 'Original Uploaded Data' in str(review[1])


LABELS_FOR_TEST = ['disease', 'year', 'morbidity_week', 'case_count']


def test_user_facts_preserve_row_conflicts_and_original():
    d = prepare(upload_csv('Disease,Year,Week,Cases,Age Group\nMeasles,2025,1,2,all-age'))
    source = copy.deepcopy(d['transformation']['source'])
    changed = update_facts(d, {'population': '5–19', 'case_classification': 'confirmed'})
    assert not changed['eligible']
    assert changed['records'][0]['population'] == 'all-age'
    assert changed['transformation']['source'] == source


def test_transformation_export_traceability():
    d = prepare(upload_csv('Disease,Year,Week,Cases\nMeasles,2025,1,2'))
    frame = export_frame(d)
    assert json.loads(frame.transformation_provenance.iloc[0])[0]['mapping']['case_count'] == 'Cases'
    assert d['metadata']['source_file_sha256'] == d['transformation']['source']['file_sha256']


def test_no_normal_json_editors():
    from dashboard.weekly.ui import build_layout
    def walk(component):
        if isinstance(component, (list, tuple)):
            for child in component:
                yield from walk(child)
        elif hasattr(component, 'to_plotly_json'):
            yield component
            yield from walk(getattr(component, 'children', None))
    components = list(walk(build_layout()))
    assert not any(type(c).__name__ == 'Textarea' for c in components)
    text = ' '.join(str(c.children) for c in components if isinstance(getattr(c, 'children', None), str))
    for forbidden in ['pre-weekly JSON', 'metadata dash', 'weekly-notice', 'cache signature', 'canonical', 'w-active']:
        assert forbidden not in text


def test_legacy_active_real_dataset_not_relabelled_demo():
    from tests.test_weekly import dataset
    from dashboard.weekly.ui import transformation_review
    displayed = str(transformation_review(dataset()))
    assert 'Synthetic / Demo Data' not in displayed
    assert 'not available' in displayed


def test_reporting_calendar_declarations_are_explicit():
    d = prepare(upload_csv('Disease,Year,Week,Cases\nMeasles,2025,53,2'))
    assert not d['metadata'].get('year_lengths')
    reviewed = update_facts(d, {'calendar:2025': 53, 'calendar:2026': 52, 'calendar_reference': 'Test source calendar'})
    assert reviewed['metadata']['year_lengths'] == {'2025': 53, '2026': 52}
    assert reviewed['records'][0]['morbidity_week'] == 53
    assert update_facts(d, {'calendar:2025': 52, 'calendar_reference': 'Test source calendar'})['quality']['errors']


def test_monthly_counts_cannot_be_manually_relabelled_weekly():
    source = upload_csv('Disease,Year,Month,Cases\nMeasles,2025,1,20')
    with pytest.raises(MappingNeeded, match='Monthly or quarterly'):
        prepare(source, {'0': {'mapping': {'morbidity_week': 'Month'}}})


def test_absent_dynamic_field_ids_do_not_break_new_upload(monkeypatch):
    from types import SimpleNamespace
    from dashboard.weekly import ui
    monkeypatch.setattr(ui, 'ctx', SimpleNamespace(triggered_id='w-source'))
    source = upload_csv('Disease,Year,Week,Cases\nMeasles,2025,1,2')
    response = ui.manage_dataset(source, 0, 0, 0, 0, 0, 0, 0, 0, [], None, None, 'Data',
                                 [None], [None], [None], [None], [None], [None], [])
    assert response[1]['records'] and response[2] is True


def test_installed_study_requirements_cannot_fabricate_source_facts(tmp_path, monkeypatch):
    from dashboard.weekly.settings import research_requirements
    path = tmp_path / 'research.json'
    path.write_text(json.dumps({'population': '5–19', 'case_classification': 'confirmed'}), encoding='utf-8')
    monkeypatch.setenv('WEEKLY_RESEARCH_CONFIG', str(path))
    with pytest.raises(ValueError, match='administrator'):
        research_requirements()


def test_eligible_source_can_use_installed_documented_study_requirements(tmp_path, monkeypatch):
    from dashboard.weekly import ui
    path = tmp_path / 'research.json'
    path.write_text(json.dumps({'approved_diseases': ['Measles'],
                               'weekly_protocol': {'approved': True, 'approval_reference': 'Test fixture only', 'minimum_complete_weeks': 1}}), encoding='utf-8')
    monkeypatch.setenv('WEEKLY_RESEARCH_CONFIG', str(path))
    source = upload_csv('Disease,Year,Week,Cases,Population,Classification,Source,Reporting Status,Dataset Type,City,Provenance\nMeasles,2025,1,2,5-19,confirmed,CESU/PIDSAR,complete,real,Antipolo City,Test source reference')
    _, pending, _, _ = ui.transition('w-source', source, None, None)
    assert pending['eligible']


def test_worksheet_scope_independent_previews_and_nondata_defaults():
    source = upload_book({'Measles': [['Week', 2025], [1, 0], [3, 2]],
                          'Notes': [['Instructions'], ['Read before use']],
                          'Sheet1': [['Year', 'Week', 'Cases'], [2025, 1, 4]]})
    pending = prepare(source, allow_partial=True)
    assert pending['review_only']
    assert [u['status'] for u in pending['worksheet_units']] == ['ready', 'excluded', 'needs_mapping']
    assert pending['worksheet_units'][0]['records'][0]['case_count'] == 0
    assert 'Sheet1' in pending['review_message']
    ready = prepare(source, {'2': {'included': False}})
    assert {r['disease'] for r in ready['records']} == {'Measles'}
    assert ready['quality']['missing_weeks']
    assert activate(ready)['records'] == ready['records']
    with pytest.raises(ValueError):
        activate(pending)


def test_only_missing_fields_and_plausible_disease_options():
    from dashboard.weekly.ui import mapping_fields, column_options
    source = upload_book({'Sheet1': [['Week', 2025, 2026], [1, 0, 1], [2, 1, 1]]})
    sheet = source['sheets'][0]
    assert sheet['kind'] == 'week_by_year'
    assert sheet['unresolved'] == ['disease']
    fields = str(mapping_fields(sheet, 0, {}))
    assert 'Required' in fields and 'unresolved-field' in fields
    assert 'Choose Reporting year' not in fields
    options = column_options(sheet, 'disease')
    assert {o['value'] for o in options} == {'__worksheet__', '__entered__'}
    ready = prepare(source, {'0': {'mapping': {'disease': '__worksheet__'}}})
    assert len(ready['records']) == 4
    assert {r['disease'] for r in ready['records']} == {'Sheet1'}


def test_excluding_every_sheet_blocks_activation():
    source = upload_csv('Disease,Year,Week,Cases\nMeasles,2025,1,2')
    pending = prepare(source, {'0': {'included': False}}, allow_partial=True)
    assert pending['review_only'] and 'Include at least one' in pending['review_message']


def test_invalid_sheet_errors_name_the_sheet_and_can_be_excluded():
    source = upload_book({'Measles': [['Week', 2025], [1, 2]],
                          'Dengue': [['Week', 2025], [99, 3]]})
    pending = prepare(source, allow_partial=True)
    assert 'Dengue' in str(pending['worksheet_units'][1]['errors'])
    ready = prepare(source, {'1': {'included': False}})
    assert not ready['quality']['errors']


def test_stale_include_selection_cannot_activate():
    from dashboard.weekly.ui import transition
    source = upload_csv('Disease,Year,Week,Cases\nMeasles,2025,1,2')
    pending = prepare(source)
    with pytest.raises(ValueError, match='selection changed'):
        transition('w-activate', source, pending, None, {'0': {'included': False}})


def test_verification_footer_excluded_with_reviewable_warning():
    source = upload_book({'Dengue': [['Week', 2024, 2025], [1, 0, 3], [53, '', 2],
                                    ['Source-reported total (for verification):', 0, 5]]})
    ready = prepare(source)
    assert len(ready['records']) == 4
    assert [r['case_count'] for r in ready['records']] == [0, None, 3, 2]
    report = ready['transformation']['sheets'][0]
    assert report['excluded_rows'] == [{'row': 4, 'reason': 'Source total row, not a weekly observation'}]
    assert any('Automatic fix:' in warning for warning in report['warnings'])
    from dashboard.weekly.ui import transformation_review
    displayed = str(transformation_review(ready, True))
    assert 'Automatic fixes applied' in displayed and 'Review automatically excluded rows' in displayed


def test_invalid_wide_week_reports_original_row_not_expanded_indices():
    source = upload_book({'Dengue': [['Week', 2024, 2025], [1, 0, 3], ['unknown', 4, 2]]})
    pending = prepare(source, allow_partial=True)
    message = pending['worksheet_units'][0]['errors'][0]
    assert 'source rows [3]' in message and 'unknown' in message
    assert 'No week numbers were guessed' in message
    from dashboard.weekly.ui import transformation_review
    assert 'Action needed before confirmation' in str(transformation_review(pending, True))


def test_local_surveillance_workbook_verification_footers():
    from pathlib import Path
    path = Path('reconciliation/sources/Antipolo_Disease_Surveillance_2016-2025.xlsx')
    if not path.exists():
        pytest.skip('Local source workbook not present')
    source = read_source('data:;base64,' + base64.b64encode(path.read_bytes()).decode(), path.name)
    ready = prepare(source)
    assert not ready.get('review_only') and not ready['quality']['errors']
    assert {'Dengue', 'Measles-Rubella'} <= set(ready['quality']['diseases'])
    assert activate(ready)['records']
