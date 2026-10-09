"""Source-calendar editing must preserve explicit source-evidence rules."""
from types import SimpleNamespace

from dash import no_update
import pytest

from dashboard.weekly import ui
from dashboard.weekly.transform import prepare, update_facts
from tests.test_transformation import upload_csv


def pending_calendar():
    return prepare(upload_csv('Disease,Year,Week,Cases\n' + '\n'.join(f'Dengue,{year},1,2' for year in range(2016, 2026))))


def walk(node):
    if isinstance(node, (list, tuple)):
        for item in node:
            yield from walk(item)
    elif node is not None:
        yield node
        yield from walk(getattr(node, 'children', None))


def test_year_cards_include_forecast_year_and_existing_editable_choices():
    pending = pending_calendar()
    pending['metadata']['year_lengths'] = {'2020': 53}
    fields = list(walk(ui.fact_fields(pending)))
    cards = [item for item in fields if getattr(item, 'className', '') == 'calendar-year-card']
    assert len(cards) == 11
    assert 'Forecast year' in str(cards[-1]) and '2026' in str(cards[-1])
    calendar = {item.id['field']: item for item in fields if isinstance(getattr(item, 'id', None), dict)
                and item.id.get('field', '').startswith('calendar:')}
    assert calendar['calendar:2020'].value == 53
    assert calendar['calendar:2016'].value == ''
    assert all([option['value'] for option in item.options] == ['', 52, 53] for item in calendar.values())


@pytest.mark.parametrize('weeks', [52, 53])
def test_bulk_calendar_only_changes_year_fields(monkeypatch, weeks):
    monkeypatch.setattr(ui, 'ctx', SimpleNamespace(triggered_id={'type': 'w-calendar-bulk', 'weeks': weeks}))
    ids = [{'type': 'w-fact', 'field': name} for name in ('calendar:2016', 'population', 'calendar:2026', 'calendar_reference')]
    assert ui.bulk_calendar_values([1, 0], ids, ['', 'all-age', 53, 'evidence']) == [weeks, no_update, weeks, no_update]
    assert ui.bulk_calendar_values([0, 0], ids, ['', 'all-age', 53, 'evidence']) == [no_update] * 4


def test_bulk_requires_evidence_and_preserves_week53_conflicts():
    pending = prepare(upload_csv('Disease,Year,Week,Cases\nDengue,2025,53,56'))
    with pytest.raises(ValueError, match='documentation reference'):
        update_facts(pending, {'calendar:2025': 52})
    revised = update_facts(pending, {'calendar_reference': 'Source calendar document', 'calendar:2025': 52})
    assert revised['quality']['errors']
    assert revised['records'][0]['case_count'] == 56 and revised['records'][0]['morbidity_week'] == 53
    assert '2025' not in pending['metadata'].get('year_lengths', {})


def test_existing_calendar_can_be_changed_or_returned_to_unknown():
    pending = pending_calendar()
    first = update_facts(pending, {'calendar_reference': 'Source calendar document', 'calendar:2020': 53})
    revised = update_facts(first, {'calendar:2020': 52})
    assert revised['metadata']['year_lengths']['2020'] == 52
    unknown = update_facts(revised, {'calendar:2020': ''})
    assert '2020' not in unknown['metadata'].get('year_lengths', {})
    assert unknown['records'] == pending['records']
    assert first['metadata']['year_lengths']['2020'] == 53


def test_activation_banner_confirms_dataset_not_forecast_readiness():
    banner = ui.activation_notice(pending_calendar())
    assert banner.role == 'status' and banner.tabIndex == -1
    text = str(banner)
    assert 'Dataset activated' in text and '10 weekly records' in text
    assert 'Open Forecast' in text and 'Dismiss' in text
    assert 'check forecast availability' in text
    assert 'Your data are ready' not in text
