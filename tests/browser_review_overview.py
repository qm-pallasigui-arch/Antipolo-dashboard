"""Review summary, section navigation, and local check expansion."""
import io
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.browser-tools'))
import pandas as pd
from playwright.sync_api import sync_playwright, expect


def run():
    evidence = ROOT / 'evidence' / 'review-overview'
    evidence.mkdir(exist_ok=True)
    stream = io.BytesIO()
    with pd.ExcelWriter(stream, engine='openpyxl') as writer:
        for name in ['Leptospirosis', 'Dengue', 'Measles']:
            pd.DataFrame([['Week', 2024, 2025], [1, 2, None], [53, 1, 2]]).to_excel(
                writer, sheet_name=name, header=False, index=False)
        pd.DataFrame([['Instructions'], ['Source notes only']]).to_excel(
            writer, sheet_name='Notes', header=False, index=False)
    errors, requests = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch(channel='msedge', headless=True)
        page = browser.new_page(viewport={'width': 1440, 'height': 1000})
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.on('request', lambda request: requests.append(request.url) if '_dash-update-component' in request.url else None)
        page.goto('http://127.0.0.1:8065/')
        page.get_by_role('tab', name='Data', exact=True).click()
        page.locator('#w-upload input[type=file]').set_input_files({
            'name': 'review-overview.xlsx', 'mimeType': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'buffer': stream.getvalue()})
        expect(page.get_by_role('dialog')).to_be_visible()
        summary = page.locator('.review-overview')
        expect(summary.locator('.included-sheets')).to_contain_text('Included (3)')
        expect(summary.locator('.excluded-sheets')).to_contain_text('Notes')
        expect(summary).to_contain_text('No missing values were converted to zero.')
        expect(summary).to_contain_text('Blank values have not been changed to zero.')
        expect(page.locator('#w-review-extra-content')).to_contain_text('Research eligibility')
        assert page.evaluate("Boolean(document.querySelector('.review-overview').compareDocumentPosition(document.querySelector('#w-step-worksheets')) & Node.DOCUMENT_POSITION_FOLLOWING)")
        styles = page.locator('#w-step-worksheets, #w-fact-panel > .review-step, #w-review-extra > .review-step').evaluate_all(
            'els => els.map(el => [getComputedStyle(el).fontSize, getComputedStyle(el).fontWeight])')
        assert styles == [['18px', '700']] * 3, styles
        for name, width, height in [('desktop', 1440, 1000), ('mobile', 390, 844)]:
            page.set_viewport_size({'width': width, 'height': height})
            page.locator('.review-dialog').evaluate('el => el.scrollTop = 0')
            page.screenshot(path=str(evidence / f'overview-{name}.png'))
            assert page.locator('.review-dialog').evaluate('el => el.scrollWidth <= el.clientWidth')
            assert page.locator('#w-cancel').evaluate("el => getComputedStyle(el).borderTopStyle") == 'solid'
        # Allow earlier preparation requests to settle, then isolate expansion traffic.
        page.wait_for_timeout(300)
        before = len(requests)
        elapsed = page.evaluate('''() => {
            const started = performance.now();
            document.querySelector('[data-review-target="w-review-extra"]').click();
            return performance.now() - started;
        }''')
        expect(page.get_by_role('heading', name='Research eligibility', exact=True)).to_be_visible()
        page.locator('#w-review-extra > summary').click()
        page.locator('#w-review-extra > summary').click()
        page.wait_for_timeout(300)
        assert len(requests) == before, 'Opening/reopening must not send dataset requests'
        page.screenshot(path=str(evidence / 'checks-mobile.png'))
        page.locator('.review-dialog').evaluate('el => el.scrollTop = 0')
        summary.get_by_role('link', name='Leptospirosis', exact=True).click()
        expect(page.locator('#w-worksheet-0 h3')).to_be_focused()
        page.get_by_role('button', name='Cancel', exact=True).click()
        expect(page.get_by_role('dialog')).not_to_be_visible()
        assert page.evaluate("sessionStorage.getItem('w-active')") in (None, 'null')
        assert not errors, errors
        browser.close()
    report = {'passed': True, 'section_heading_styles': styles,
              'section_open_handler_ms': elapsed, 'expansion_server_requests': 0,
              'included': 3, 'excluded': 1, 'page_errors': errors}
    (evidence / 'report.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    run()
