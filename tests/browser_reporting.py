"""Reporting workflow smoke test against a local server; forecast fixture avoids fitting."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from playwright.sync_api import sync_playwright, expect
from dashboard.weekly.data import demo


def run():
    active = demo()
    result = {'dataset_id': active['id'], 'disease': 'Demo disease', 'hybrid': [10, 25, 30, 20] * 13,
              'context': 'Synthetic / Demo Data', 'issued_at': '2026-10-13T00:00:00Z',
              'forecast_index': [{'year': 2026, 'morbidity_week': i + 1, 'horizon_week': i + 1} for i in range(52)]}
    evidence = ROOT / 'evidence' / 'reporting'
    evidence.mkdir(exist_ok=True)
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch(channel='msedge', headless=True)
        page = browser.new_page(viewport={'width': 1440, 'height': 1000})
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto('http://127.0.0.1:8073/')
        page.get_by_role('tab', name='Reporting', exact=True).click()
        page.get_by_role('button', name='Generate Report', exact=True).click()
        expect(page.locator('#w-report-body')).to_contain_text('Upload and confirm')
        page.evaluate("data => window.dash_clientside.set_props('w-active', {data})", active)
        expect(page.locator('#w-report-disease')).to_contain_text('Demo disease')
        page.get_by_role('button', name='Generate Report', exact=True).click()
        expect(page.locator('#w-report-body')).to_contain_text('Generate a forecast')
        page.evaluate("data => window.dash_clientside.set_props('w-result', {data})", {'Demo disease': result})
        page.get_by_role('button', name='Generate Report', exact=True).click()
        expect(page.locator('.report-briefing')).to_contain_text('4-week outlook')
        expect(page.locator('.report-table tbody tr')).to_have_count(4)
        expect(page.locator('#w-report-chart .main-svg').first).to_be_visible(timeout=20000)
        page.screenshot(path=str(evidence / 'desktop.png'), full_page=True)
        page.locator('#w-report-horizon input[value="52"]').check()
        expect(page.locator('#w-report-pdf')).to_be_disabled()
        page.get_by_role('button', name='Generate Report', exact=True).click()
        expect(page.locator('.report-table tbody tr')).to_have_count(52)
        with page.expect_download() as download:
            page.get_by_role('button', name='Export PDF', exact=True).click()
        download.value.save_as(str(evidence / 'outlook-52-weeks.pdf'))
        page.set_viewport_size({'width': 390, 'height': 844})
        page.evaluate('window.scrollTo(0, 0)')
        page.wait_for_function('document.documentElement.scrollWidth <= window.innerWidth', timeout=10000)
        page.screenshot(path=str(evidence / 'mobile.png'), full_page=True)
        page.screenshot(path=str(evidence / 'mobile-top.png'))
        page.get_by_role('button', name='Open Forecast', exact=True).click()
        expect(page.locator('#w-page-title')).to_have_text('Forecast')
        page.get_by_role('button', name='Open Reporting', exact=True).click()
        expect(page.locator('#w-page-title')).to_have_text('Reporting')
        page.evaluate("data => window.dash_clientside.set_props('w-result', {data})", {})
        expect(page.locator('#w-report-pdf')).to_be_disabled()
        assert not errors, errors
        browser.close()
    print('Reporting browser checks passed: empty state, missing forecast, 4/52-week reports, PDF, mobile, navigation, invalidation.')


if __name__ == '__main__':
    run()
