"""Manual synthetic browser acceptance: python tests/browser_postpr11.py."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.request
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.browser-tools'))
sys.path.insert(0, str(ROOT))
from playwright.sync_api import sync_playwright, expect  # noqa: E402
from tests.test_weekly import protocol  # noqa: E402


def main():
    evidence = ROOT / 'evidence' / 'post-pr11-browser'
    evidence.mkdir(parents=True, exist_ok=True)
    config = {**protocol(), 'version': 'synthetic-browser-tvt', 'nnar_maxiter': 5000}
    config_path = evidence / 'synthetic-protocol.json'
    config_path.write_text(json.dumps(config), encoding='utf-8')
    environment = {**os.environ, 'WEEKLY_MODEL_CONFIG': str(config_path),
                   'WEEKLY_MODEL_STORE': str(evidence / (uuid.uuid4().hex + '.sqlite3'))}
    errors, checks = [], []
    with (evidence / 'server.log').open('w', encoding='utf-8') as log:
        server = subprocess.Popen(
            [sys.executable, '-c', "import app; app.dash_app.run(host='127.0.0.1',port=8067,debug=False)"],
            cwd=ROOT, env=environment, stdout=log, stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        try:
            for _ in range(100):
                try:
                    urllib.request.urlopen('http://127.0.0.1:8067/healthz', timeout=1).close()
                    break
                except OSError:
                    time.sleep(.1)
            with sync_playwright() as p:
                browser = p.chromium.launch(channel='msedge', headless=True)
                page = browser.new_page(viewport={'width': 1440, 'height': 1000})
                page.set_default_timeout(30000)
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.goto('http://127.0.0.1:8067/')
                page.get_by_text('Data', exact=True).first.click()
                text = 'Disease,Reporting Year,Week,Total Cases,Dataset Type,Reporting Status,Age Group\n'
                text += '\n'.join(f'Measles,{2022 + i // 52},{i % 52 + 1},{i % 7},synthetic,complete,all-age'
                                  for i in range(156))
                page.locator('#w-upload input[type=file]').set_input_files(
                    {'name': 'synthetic-tvt.csv', 'mimeType': 'text/csv', 'buffer': text.encode()})
                expect(page.get_by_role('dialog')).to_be_visible()
                page.get_by_role('button', name='Confirm & Use Data', exact=True).click()
                expect(page.get_by_role('dialog')).not_to_be_visible()
                page.get_by_text('Forecast', exact=True).first.click()
                page.get_by_role('button', name='Generate Forecast', exact=True).click()
                expect(page.get_by_text('No compatible locked configuration.', exact=False)).to_be_visible()
                checks.append('Normal generation does not run model selection.')
                page.get_by_role('button', name='Compute Model Performance', exact=True).click()
                expect(page.get_by_text('Configuration locked. Choose Generate Forecast', exact=False)).to_be_visible(timeout=60000)
                checks.append('Performance action bootstraps and persists Training/Validation/Test selection.')
                page.get_by_role('button', name='Generate Forecast', exact=True).click()
                expect(page.get_by_role('heading', name='Preparedness Interpretation')).to_be_visible(timeout=60000)
                expect(page.get_by_text('Forecast-based preparedness interpretation', exact=False)).to_be_visible()
                page.screenshot(path=str(evidence / 'forecast.png'), full_page=True)
                traces = page.locator('.js-plotly-plot').evaluate_all('(nodes) => nodes.flatMap(n => (n.data || []).map(t => t.name))')
                assert 'Forecast range' not in traces
                checks.append('Operational path and reproducible interpretation render without an uncertainty band.')
                page.get_by_text('About', exact=True).first.click()
                page.get_by_text('Advanced Details', exact=True).click()
                expect(page.get_by_text('Model status, configuration and diagnostics', exact=True)).to_be_visible()
                page.get_by_text('Model status, configuration and diagnostics', exact=True).click()
                expect(page.locator('#w-advanced')).to_contain_text('final_test')
                page.screenshot(path=str(evidence / 'advanced.png'), full_page=True)
                with page.expect_download() as downloading:
                    page.get_by_role('button', name='Download Detailed Evidence', exact=True).click()
                download = downloading.value
                destination = evidence / 'synthetic-evidence.json'
                download.save_as(destination)
                payload = json.loads(destination.read_text(encoding='utf-8'))
                assert len(payload['future_forecast_results']) == 104
                assert payload['historical_model_performance']['scored_test_observations'] == 52
                assert payload['model_metadata']['periods']['validation']['positions'] == 52
                assert payload['preparedness_summary']['status'] == 'Available'
                assert 'range' not in payload['forecast']
                checks.append('Advanced Details and downloaded evidence contain split boundaries and all four sections.')
                page.reload()
                page.get_by_text('Forecast', exact=True).first.click()
                expect(page.get_by_role('heading', name='Preparedness Interpretation')).to_be_visible()
                checks.append('Session forecast and computed performance survive page reload.')
                assert not errors, errors
                browser.close()
        finally:
            server.terminate()
            server.wait(timeout=10)
            (evidence / 'checks.json').write_text(json.dumps({'checks': checks, 'browser_errors': errors}, indent=2), encoding='utf-8')
    print(json.dumps({'checks': checks, 'browser_errors': errors}, indent=2))


if __name__ == '__main__':
    main()
