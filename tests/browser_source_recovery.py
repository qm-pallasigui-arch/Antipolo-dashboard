"""Real-browser regression for failed source-information confirmation and retry."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.request
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / '.browser-tools'), str(ROOT)]
from playwright.sync_api import sync_playwright, expect


def run():
    evidence = ROOT / 'evidence' / 'source-recovery-2026-10-04'
    evidence.mkdir(parents=True, exist_ok=True)
    log = (evidence / 'server.log').open('w')
    # Delay only this test server's validation to make the busy state observable.
    command = "import time; import app; from dashboard.weekly import ui; original=ui.update_facts; ui.update_facts=lambda *a,**k: (time.sleep(0.8),original(*a,**k))[1]; app.dash_app.run(host='127.0.0.1',port=8064,debug=False)"
    server = subprocess.Popen([sys.executable, '-c', command], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                              creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
    errors = []
    try:
        for _ in range(100):
            try:
                urllib.request.urlopen('http://127.0.0.1:8064/healthz', timeout=1)
                break
            except OSError:
                time.sleep(.1)
        with sync_playwright() as p:
            browser = p.chromium.launch(channel='msedge', headless=True)
            page = browser.new_page(viewport={'width': 1440, 'height': 1000})
            page.on('pageerror', lambda e: errors.append(str(e)))
            page.goto('http://127.0.0.1:8064/')
            expect(page.locator('.outlook-header')).to_be_visible()
            page.screenshot(path=str(evidence / 'header-desktop.png'), full_page=True)
            page.get_by_text('Data', exact=True).first.click()
            page.locator('#w-upload input[type=file]').set_input_files({'name':'weekly.csv','mimeType':'text/csv',
                'buffer':b'Disease,Year,Week,Cases\nDengue,2025,1,2\nDengue,2025,2,3'})
            expect(page.get_by_role('dialog')).to_be_visible()
            page.get_by_role('button', name='Confirm & Use Data', exact=True).click()
            expect(page.get_by_role('dialog')).not_to_be_visible()
            before = page.evaluate("JSON.parse(sessionStorage.getItem('w-active'))")
            page.get_by_text('Data', exact=True).first.click()
            page.get_by_role('button', name='Update Source Information', exact=True).click()
            expect(page.get_by_role('dialog')).to_be_visible()
            expect(page.get_by_role('heading', name='1. Worksheets and preparation', exact=True)).to_be_visible()
            assert page.get_by_role('button', name='Review Details', exact=True).count() == 0
            assert page.evaluate("Boolean(document.getElementById('w-review-extra').compareDocumentPosition(document.getElementById('w-review-actions')) & Node.DOCUMENT_POSITION_FOLLOWING)")
            label = page.get_by_text('CESU/source evidence for historical completeness', exact=True)
            if not label.is_visible():
                page.get_by_text('2. Source information', exact=True).click()
            def field(name):
                identity = json.dumps({'field':name,'type':'w-fact'}, separators=(',',':'),sort_keys=True)
                return page.locator('[id=' + json.dumps(identity) + ']')
            field('reporting_status').click()
            page.get_by_text('Historical reporting period complete', exact=True).click()
            page.get_by_text('3. Data checks and research eligibility', exact=True).click()
            expect(page.get_by_role('heading', name='Research eligibility', exact=True)).to_be_visible()
            expect(field('reporting_status')).to_contain_text('Historical reporting period complete')
            page.get_by_text('3. Data checks and research eligibility', exact=True).click()
            page.get_by_role('button', name='Confirm & Use Data', exact=True).click()
            expect(page.locator('#w-review-progress')).to_have_text('Checking and applying your changes…')
            expect(page.get_by_role('button', name='Confirm & Use Data', exact=True)).to_be_disabled()
            expect(page.locator('#w-review-message')).to_contain_text('documentation reference')
            expect(field('reporting_status')).to_contain_text('Historical reporting period complete')
            expect(page.get_by_role('dialog')).to_be_visible()
            assert page.evaluate("JSON.parse(sessionStorage.getItem('w-active'))")['id'] == before['id']
            page.screenshot(path=str(evidence / 'error-preserves-form.png'))
            page.set_viewport_size({'width':390,'height':844})
            field('reporting_reference').fill('Test-only source confirmation')
            page.get_by_role('button', name='Confirm & Use Data', exact=True).click()
            expect(page.locator('#w-review-progress')).to_have_text('Checking and applying your changes…')
            expect(page.get_by_role('dialog')).not_to_be_visible(timeout=15000)
            active = page.evaluate("JSON.parse(sessionStorage.getItem('w-active'))")
            assert active['metadata']['reporting_status'] == 'complete'
            assert active['metadata']['reporting_reference'] == 'Test-only source confirmation'
            assert active['id'] != before['id']
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            page.screenshot(path=str(evidence / 'confirmed-mobile.png'),full_page=True)
            assert not errors, errors
            browser.close()
        report = {'passed':True,'checks':['Busy message and disabled confirmation during validation',
                  'Missing reference shows visible error without resetting selection','Failure preserves active dataset',
                  'Corrected reference confirms without reupload','Updated metadata persisted','Mobile page has no horizontal overflow'],
                  'page_errors':errors}
        (evidence / 'results.json').write_text(json.dumps(report,indent=2))
        print(json.dumps(report,indent=2))
    finally:
        server.terminate()
        server.wait(timeout=20)
        log.close()

if __name__ == '__main__':
    run()
