"""Every supplied calendar conflict must have an actionable review control."""
import pytest

from dashboard.weekly import calendar, transform, ui
from tests.test_transformation import upload_csv
from tests.test_weekly_views import _walk


def fields(pending):
    return {node.id['field'] for node in _walk(ui.fact_fields(pending))
            if isinstance(getattr(node, 'id', None), dict) and node.id.get('type') == 'w-fact'}


@pytest.mark.parametrize('decision', ['include', 'exclude'])
def test_zero_count_conflict_is_reviewable_alongside_positive_disease(decision):
    source = upload_csv('Disease,Year,Week,Cases\nDengue,2024,52,2\nDengue,2024,53,0\nMeasles-Rubella,2024,52,1\nMeasles-Rubella,2024,53,5')
    pending = transform.prepare(source, metadata={'year_lengths': {'2024': 52}})
    conflicts = calendar.has_week_three(pending['records'], {'2024': 52})
    assert {pending['records'][i]['disease'] for i in conflicts} == {'Dengue', 'Measles-Rubella'}
    assert all(f'conflict:{i}' in fields(pending) for i in conflicts)
    index = next(i for i in conflicts if pending['records'][i]['disease'] == 'Dengue')
    with pytest.raises(ValueError, match='source evidence'):
        transform.update_facts(pending, {f'conflict:{index}': decision})
    revised = transform.update_facts(pending, {f'conflict:{index}': decision, f'conflict_evidence:{index}': 'CESU source review'})
    assert not any('Dengue: supplied week 53' in e for e in revised['quality']['errors'])
    assert any(r['disease'] == 'Dengue' and r['morbidity_week'] == 53 for r in revised['records']) == (decision == 'include')
    replayed = transform.prepare(source, metadata=revised['metadata'])
    assert replayed['records'] == revised['records']
    assert pending['records'][index]['case_count'] == 0


def test_confirmed_zero_from_blank_still_offers_calendar_review():
    source = upload_csv('Disease,Year,Week,Cases\nDengue,2024,52,2\nDengue,2024,53,')
    pending = transform.prepare(source)
    key = ('Dengue', 53, 'week53-absent')
    revised = transform.update_facts(pending, {
        transform.group_field('group_resolution', key): 'zero',
        transform.group_field('group_evidence', key): 'Source confirms zero',
    })
    assert any('supplied week 53 conflicts' in e for e in revised['quality']['errors'])
    assert 'conflict:1' in fields(revised)
    assert not transform.group_blank_cells(revised['records'], {'2024': 52})


def test_confirm_stages_new_conflicts_and_allows_resolution_before_activation():
    years = [2016, 2017, 2018, 2019, 2021, 2022, 2023, 2024]
    source = upload_csv('Disease,Year,Week,Cases\n' + '\n'.join(
        f'Dengue,{year},{week},{count}' for year in years for week, count in [(52, '2'), (53, '')]))
    pending = transform.prepare(source)
    key = ('Dengue', 53, 'week53-absent')
    facts = {transform.group_field('group_resolution', key): 'zero',
             transform.group_field('group_evidence', key): 'Source confirms zero'}
    active, revised, opened, message = ui.transition('w-activate', source, pending, None, declarations=facts)
    assert active is None and opened is True
    assert 'saved in this review' in message
    conflicts = calendar.has_week_three(revised['records'], revised['metadata']['year_lengths'])
    assert len(conflicts) == 8
    assert all(f'conflict:{i}' in fields(revised) for i in conflicts)
    assert ui.review(True, revised, None, source)[4] is True, 'Confirm disabled until conflicts resolved'
    decisions = {f'{prefix}:{i}': value for i in conflicts for prefix, value in
                 [('conflict', 'exclude'), ('conflict_evidence', 'Source confirms week does not exist')]}
    active, ready, opened, _ = ui.transition('w-apply-facts', source, revised, None, declarations=decisions)
    assert active is None and not ready['quality']['errors']
    active, cleared, opened, _ = ui.transition('w-activate', source, ready, None)
    assert not opened and cleared is None and len(active['records']) == 8
    assert len(pending['records']) == 16
