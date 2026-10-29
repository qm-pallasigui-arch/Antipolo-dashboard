"""Browser integration with explicitly simulated fits, never research evidence."""
import json
from pathlib import Path
import sys
import threading

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / '.browser-tools'))
from playwright.sync_api import sync_playwright, expect
from werkzeug.serving import make_server

import app
from dashboard.weekly import jobs, model, workflow
from tests.test_corrected_methodology import research_fixture


def main():
    output = ROOT / 'evidence' / 'forecast-progress-browser'
    output.mkdir(parents=True, exist_ok=True)
    jobs.ROOT = output / 'jobs'
    active, config = research_fixture()
    workflow.settings.model_configuration = lambda: config
    workflow.ROOT = output / 'research'
    release = threading.Event()
    fail = [False]
    def simulated_fit(values, steps, c, progress=None):
        progress('sarima', 'Fitting SARIMA (browser test fixture).')
        if not release.wait(30):
            raise ValueError('Browser test timed out')
        if fail[0]:
            raise ValueError('SARIMA optimizer did not converge.')
        progress('residuals', 'Post-initialization residuals prepared (test fixture).')
        progress('nnar', 'NNAR fitted (test fixture).')
        progress('residual_forecast', 'Recursive residual forecast generated (test fixture).')
        progress('combine', 'Forecast components combined (test fixture).')
        return {'hybrid': [1.]*steps, 'sarima': [2.]*steps, 'hybrid_status': 'Available',
                'sarima_status': 'Available', 'diagnostics': {}, 'range': None,
                'components': {'raw_sarima': [2.]*steps, 'nnar_correction': [-1.]*steps, 'hybrid': [1.]*steps}}
    real_fit = model.fit_models
    model.fit_models = simulated_fit
    server = make_server('127.0.0.1', 8068, app.server, threaded=True)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    errors = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(channel='msedge', headless=True)
            page = browser.new_page(viewport={'width': 1365, 'height': 1000})
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.goto('http://127.0.0.1:8068/')
            page.wait_for_function('typeof window.dash_clientside?.set_props === "function"')
            page.evaluate("data => window.dash_clientside.set_props('w-active', {data})", active)
            page.get_by_role('tab', name='Forecast', exact=True).click()
            page.locator('#w-run').click()
            expect(page.locator('#w-fitting')).to_contain_text('Fitting SARIMA', timeout=15000)
            expect(page.locator('#w-run')).to_be_disabled()
            assert page.locator('#w-evaluate').count() == 0
            page.screenshot(path=str(output / 'running.png'), full_page=True)
            release.set()
            expect(page.locator('#w-fitting')).to_contain_text('52 weekly projections generated', timeout=15000)
            expect(page.locator('#w-run')).to_be_enabled()
            page.locator('#w-fitting summary').click()
            expect(page.locator('#w-fitting')).to_contain_text('Forecast components combined')
            page.wait_for_timeout(3500)  # Must survive multiple one-second poll ticks.
            assert page.locator('#w-fitting details').evaluate('el => el.open')
            page.locator('#w-fitting summary').click()
            page.wait_for_timeout(1500)
            assert not page.locator('#w-fitting details').evaluate('el => el.open')
            first = page.evaluate("JSON.parse(sessionStorage.getItem('w-result'))")
            page.screenshot(path=str(output / 'complete.png'), full_page=True)
            expect(page.locator('.model-performance-panel')).to_be_visible()
            prior = page.evaluate("JSON.parse(sessionStorage.getItem('w-result'))")
            assert prior['Measles']['metrics']['hybrid']['n'] == 52
            fail[0] = True
            page.locator('#w-run').click()
            expect(page.locator('#w-fitting')).to_contain_text('SARIMA optimizer did not converge', timeout=15000)
            expect(page.locator('#w-run')).to_be_enabled()
            after = page.evaluate("JSON.parse(sessionStorage.getItem('w-result'))")
            assert prior == after and first['Measles']['hybrid'] == after['Measles']['hybrid']
            page.screenshot(path=str(output / 'failure.png'), full_page=True)
            # The sample button must run genuine estimators without a research lock.
            from dashboard.weekly.data import demo
            model.fit_models = real_fit
            page.evaluate("data => window.dash_clientside.set_props('w-active', {data})", demo())
            expect(page.locator('#w-disease')).to_contain_text('Demo disease')
            expect(page.locator('#w-run')).to_be_disabled()
            page.get_by_text('Advanced Options', exact=True).click()
            page.locator('#w-sample-run').click()
            expect(page.locator('#w-fitting')).to_contain_text('Quick Preview complete', timeout=60000)
            sample = page.evaluate("JSON.parse(sessionStorage.getItem('w-result'))")['Demo disease']
            assert len(sample['hybrid']) == 52 and sample['sample_forecast'] and not sample['eligible']
            assert sample['metrics'] == {}
            page.screenshot(path=str(output / 'sample.png'), full_page=True)
            assert not errors, errors
            (output / 'checks.json').write_text(json.dumps({'simulated_fits': True, 'success': True,
                'failure_preserves_previous': True, 'evaluation': True, 'buttons_restored': True,
                'completed_log_accessible': True, 'details_state_survives_polling': True, 'genuine_sample_forecast': True,
                'sample_horizon': 52, 'browser_errors': errors}, indent=2), encoding='utf-8')
            browser.close()
    finally:
        release.set()
        server.shutdown()


if __name__ == '__main__':
    main()

