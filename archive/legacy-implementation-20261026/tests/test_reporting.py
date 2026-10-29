"""Report calculations, stale-data guards and exported evidence parity."""
from io import BytesIO

import pdfplumber
import pytest

from dashboard.weekly.reporting import build_report, report_pdf, weekly_cells
from dashboard.weekly.reporting_ui import download, report_view


def fixture(disease='Dengue', baseline=10):
    active = {'id': 'report-test', 'context': 'Synthetic / Demo Data',
              'metadata': {'population': '5-19', 'location': 'Antipolo City', 'reporting_status': 'complete'},
              'records': [{'disease': disease, 'year': 2025, 'morbidity_week': w, 'case_count': n, **extra}
                          for w, n, extra in [(3, 999, {'reporting_status': 'incomplete'}), (2, baseline, {}), (1, 2, {})]]}
    result = {'dataset_id': active['id'], 'disease': disease, 'issued_at': '2026-10-13T00:00:00Z',
              'hybrid': [10, 15, 5, 20] * 13, 'context': 'Synthetic / Demo Data',
              'forecast_index': [{'horizon_week': i + 1, 'year': None, 'morbidity_week': None} for i in range(52)]}
    return active, result


def test_baseline_uses_latest_complete_week_not_latest_or_input_order():
    active, result = fixture()
    report = build_report(active, result, 'Dengue', 4)
    assert report['baseline'] == 10
    assert report['baseline_week'] == '2025 W02'
    assert [r['change'] for r in report['rows']] == [0, 5, -5, 10]
    assert report['rows'][1]['percent'] == 50
    assert '2 of 4' in report['summary']
    assert 'Forecast week +4' in report['summary']
    assert report['sources'] and report_view(report)


def test_zero_baseline_and_unsupported_disease():
    active, result = fixture('Other disease', 0)
    report = build_report(active, result, 'Other disease', 4)
    assert all(row['percent'] is None for row in report['rows'])
    assert weekly_cells(report)[0][3] == 'N/A'
    assert not report['sources']
    assert 'No verified' in report['actions'][1]['finding']


@pytest.mark.parametrize('change', [dict(dataset_id='old'), dict(disease='Other'), dict(hybrid=None), dict(hybrid=[float('nan')] * 52)])
def test_rejects_stale_or_invalid_forecasts(change):
    active, result = fixture()
    with pytest.raises(ValueError):
        build_report(active, {**result, **change}, 'Dengue', 4)


def test_pdf_contains_all_weeks_scope_sources_and_paginated_plan():
    active, result = fixture('Measles-Rubella')
    report = build_report(active, result, 'Measles-Rubella', 52)
    data = report_pdf(report)
    with pdfplumber.open(BytesIO(data)) as pdf:
        text = '\n'.join(page.extract_text() or '' for page in pdf.pages)
        assert len(pdf.pages) >= 3
        assert all(f'Page {i + 1}' in page.extract_text() for i, page in enumerate(pdf.pages))
    for expected in ['Synthetic / Demo Data', 'Population: 5-19', 'Forecast week +52', 'Recommendations', '48 hours', 'References', 'doh.gov.ph']:
        assert expected in text
    assert data.startswith(b'%PDF-')


def test_export_refuses_report_after_forecast_changes():
    active, result = fixture()
    report = build_report(active, result, 'Dengue', 4)
    changed = {**result, 'hybrid': [20] * 52}
    response, message = download(1, report, active, {'Dengue': changed}, 'Dengue', 4)
    assert 'outdated' in message.children


def test_no_complete_baseline_blocks_report():
    active, result = fixture()
    active['metadata']['reporting_status'] = 'unknown'
    with pytest.raises(ValueError, match='No complete'):
        build_report(active, result, 'Dengue', 4)
