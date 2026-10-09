"""Desktop/mobile source-calendar and activation-banner browser checks."""
import os
from pathlib import Path
import subprocess
import sys
import time
import json
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
EVIDENCE = ROOT / 'evidence' / 'calendar-ux' / os.environ.get('CALENDAR_BROWSER_RUN', time.strftime('%Y%m%d-%H%M%S'))


def serve():
    import app
    from tests.test_calendar_ux import pending_calendar
    pending = pending_calendar()
    pending['context'] = 'Synthetic / Demo Data'
    pending['metadata']['dataset_type'] = 'synthetic'
    def initialize(node):
        if getattr(node, 'id', None) == 'w-pending':
            node.data = pending
        if getattr(node, 'id', None) == 'w-modal-open':
            node.data = True
        children = getattr(node, 'children', None)
        for child in children if isinstance(children, (list, tuple)) else [children]:
            if child is not None:
                initialize(child)
    initialize(app.dash_app.layout)
    app.dash_app.run(host='127.0.0.1', port=8068, debug=False)


def browser():
    sys.path.insert(0, str(ROOT / '.browser-tools'))
    from playwright.sync_api import sync_playwright, expect
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    with (EVIDENCE / 'server.log').open('w', encoding='utf-8') as log:
        process = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), '--serve'], cwd=ROOT,
                                   env={**os.environ, 'CALENDAR_BROWSER_RUN': EVIDENCE.name}, stdout=log, stderr=log,
                                   creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        try:
            for _ in range(100):
                try:
                    urlopen('http://127.0.0.1:8068/healthz', timeout=1).close()
                    break
                except OSError:
                    time.sleep(.1)
            with sync_playwright() as p:
                browser = p.chromium.launch(channel='msedge', headless=True)
                page = browser.new_page(viewport={'width': 1280, 'height': 900})
                errors = []
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.on('response', lambda response: errors.append(f'{response.status}: {response.url}') if response.status >= 400 else None)
                page.goto('http://127.0.0.1:8068')
                page.locator('summary').filter(has_text='Reporting calendar').click()
                cards = page.locator('.calendar-year-card')
                expect(cards).to_have_count(11)
                grid = page.locator('.calendar-year-grid')
                grid.scroll_into_view_if_needed()
                rows = cards.evaluate_all('(nodes) => new Set(nodes.map(n => Math.round(n.getBoundingClientRect().top))).size')
                assert rows == 3, rows
                assert len(grid.evaluate('(node) => getComputedStyle(node).gridTemplateColumns').split()) == 4
                page.get_by_role('button', name='Set all to 53', exact=True).click()
                expect(cards.filter(has_text='53 wk')).to_have_count(11)
                page.get_by_role('button', name='Set all to 52', exact=True).click()
                expect(cards.filter(has_text='52 wk')).to_have_count(11)
                page.set_viewport_size({'width': 1280, 'height': 1200})
                grid.scroll_into_view_if_needed()
                grid.screenshot(path=str(EVIDENCE / 'desktop-calendar.png'))
                page.get_by_role('button', name='Apply Source Information', exact=True).click()
                expect(page.locator('#w-review-message')).to_contain_text('documentation reference')
                page.set_viewport_size({'width': 390, 'height': 844})
                grid.scroll_into_view_if_needed()
                assert len(grid.evaluate('(node) => getComputedStyle(node).gridTemplateColumns').split()) == 2
                assert grid.evaluate('(node) => node.scrollWidth <= node.clientWidth')
                page.screenshot(path=str(EVIDENCE / 'mobile-calendar.png'))
                page.locator('input[id*="calendar_reference"]').fill('Synthetic calendar evidence fixture; covers 2016-2026')
                page.get_by_role('button', name='Confirm & Use Data', exact=True).click()
                expect(page.locator('#w-modal')).not_to_be_visible()
                expect(page.locator('.activation-notice')).to_be_visible()
                expect(page.locator('.activation-notice')).to_contain_text('Dataset activated')
                page.locator('.activation-notice').scroll_into_view_if_needed()
                page.screenshot(path=str(EVIDENCE / 'activation-mobile.png'))
                page.get_by_role('button', name='Open Forecast', exact=True).click()
                expect(page.locator('#w-page-title')).to_have_text('Forecast')
                page.get_by_role('button', name='Dismiss dataset activation notification').click()
                expect(page.locator('.activation-notice')).to_have_count(0)
                assert not errors, errors
                (EVIDENCE / 'checks.json').write_text(json.dumps({'desktop_rows': rows, 'desktop_columns': 4,
                    'mobile_columns': 2, 'bulk_52_and_53': True, 'evidence_gate': True, 'activation_banner': True,
                    'open_forecast': True, 'dismiss': True, 'errors': errors}, indent=2), encoding='utf-8')
                browser.close()
                print(EVIDENCE)
        finally:
            process.terminate()
            process.wait(timeout=10)


if __name__ == '__main__':
    serve() if '--serve' in sys.argv else browser()
