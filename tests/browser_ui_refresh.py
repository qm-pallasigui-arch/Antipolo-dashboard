"""Desktop/mobile acceptance checks against the running local preview."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.browser-tools'))
from playwright.sync_api import sync_playwright, expect


def run():
    evidence = ROOT / 'evidence' / 'ui-refresh-2026-10-09'
    evidence.mkdir(exist_ok=True)
    errors, checks = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch(channel='msedge', headless=True)
        page = browser.new_page(viewport={'width': 1440, 'height': 1000})
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto('http://127.0.0.1:8065/')
        expect(page.get_by_role('tab', name='Overview', exact=True)).to_be_visible()
        expect(page.locator('#w-dataset-badge')).to_have_text('No dataset loaded')
        page.get_by_role('tab', name='Overview', exact=True).focus()
        page.keyboard.press('ArrowRight')
        expect(page.locator('#w-page-title')).to_have_text('Forecast')
        expect(page.get_by_role('tab', name='Forecast', exact=True)).to_be_focused()
        assert page.get_by_role('tab', name='Forecast', exact=True).evaluate("el => getComputedStyle(el).outlineStyle") != 'none'
        page.keyboard.press('End')
        expect(page.locator('#w-page-title')).to_have_text('About')
        page.keyboard.press('Home')
        expect(page.locator('#w-page-title')).to_have_text('Overview')
        checks.append('Arrow/Home/End keyboard navigation and visible focus')
        page.get_by_role('tab', name='Data', exact=True).click()
        page.locator('#w-upload input[type=file]').set_input_files({
            'name': 'weekly.csv', 'mimeType': 'text/csv',
            'buffer': b'Disease,Year,Week,Cases\nDengue,2025,1,2\nDengue,2025,2,3'})
        expect(page.get_by_role('dialog')).to_be_visible()
        expect(page.locator('.before-after .numeric-card')).to_have_count(2)
        for name, width, height in [('desktop', 1440, 1000), ('mobile', 390, 844)]:
            page.set_viewport_size({'width': width, 'height': height})
            values = page.locator('.before-after .card-value').evaluate_all(
                "els => els.map(el => [getComputedStyle(el).fontSize, getComputedStyle(el).fontWeight])")
            assert values == [['28px', '700'], ['28px', '700']], values
            page.screenshot(path=str(evidence / f'upload-{name}.png'), full_page=True)
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        page.locator('#w-modal-title').focus()
        page.keyboard.press('Shift+Tab')
        assert page.evaluate("!!document.activeElement.closest('[role=dialog]')")
        page.get_by_role('button', name='Confirm & Use Data', exact=True).click()
        expect(page.get_by_role('dialog')).not_to_be_visible()
        expect(page.locator('#w-dataset-badge')).to_have_text('Uploaded data')
        checks.append('Upload review: matching 28px counts, mobile fit, focus trap, confirmation')
        for name, width, height in [('desktop', 1440, 1000), ('mobile', 390, 844)]:
            page.set_viewport_size({'width': width, 'height': height})
            for label in ['Overview', 'Forecast', 'Trends', 'Data', 'About']:
                page.get_by_role('tab', name=label, exact=True).click()
                expect(page.locator('#w-page-title')).to_have_text(label)
                if label in ['Overview', 'Forecast', 'Trends']:
                    expect(page.locator('#w-content .js-plotly-plot').first).to_be_visible(timeout=20000)
                expect(page.get_by_role('tab', name=label, exact=True)).to_have_attribute('aria-selected', 'true')
                assert page.locator('h1').count() == 1
                assert 'WAPE' not in page.locator('body').inner_text()
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), (name, label)
                for tab in page.get_by_role('tab').all():
                    box = tab.bounding_box()
                    assert box['x'] >= 0 and box['x'] + box['width'] <= width
                page.screenshot(path=str(evidence / f'{label.lower()}-{name}.png'), full_page=True)
            page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            assert page.locator('.primary-navigation').bounding_box()['y'] >= 0
        checks.append('All five pages: desktop/mobile, active tabs, no overflow, sticky navigation')
        page.get_by_role('tab', name='Data', exact=True).click()
        page.get_by_role('button', name='Try Synthetic / Demo Data', exact=True).click()
        expect(page.get_by_role('dialog')).to_be_visible()
        page.get_by_role('button', name='Confirm & Use Data', exact=True).click()
        expect(page.locator('#w-dataset-badge')).to_have_text('Demo data')
        checks.append('Dataset badge accurately distinguishes uploaded and demo records')
        assert not errors, errors
        browser.close()
    (evidence / 'browser-report.json').write_text(json.dumps({'checks': checks, 'page_errors': errors}, indent=2))
    print(json.dumps({'checks': checks, 'page_errors': errors}, indent=2))


if __name__ == '__main__':
    run()
