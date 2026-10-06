"""Run manually: python tests/browser_revision39.py (requires local Playwright).

Launches a local test server with an explicitly synthetic-only fixture protocol.
The fixture is not an approved methodology or a production default.
"""
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.browser-tools'))
sys.path.insert(0, str(ROOT))
from playwright.sync_api import sync_playwright, expect  # noqa: E402
import pandas as pd  # noqa: E402
from tests.test_weekly import protocol  # noqa: E402


def workbook():
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        pd.DataFrame([['Morbidity Week', 2025], [1, 0], [2, ''], [4, 7], [53, 2]]).to_excel(writer, sheet_name='Leptospirosis', header=False, index=False)
    return buffer.getvalue()


def run_browser():
    evidence = ROOT / 'evidence' / 'revision39'
    evidence.mkdir(parents=True, exist_ok=True)
    config = protocol()
    config['version'] = 'browser-test-synthetic-only'
    config['nnar_maxiter'] = 5000
    config_path = evidence / 'synthetic-test-protocol.json'
    config_path.write_text(json.dumps(config, indent=2), encoding='utf-8')
    environment = {**os.environ, 'WEEKLY_MODEL_CONFIG': str(config_path)}
    log = (evidence / 'browser-server.log').open('w', encoding='utf-8')
    server = subprocess.Popen([sys.executable, '-c', "import app; app.dash_app.run(host='127.0.0.1',port=8062,debug=False)"],
                              cwd=ROOT, env=environment, stdout=log, stderr=subprocess.STDOUT,
                              creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
    checks, errors = [], []
    try:
        for _ in range(100):
            try:
                urllib.request.urlopen('http://127.0.0.1:8062/healthz', timeout=1)
                break
            except OSError:
                time.sleep(.1)
        with sync_playwright() as p:
            browser = p.chromium.launch(channel='msedge', headless=True)
            page = browser.new_page(viewport={'width': 1440, 'height': 1000}, device_scale_factor=1)
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.goto('http://127.0.0.1:8062/')
            page.get_by_text('Data', exact=True).first.click()
            expect(page.get_by_role('heading', name='Upload Data')).to_be_visible()
            page.screenshot(path=str(evidence / 'desktop-data.png'), full_page=True)
            source_workbook = workbook()
            page.locator('#w-upload input[type=file]').set_input_files({'name': 'legacy-weekly.xlsx', 'mimeType': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'buffer': source_workbook})
            expect(page.get_by_role('dialog')).to_be_visible()
            expect(page.get_by_role('heading', name='Original Uploaded Data')).to_be_visible()
            expect(page.get_by_role('heading', name='Prepared Weekly Data')).to_be_visible()
            expect(page.get_by_text('Week 53 was preserved from the source data.', exact=True)).to_be_visible()
            page.screenshot(path=str(evidence / 'desktop-transformation.png'))
            checks.append('Legacy XLSX automatically opens original/prepared review with week 53 and blank/zero preservation.')
            page.get_by_text('2. Source information', exact=True).click()
            identifier = json.dumps({'field': 'reporting_status', 'type': 'w-fact'}, separators=(',', ':'), sort_keys=True)
            page.locator('[id=' + json.dumps(identifier) + ']').click()
            page.get_by_text('Historical reporting period complete', exact=True).last.click()
            reference_id = json.dumps({'field': 'reporting_reference', 'type': 'w-fact'}, separators=(',', ':'), sort_keys=True)
            page.locator('[id=' + json.dumps(reference_id) + ']').fill('Synthetic browser fixture source confirmation')
            page.get_by_role('button', name='Apply Source Information', exact=True).click()
            expect(page.get_by_text('Some reporting is incomplete or not specified.', exact=False)).not_to_be_visible()
            checks.append('Ordinary source-information fields update reporting completeness without a JSON editor.')
            blank_controls = page.get_by_text('Resolve blank counts individually (source evidence required)', exact=True)
            if not blank_controls.is_visible():
                page.get_by_text('2. Source information', exact=True).click()
            blank_controls.click()
            resolution_id = json.dumps({'field': 'resolution:1', 'type': 'w-fact'}, separators=(',', ':'), sort_keys=True)
            page.locator('[id=' + json.dumps(resolution_id) + ']').click()
            page.get_by_text('Confirmed zero', exact=True).click()
            evidence_id = json.dumps({'field': 'evidence:1', 'type': 'w-fact'}, separators=(',', ':'), sort_keys=True)
            page.locator('[id=' + json.dumps(evidence_id) + ']').fill('Synthetic fixture correction; week 2 confirmed zero')
            page.get_by_role('button', name='Apply Source Information', exact=True).click()
            expect(page.get_by_text('Source-supported blank-count decisions', exact=True)).to_be_visible()
            page.get_by_text('Source-supported blank-count decisions', exact=True).click()
            expect(page.get_by_text('Synthetic fixture correction; week 2 confirmed zero', exact=True)).to_be_visible()
            page.screenshot(path=str(evidence / 'blank-resolution.png'))
            checks.append('Individual blank resolution requires evidence and exposes a preserved source-supported decision.')
            page.keyboard.press('Escape')
            expect(page.get_by_role('dialog')).to_be_visible()
            page.get_by_role('button', name='Cancel', exact=True).click()
            expect(page.get_by_role('dialog')).not_to_be_visible()
            expect(page.get_by_text('No dataset is currently in use.', exact=True)).to_be_visible()
            checks.append('Escape does not dismiss review; Cancel leaves the empty/active context unchanged.')
            page.locator('#w-upload input[type=file]').set_input_files({'name': 'legacy-weekly.xlsx', 'mimeType': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'buffer': source_workbook})
            expect(page.get_by_role('dialog')).to_be_visible()
            page.get_by_role('button', name='Cancel', exact=True).click()
            expect(page.get_by_role('dialog')).not_to_be_visible()
            checks.append('The exact same file can be uploaded again after cancellation.')

            # A canonical but clearly synthetic source exercises successful model generation.
            text = 'Disease,Reporting Year,Week,Total Cases,Dataset Type,Reporting Status,Age Group\n'
            text += '\n'.join(f'Demo disease,2025,{i},{15 + i % 7},synthetic,complete,all-age' for i in range(1, 41))
            page.locator('#w-upload input[type=file]').set_input_files({'name': 'synthetic-weekly.csv', 'mimeType': 'text/csv', 'buffer': text.encode()})
            expect(page.get_by_role('dialog')).to_be_visible()
            page.get_by_role('button', name='Confirm & Use Data', exact=True).click()
            expect(page.get_by_role('dialog')).not_to_be_visible()
            expect(page.get_by_text('Active Dataset', exact=True)).to_be_visible()
            expect(page.locator('#w-content').get_by_text('synthetic-weekly.csv', exact=True)).to_be_visible()
            page.screenshot(path=str(evidence / 'desktop-overview.png'), full_page=True)
            checks.append('Confirmation activates reviewed data and navigates to Overview.')
            page.get_by_text('Forecast', exact=True).first.click()
            page.get_by_role('button', name='Generate Forecast', exact=True).click()
            expect(page.get_by_text('The highest projected count', exact=False)).to_be_visible(timeout=60000)
            original = page.evaluate("JSON.parse(sessionStorage.getItem('w-result'))")
            assert len(original['hybrid']) == 52 and len(original['sarima']) == 52
            page.get_by_text('Next 4 weeks', exact=True).click()
            expect(page.locator('#w-content')).to_contain_text('model-based projection')
            after = page.evaluate("JSON.parse(sessionStorage.getItem('w-result'))")
            assert original['issued_at'] == after['issued_at'] and original['hybrid'] == after['hybrid']
            page.screenshot(path=str(evidence / 'desktop-forecast.png'), full_page=True)
            checks.append('Synthetic-only fixture generates separate 52-point Hybrid/SARIMA paths; horizon change preserves original issue time and values.')

            page.get_by_text('Data', exact=True).first.click()
            page.get_by_role('button', name='View Transformation Details', exact=True).click()
            expect(page.get_by_role('heading', name='Original Uploaded Data')).to_be_visible()
            page.get_by_role('button', name='Close', exact=True).click()
            checks.append('Activated transformation history reopens without reactivating or retraining.')
            page.locator('#w-upload input[type=file]').set_input_files({'name': 'unknown.csv', 'mimeType': 'text/csv', 'buffer': b'A,B,C,D\nMeasles,2025,1,3\n'})
            expect(page.get_by_text('We could not identify all required fields automatically. Please help us match the columns.', exact=True).first).to_be_visible()
            for field, column in [('disease', 'A'), ('year', 'B'), ('morbidity_week', 'C'), ('case_count', 'D')]:
                # IDs are only used by automation, never shown as workflow labels.
                identifier = json.dumps({'field': field, 'sheet': 0, 'type': 'w-map'}, separators=(',', ':'), sort_keys=True)
                dropdown = page.locator('[id=' + json.dumps(identifier) + ']')
                dropdown.click()
                page.get_by_text(column + ' ·', exact=False).last.click()
            page.get_by_role('button', name='Apply Worksheet Changes', exact=True).click()
            expect(page.get_by_role('heading', name='Prepared Weekly Data')).to_be_visible()
            page.screenshot(path=str(evidence / 'desktop-manual-review.png'))
            page.get_by_role('button', name='Cancel', exact=True).click()
            expect(page.get_by_role('heading', name='synthetic-weekly.csv', exact=True)).to_be_visible()
            checks.append('Unknown layout uses dropdown matching; prepared replacement can be cancelled without changing active data.')

            page.get_by_text('About the Model', exact=True).first.click()
            expect(page.get_by_text('How the forecast works', exact=True)).to_be_visible()
            assert page.locator('textarea:visible').count() == 0
            assert page.locator('pre:visible').count() == 0
            page.screenshot(path=str(evidence / 'desktop-about.png'), full_page=True)
            checks.append('About page explains the model; configuration and diagnostics are collapsed, with no JSON editor.')
            page.set_viewport_size({'width': 390, 'height': 844})
            page.get_by_text('Data', exact=True).first.click()
            page.screenshot(path=str(evidence / 'mobile-data.png'), full_page=True)
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
            page.get_by_role('button', name='View Transformation Details', exact=True).click()
            expect(page.get_by_role('dialog')).to_be_visible()
            page.screenshot(path=str(evidence / 'mobile-transformation.png'))
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
            page.get_by_role('heading', name='Prepared Weekly Data').scroll_into_view_if_needed()
            page.screenshot(path=str(evidence / 'mobile-prepared-data.png'))
            page.get_by_role('button', name='Close', exact=True).click()
            checks.append('390px mobile review and data page fit the viewport with controlled table scrolling.')
            # Exercise the normal pending-protocol state without installing a default methodology.
            config_path.write_text('{}', encoding='utf-8')
            page.get_by_text('Forecast', exact=True).first.click()
            page.get_by_role('button', name='Generate Forecast', exact=True).click()
            expect(page.get_by_text('Hybrid forecast is currently unavailable for this dataset.', exact=True)).to_be_visible()
            assert page.locator('pre:visible').count() == 0
            page.screenshot(path=str(evidence / 'mobile-pending-forecast.png'), full_page=True)
            config_path.write_text(json.dumps(config, indent=2), encoding='utf-8')
            checks.append('Pending protocol shows the plain-language Hybrid-unavailable message without substituting a comparison model or exposing a configuration editor.')
            page.set_viewport_size({'width': 1440, 'height': 1000})
            page.get_by_text('Data', exact=True).first.click()
            dated = b'Disease,Year,Week,Cases,Week Start Date\nDengue,2025,1,2,2025-01-06\nDengue,2025,6,3,2025-02-10\nDengue,2025,15,4,2025-04-07'
            page.locator('#w-upload input[type=file]').set_input_files({'name': 'dated-weekly.csv', 'mimeType': 'text/csv', 'buffer': dated})
            expect(page.get_by_role('dialog')).to_be_visible()
            page.get_by_role('button', name='Confirm & Use Data', exact=True).click()
            expect(page.get_by_role('dialog')).not_to_be_visible()
            expect(page.locator('#w-content').get_by_text('dated-weekly.csv', exact=True)).to_be_visible()
            expect(page.locator('#w-content').get_by_text('Dengue', exact=True)).to_be_visible()
            page.get_by_text('Historical Trends', exact=True).first.click()
            page.locator('#w-aggregation input[value=Monthly]').check()
            expect(page.locator('#w-start-label')).to_have_text('From reporting month')
            expect(page.get_by_text('Monthly summary · Weekly records remain unchanged.', exact=True)).to_be_visible()
            page.locator('#w-aggregation input[value=Quarterly]').check()
            expect(page.locator('#w-start-label')).to_have_text('From reporting quarter')
            expect(page.get_by_text('Quarterly summary · Weekly records remain unchanged.', exact=True)).to_be_visible()
            page.screenshot(path=str(evidence / 'quarterly-history.png'), full_page=True)
            checks.append('Confirmed replacement refreshes Overview; dated weekly records enable monthly/quarterly charts and matching range labels.')
            page.get_by_text('Data', exact=True).first.click()
            page.get_by_role('button', name='Update Source Information', exact=True).click()
            expect(page.get_by_role('dialog')).to_be_visible()
            if not page.get_by_text('CESU/source evidence for historical completeness', exact=True).is_visible():
                page.get_by_text('2. Source information', exact=True).click()
            expect(page.get_by_text('CESU/source evidence for historical completeness', exact=True)).to_be_visible()
            page.get_by_role('button', name='Cancel', exact=True).click()
            expect(page.get_by_role('dialog')).not_to_be_visible()
            checks.append('Active source information can be staged without reupload; cancellation preserves the active dataset.')
            assert not errors, errors
            browser.close()
        report = {'checks': checks, 'page_errors': errors, 'browser': 'Microsoft Edge / Playwright',
                  'desktop': '1440x1000', 'mobile': '390x844', 'protocol': 'Synthetic-only test fixture; not a production default or adviser approval.'}
        (evidence / 'browser-results.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
        print(json.dumps(report, indent=2))
    finally:
        server.terminate()
        server.wait(timeout=20)
        log.close()


if __name__ == '__main__':
    run_browser()
