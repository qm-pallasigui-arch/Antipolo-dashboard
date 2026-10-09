"""Revision 45 protocol, evidence and retrospective scoring acceptance."""
import copy
import pytest
from dashboard.weekly import model, ui
from dashboard.weekly.protocol import exploratory_configuration, EXPLORATORY_LABEL
from dashboard.weekly.settings import model_configuration
from dashboard.weekly.transform import prepare, update_facts
from tests.test_transformation import upload_csv
from tests.test_weekly import dataset


def test_installed_decision90_protocol_supersedes_exploratory(monkeypatch):
    monkeypatch.delenv('WEEKLY_MODEL_CONFIG', raising=False)
    c = model_configuration()
    assert model.validate_config(c)
    assert c['version'] == 'weekly-decision-90-v1' and c['approved']
    assert len(c['candidates']) == 144
    assert all(x['seasonal_order'][-1] == 52 for x in c['candidates'])
    assert c['lag_windows'] == [3, 6, 12, 26, 52]
    assert c['hidden_nodes_grid'] == [2, 3, 5, 8]
    c['candidates'].clear()
    assert len(model_configuration()['candidates']) == 144


def test_horizon_scoring_same_positions_no_holdout_leak(monkeypatch):
    active = dataset([{'disease': 'Measles', 'year': 2020 + i // 52, 'morbidity_week': i % 52 + 1,
                       'case_count': None if i == 209 else i % 5} for i in range(260)],
                     year_lengths={str(y): 52 for y in range(2020, 2027)})
    calls = []
    def fake(values, steps, config):
        calls.append(copy.deepcopy(values))
        return {'hybrid': [1] * steps, 'sarima': [2] * steps,
                'hybrid_status': 'Available', 'sarima_status': 'Available', 'diagnostics': {}}
    monkeypatch.setattr(model, 'fit_models', fake)
    result = model.run(active, 'Measles', exploratory_configuration())
    assert len(calls[0]) == 260 and len(calls[1]) == 208
    for h in (4, 13, 26, 52):
        evidence = result['horizon_metrics'][str(h)]
        assert evidence['scored_weeks'] == h - 1 and evidence['excluded_missing_actuals'] == 1
        assert evidence['metrics']['hybrid'] and evidence['metrics']['sarima']
    assert result['configuration_label'] == EXPLORATORY_LABEL
    assert result['context'] == 'Technical / Retrospective Evaluation'


def test_documented_completeness_and_calendar_required():
    d = prepare(upload_csv('Disease,Year,Week,Cases\nDengue,2025,1,2'))
    with pytest.raises(ValueError, match='documentation reference'):
        update_facts(d, {'reporting_status': 'complete'})
    with pytest.raises(ValueError, match='documentation reference'):
        update_facts(d, {'calendar:2025': 52})
    revised = update_facts(d, {'reporting_status': 'complete', 'reporting_reference': 'CESU document A',
                               'calendar:2025': 52, 'calendar_reference': 'CESU calendar B'})
    assert revised['metadata']['reporting_status'] == 'complete'
    assert d['metadata'].get('reporting_status') != 'complete'


@pytest.mark.parametrize('action,value,expected', [('zero', None, 0), ('corrected', 7, 7), ('missing', None, None)])
def test_individual_blank_resolutions_retain_original_and_survive_prepare(action, value, expected):
    source = upload_csv('Disease,Year,Week,Cases\nDengue,2025,1,\nDengue,2025,2,2')
    d = prepare(source)
    facts = {'resolution:0': action, 'corrected:0': value, 'evidence:0': 'CESU source correction A'}
    revised = update_facts(d, facts)
    assert revised['records'][0]['case_count'] == expected
    assert d['records'][0]['case_count'] is None
    decision = next(iter(revised['metadata']['blank_resolutions'].values()))
    assert decision['original']['case_count'] is None
    replayed = prepare(source, metadata=revised['metadata'])
    assert replayed['records'][0]['case_count'] == expected
    assert revised['worksheet_units'][0]['records'][0]['case_count'] == expected


