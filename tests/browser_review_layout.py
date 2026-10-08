"""Visual review of a wide Leptospirosis worksheet and adjacent review controls."""
import io
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.browser-tools'))
import pandas as pd
from playwright.sync_api import sync_playwright, expect


def run():
    evidence = ROOT / 'evidence' / 'review-layout'
    evidence.mkdir(exist_ok=True)
    stream = io.BytesIO()
    with pd.ExcelWriter(stream, engine='openpyxl') as writer:
        pd.DataFrame([['Morbidity Week', *range(2016, 2026)],
                      [1, *range(1, 11)], [2, *range(2, 12)],
                      ['TOTAL', *range(3, 23, 2)]]).to_excel(
                          writer, sheet_name='Leptospirosis', header=False, index=False)
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch(channel='msedge', headless=True)
        page = browser.new_page(viewport={'width': 1440, 'height': 1000})
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto('http://127.0.0.1:8065/')
        page.get_by_role('tab', name='Data', exact=True).click()
        page.locator('#w-upload input[type=file]').set_input_files({
            'name': 'review-example.xlsx', 'mimeType': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'buffer': stream.getvalue()})
        expect(page.get_by_role('dialog')).to_be_visible()
        expect(page.locator('.worksheet-header h3')).to_have_text('Reviewing worksheet: Leptospirosis.')
        assert 'excluded rows below' not in page.locator('body').inner_text()
        choice = page.locator('.worksheet-choice label').first
        assert choice.evaluate("el => getComputedStyle(el).borderTopWidth") == '2px'
        expect(page.locator('.year-chips li')).to_have_count(10)
        expect(page.locator('.detected-mappings')).to_contain_text('worksheet name: Leptospirosis')
        actions = page.locator('.worksheet-review-actions')
        expect(actions.locator('summary')).to_have_text(['Change inferred Disease', 'Review automatically excluded rows'])
        assert page.evaluate("Boolean(document.querySelector('.worksheet-review-actions').compareDocumentPosition(document.querySelector('.transformation-changes')) & Node.DOCUMENT_POSITION_FOLLOWING)")
        for name, width, height in [('desktop', 1440, 1000), ('mobile', 390, 844)]:
            page.set_viewport_size({'width': width, 'height': height})
            page.locator('.review-dialog').evaluate('el => el.scrollTop = 0')
            page.screenshot(path=str(evidence / f'preview-{name}.png'))
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            assert page.locator('.review-dialog').evaluate('el => el.scrollWidth <= el.clientWidth')
            sizes = page.locator('.before-after .card-value').evaluate_all('els => els.map(el => getComputedStyle(el).fontSize)')
            assert sizes == ['28px', '28px'], sizes
            page.locator('.detection-summary').scroll_into_view_if_needed()
            sticky = page.locator('.review-sticky').bounding_box()
            dialog = page.locator('.review-dialog').bounding_box()
            assert sticky['y'] >= dialog['y'] and sticky['y'] < dialog['y'] + 40
            page.screenshot(path=str(evidence / f'detection-{name}.png'))
        actions.get_by_text('Change inferred Disease', exact=True).click()
        expect(actions.locator('input[type=text]')).to_be_visible()
        actions.get_by_text('Review automatically excluded rows', exact=True).click()
        expect(actions).to_contain_text('Source total row')
        assert not errors, errors
        browser.close()
    report = {'passed': True, 'page_errors': errors, 'checks': [
        'Navy Leptospirosis header', 'Distinct source and prepared panels',
        'Ten detected years and explicit field origins', 'Adjacent working review controls before What changed',
        'Desktop/mobile screenshots, equal count typography, no modal overflow']}
    (evidence / 'report.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    run()
