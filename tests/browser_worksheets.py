"""Browser regression for independent worksheet review."""
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / '.browser-tools'), str(ROOT)]
import pandas as pd
from playwright.sync_api import sync_playwright, expect


def run():
    evidence = ROOT / 'evidence' / 'worksheet-review'
    evidence.mkdir(parents=True, exist_ok=True)
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        for name, rows in {'Measles': [['Week', 2025], [1, 0], [3, 2]],
                           'Notes': [['Instructions'], ['Read before use']],
                           'Sheet1': [['Week', 2025], [1, 4]]}.items():
            pd.DataFrame(rows).to_excel(writer, sheet_name=name, header=False, index=False)
    log = (evidence / 'server.log').open('w')
    server = subprocess.Popen([sys.executable, '-c', "import app; app.dash_app.run(host='127.0.0.1',port=8063,debug=False)"], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
    errors = []
    try:
        for _ in range(100):
            try:
                urllib.request.urlopen('http://127.0.0.1:8063/healthz', timeout=1)
                break
            except OSError:
                time.sleep(.1)
        with sync_playwright() as p:
            browser = p.chromium.launch(channel='msedge', headless=True)
            page = browser.new_page(viewport={'width': 1440, 'height': 1000})
            page.on('pageerror', lambda e: errors.append(str(e)))
            page.goto('http://127.0.0.1:8063/')
            page.get_by_text('Data', exact=True).first.click()
            page.locator('#w-upload input[type=file]').set_input_files({'name':'mixed.xlsx', 'mimeType':'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'buffer':buffer.getvalue()})
            cards = page.locator('.worksheet-card')
            expect(cards).to_have_count(3)
            expect(cards.nth(0).get_by_role('heading', name='Reviewing worksheet: Measles.')).to_be_visible()
            expect(cards.nth(1).get_by_text('Suggested: Exclude.', exact=False)).to_be_visible()
            expect(cards.nth(1).locator('input[value=exclude]')).to_be_checked()
            expect(cards.nth(2).locator('.unresolved-field')).to_have_count(1)
            expect(page.get_by_role('button', name='Confirm & Use Data', exact=True)).to_be_disabled()
            cards.nth(2).scroll_into_view_if_needed()
            page.screenshot(path=str(evidence / 'required-disease.png'))
            cards.nth(2).get_by_text('Choose Disease for Sheet1', exact=True).click()
            expect(page.get_by_text('Use worksheet name as Disease: Sheet1', exact=True)).to_be_visible()
            assert not page.get_by_role('option').filter(has_text='2025').count()
            page.keyboard.press('Escape')
            cards.nth(2).locator('input[value=exclude]').check()
            expect(page.get_by_role('button', name='Confirm & Use Data', exact=True)).to_be_enabled()
            expect(cards.nth(2).locator('.unresolved-field')).to_have_count(0)
            page.screenshot(path=str(evidence / 'excluded-ready.png'))
            cards.nth(0).locator('input[value=exclude]').check()
            expect(page.get_by_role('button', name='Confirm & Use Data', exact=True)).to_be_disabled()
            cards.nth(0).locator('input[value=include]').check()
            expect(page.get_by_role('button', name='Confirm & Use Data', exact=True)).to_be_enabled()
            page.get_by_role('button', name='Confirm & Use Data', exact=True).click()
            expect(page.get_by_role('dialog')).not_to_be_visible()
            active = page.evaluate("JSON.parse(sessionStorage.getItem('w-active'))")
            assert len(active['records']) == 2
            assert {r['disease'] for r in active['records']} == {'Measles'}
            assert active['records'][0]['case_count'] == 0
            assert not errors, errors
            browser.close()
        report = {'passed': True, 'checks': ['Three independent worksheet cards', 'Notes excluded by default', 'Only unresolved Disease requested and highlighted', 'Year columns filtered from Disease options', 'Exclude unresolved sheet enables activation', 'All excluded blocks activation', 'Only included records activated; zero preserved'], 'page_errors': errors}
        (evidence / 'results.json').write_text(json.dumps(report, indent=2))
        print(json.dumps(report, indent=2))
    finally:
        server.terminate()
        server.wait(timeout=20)
        log.close()

if __name__ == '__main__':
    run()
