"""Browser workflow checks with a clearly simulated search, not accuracy evidence."""
import copy
import json
from pathlib import Path
import sys
import threading

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / '.browser-tools'))
import pytest
from playwright.sync_api import sync_playwright, expect
from werkzeug.serving import make_server

import app
from dashboard.weekly import jobs, workflow
from tests.test_provisional_validation import provisional_fixture


def main():
    output = ROOT / 'evidence' / 'provisional-browser'
    output.mkdir(parents=True, exist_ok=True)
    patch = pytest.MonkeyPatch()
    active, result, _ = provisional_fixture(patch, output / 'fixture')
    jobs.ROOT = output / 'jobs'
    release = threading.Event()
    def simulated(dataset, disease, output=None, progress=None):
        progress('sarima_search', 'Fitting SARIMA candidate 1/144 (browser test fixture).')
        if not release.wait(30):
            raise ValueError('Browser fixture timed out')
        progress('nnar_search', 'Evaluating NNAR configuration 96/96 (browser test fixture).')
        return copy.deepcopy(result)
    patch.setattr(workflow, 'run_provisional', simulated)
    server = make_server('127.0.0.1', 8069, app.server, threaded=True)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    errors = []
    downloads = []
    callbacks = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(channel='msedge', headless=True)
            page = browser.new_page(viewport={'width': 1400, 'height': 1000})
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.on('download', lambda download: downloads.append(download.suggested_filename))
            page.on('request', lambda request: callbacks.append(request.url) if '/_dash-update-component' in request.url else None)
            def assert_idle():
                page.wait_for_timeout(1000)  # Let completion-dependent callbacks settle.
                count = len(callbacks)
                page.wait_for_timeout(2200)
                assert len(callbacks) == count, 'An idle page must not keep polling or updating.'
            page.goto('http://127.0.0.1:8069/')
            page.wait_for_function('typeof window.dash_clientside?.set_props === "function"')
            page.evaluate("data => window.dash_clientside.set_props('w-active', {data})", active)
            page.get_by_role('tab', name='Forecast', exact=True).click()
            expect(page.locator('#w-provisional-export')).to_be_disabled()
            assert page.get_by_role('button', name='Generate Forecast', exact=True).count() == 1
            assert page.locator('#w-provisional-run, #w-evaluate').count() == 0
            assert_idle()
            page.evaluate("""() => {
                window.observedTitles = [];
                new MutationObserver(() => window.observedTitles.push(document.title))
                  .observe(document.querySelector('title'), {childList: true, subtree: true, characterData: true});
            }""")
            page.locator('#w-run').click()
            expect(page.locator('#w-fitting')).to_contain_text('candidate 1/144', timeout=15000)
            expect(page.locator('#w-run')).to_be_disabled()
            expect(page.locator('#w-sample-run')).to_be_disabled()
            page.wait_for_timeout(1500)
            assert all('Updating' not in title for title in page.evaluate('window.observedTitles'))
            release.set()
            expect(page.locator('#w-fitting')).to_contain_text('Forecast complete', timeout=15000)
            expect(page.locator('.model-performance-panel')).to_be_visible()
            expect(page.locator('#w-content')).to_contain_text('Not Thesis-Validated')
            expect(page.locator('#w-provisional-export')).to_be_enabled()
            assert_idle()
            page.get_by_text('Diagnostics', exact=True).click()
            page.get_by_text('Forecast Components', exact=True).click()
            page.wait_for_timeout(2500)
            assert page.get_by_text('Forecast Components', exact=True).evaluate('el => el.parentElement.open')
            assert page.locator('.model-performance-panel .js-plotly-plot').count() == 4
            assert downloads == [], 'Rendering results or expanding diagnostics must not download a report.'
            with page.expect_download() as download:
                page.locator('#w-provisional-export').click()
            download.value.save_as(output / 'download.json')
            report = json.loads((output / 'download.json').read_text(encoding='utf-8'))
            assert report['research_validated'] is False
            assert len(report['hybrid']) == 52
            before = page.evaluate("JSON.parse(sessionStorage.getItem('w-job')).run_id")
            page.get_by_text('Next 52 weeks', exact=True).click()
            page.wait_for_timeout(1500)
            assert page.evaluate("JSON.parse(sessionStorage.getItem('w-job')).run_id") == before
            page.get_by_role('tab', name='Overview', exact=True).click()
            page.get_by_role('tab', name='Forecast', exact=True).click()
            expect(page.locator('.model-performance-panel')).to_be_visible()
            page.wait_for_timeout(1500)
            assert downloads == ['methodology-report.json'], 'Horizon changes and navigation must not export files.'
            page.reload()
            page.get_by_role('tab', name='Forecast', exact=True).click()
            expect(page.locator('#w-fitting')).to_contain_text('Forecast complete', timeout=15000)
            assert_idle()
            def fail(*args, **kwargs):
                raise ValueError('Provisional Final Test blocked: test fixture missing starting residual.')
            patch.setattr(workflow, 'run_provisional', fail)
            page.locator('#w-run').click()
            expect(page.locator('#w-fitting')).to_contain_text('previous successful run', timeout=15000)
            expect(page.locator('.model-performance-panel')).to_be_visible()
            assert_idle()
            from dashboard.weekly.data import demo
            page.evaluate("data => window.dash_clientside.set_props('w-active', {data})", demo())
            expect(page.locator('#w-run')).to_be_disabled()
            page.get_by_text('Advanced Options', exact=True).click()
            expect(page.locator('#w-sample-run')).to_be_visible()
            expect(page.locator('#w-sample-run')).to_be_enabled()
            page.screenshot(path=str(output / 'completed.png'), full_page=True)
            assert not errors, errors
            (output / 'checks.json').write_text(json.dumps({'browser_errors': errors,
                'simulated_search': True, 'action_and_progress': 'passed', 'four_charts': 'passed',
                'components_stay_expanded': 'passed', 'provisional_report_download': 'passed',
                'no_unsolicited_downloads': 'passed', 'idle_polling_stops': 'passed',
                'terminal_reload': 'passed', 'stable_tab_title': 'passed'}, indent=2))
            browser.close()
    finally:
        release.set()
        server.shutdown()
        patch.undo()


if __name__ == '__main__':
    main()
