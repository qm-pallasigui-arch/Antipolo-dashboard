"""Actionable empty/failure states and stable worksheet selection scrolling."""
import io
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.browser-tools'))
import pandas as pd
from playwright.sync_api import sync_playwright, expect


def run():
    evidence = ROOT / 'evidence' / 'navigation-followup'
    evidence.mkdir(exist_ok=True)
    stream = io.BytesIO()
    with pd.ExcelWriter(stream, engine='openpyxl') as writer:
        for name in ['Dengue', 'Leptospirosis', 'Measles']:
            pd.DataFrame([['Week', 2025], *[[w, w] for w in range(1, 10)]]).to_excel(
                writer, sheet_name=name, header=False, index=False)
    errors, offsets = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch(channel='msedge', headless=True)
        page = browser.new_page(viewport={'width': 1440, 'height': 1000})
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto('http://127.0.0.1:8065/')
        for label in ['Overview', 'Forecast', 'Trends']:
            page.get_by_role('tab', name=label, exact=True).click()
            page.get_by_role('button', name='Go to data upload', exact=True).click()
            expect(page.locator('#w-page-title')).to_have_text('Data')
            expect(page.locator('#w-upload')).to_be_focused()
        page.locator('#w-upload input[type=file]').set_input_files({
            'name': 'sample.xlsx', 'mimeType': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'buffer': stream.getvalue()})
        expect(page.get_by_role('dialog')).to_be_visible()
        for width, height in [(1440, 1000), (390, 844)]:
            page.set_viewport_size({'width': width, 'height': height})
            card = page.locator('[data-worksheet-index="1"]')
            for value in ['exclude', 'include']:
                choice = card.locator('input[value=' + value + ']')
                choice.scroll_into_view_if_needed()
                top = card.bounding_box()['y']
                choice.check()
                expect(card).to_have_class('worksheet-card worksheet-excluded' if value == 'exclude' else 'worksheet-card')
                page.wait_for_timeout(250)
                delta = abs(card.bounding_box()['y'] - top)
                offsets.append(delta)
                assert delta < 40, (width, value, delta)
                assert page.locator('.review-dialog').evaluate('el => el.scrollTop') > 100
            assert card.locator('.worksheet-choice label').first.bounding_box()['height'] <= 48
            page.screenshot(path=str(evidence / f'choices-{width}.png'))
        page.get_by_role('button', name='Confirm & Use Data', exact=True).click()
        expect(page.get_by_role('dialog')).not_to_be_visible()
        page.get_by_role('tab', name='Forecast', exact=True).click()
        page.get_by_role('button', name='Generate Forecast', exact=True).click()
        expect(page.locator('.forecast-action-panel')).to_contain_text('No weeks are established as complete', timeout=15000)
        page.screenshot(path=str(evidence / 'forecast-action-mobile.png'), full_page=True)
        page.get_by_role('button', name='Update source information', exact=True).click()
        expect(page.locator('#w-page-title')).to_have_text('Data')
        expect(page.get_by_role('dialog')).to_be_visible()
        expect(page.locator('#w-fact-panel > h3')).to_be_focused()
        heading = page.locator('#w-fact-panel > h3').bounding_box()
        bar = page.locator('.review-sticky').bounding_box()
        assert heading['y'] >= bar['y'] + bar['height']
        page.screenshot(path=str(evidence / 'source-shortcut-mobile.png'))
        assert not errors, errors
        browser.close()
    report = {'passed': True, 'worksheet_position_deltas_px': offsets,
              'upload_shortcuts': ['Overview', 'Forecast', 'Trends'],
              'source_shortcut_focus': True, 'page_errors': errors}
    (evidence / 'report.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    run()