def test_nonexistent_week_requires_calendar_and_preserves_evidence():
    d = prepare(upload_csv('Disease,Year,Week,Cases\nDengue,2025,52,2\nDengue,2025,53,'))
    facts = {'resolution:1': 'nonexistent', 'evidence:1': 'Source correction'}
    with pytest.raises(ValueError, match='calendar evidence'):
        update_facts(d, facts)
    revised = update_facts(d, {**facts, 'calendar:2025': 52, 'calendar_reference': 'CESU calendar'})
    assert len(revised['records']) == 1 and not revised['quality']['errors']
    assert len(revised['transformation']['source']['sheets'][0]['rows']) == 2
    assert 'nonexistent' in str(ui.transformation_review(revised))


def test_source_completeness_not_fabricated_by_protocol():
    active = dataset(reporting_status='unknown')
    result = model.run(active, 'Measles', exploratory_configuration())
    assert not result['hybrid'] and 'No complete' in result['failure_reason']


def test_edit_active_source_information_stages_copy_and_preserves_cancel():
    active = dataset(reporting_status='unknown')
    pending, opened = ui.edit_source_information(1, active)
    assert opened and pending == active and pending is not active
    pending['metadata']['reporting_reference'] = 'Source document'
    assert 'reporting_reference' not in active['metadata']
    current, discarded, opened, _ = ui.transition('w-cancel', None, pending, active)
    assert current is active and discarded is None and not opened


def test_failed_confirmation_does_not_rebuild_or_erase_form(monkeypatch):
    from types import SimpleNamespace
    from dash import no_update
    monkeypatch.setattr(ui, 'ctx', SimpleNamespace(triggered_id='w-activate'))
    source = upload_csv('Disease,Year,Week,Cases\nDengue,2025,1,2')
    pending = prepare(source)
    response = ui.manage_dataset(source, 0, 1, 0, 0, 0, 0, 0, 0, [], pending, pending, 'Data',
                                 [], [], [], [], [{'type': 'w-fact', 'field': 'reporting_status'}], ['complete'], [])
    assert response[0] is no_update and response[1] is no_update and response[2] is no_update
    assert 'documentation reference' in str(response[4])
    assert response[5] is no_update


def test_confirmation_reports_calendar_conflict_without_generic_error():
    source = upload_csv('Disease,Year,Week,Cases\nDengue,2025,53,2')
    pending = prepare(source)
    with pytest.raises(ValueError, match='week 53 conflicts'):
        ui.transition('w-activate', source, pending, None, declarations={
            'calendar:2025': 52, 'calendar_reference': 'Test reference'})


def test_unchanged_source_facts_reuse_validation(monkeypatch):
    from dashboard.weekly import transform
    pending = prepare(upload_csv('Disease,Year,Week,Cases\nDengue,2025,1,2'))
    def unexpected(*args, **kwargs):
        raise AssertionError('Unchanged confirmation must reuse validated data')
    monkeypatch.setattr(transform, 'validate', unexpected)
    assert update_facts(pending, {}) is pending


def test_source_fact_update_does_not_retransform_workbook(monkeypatch):
    from dashboard.weekly import transform
    pending = prepare(upload_csv('Disease,Year,Week,Cases\nDengue,2025,1,2'))
    def unexpected(*args, **kwargs):
        raise AssertionError('Metadata update must not transform source sheets again')
    monkeypatch.setattr(transform, 'transform_sheet', unexpected)
    updated = update_facts(pending, {'reporting_status': 'complete', 'reporting_reference': 'Test source'})
    assert updated['records'] == pending['records']
    assert not updated['quality']['excluded_from_training']
    assert updated['transformation']['source'] == pending['transformation']['source']


def test_checks_are_only_built_when_expanded(monkeypatch):
    def unexpected(*args, **kwargs):
        raise AssertionError('Closed checks should not create hidden tables')
    monkeypatch.setattr(ui, 'quality_details', unexpected)
    assert ui.review_checks(False, dataset(), True, None) == ''
