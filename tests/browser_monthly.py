"""Real-browser acceptance with synthetic data and an isolated temporary store."""
from pathlib import Path
import sys
import os
import tempfile
import threading

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'evidence' / 'ui-refinement-20261030'
EVIDENCE.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT))

from dash import Dash
from playwright.sync_api import expect, sync_playwright
from werkzeug.serving import make_server

from dashboard.monthly.security import create_user
from dashboard.monthly.store import Store
from dashboard.monthly.ui import install
from tests.test_monthly_system import frame


def main():
    with tempfile.TemporaryDirectory(prefix='monthly-browser-') as directory:
        os.environ['MPLCONFIGDIR'] = str(Path(directory) / 'matplotlib')
        store = Store(Path(directory) / 'state.sqlite3', is_prototype=True)
        admin_id = create_user(store, 'researcher', 'a-long-test-password', bootstrap=True)
        create_user(store, 'viewer', 'viewer-test-password', actor=dict(id=admin_id, role='admin', active=1))
        app = Dash('monthly_browser', assets_folder=str(ROOT / 'dashboard' / 'assets'))
        install(app, store)
        server = make_server('127.0.0.1', 8073, app.server, threaded=True)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        errors = []
        try:
            with sync_playwright() as browser_tools:
                browser = browser_tools.chromium.launch(channel='msedge', headless=True)
                page = browser.new_page(viewport={'width': 1440, 'height': 1050})
                page.on('pageerror', lambda error: errors.append(str(error)))
                def navigate(name):
                    if name == 'Notifications':
                        page.locator('#m-notifications-link').click()
                    elif page.viewport_size['width'] <= 1000:
                        page.locator('.m-mobile-nav summary').click()
                        page.locator('.m-mobile-nav').get_by_role('link', name=name, exact=True).click()
                    else:
                        page.locator('.m-desktop-nav').get_by_text(name, exact=True).click()
                page.goto('http://127.0.0.1:8073/')
                expect(page.locator('.m-app-header')).to_be_visible()
                page.screenshot(path=str(EVIDENCE / 'monthly-login.png'), full_page=True)
                page.locator('input[name=username]').fill('researcher')
                page.locator('input[name=password]').fill('a-long-test-password')
                page.get_by_role('button', name='Show password').click()
                expect(page.locator('input[name=password]')).to_have_attribute('type', 'text')
                page.get_by_role('button', name='Hide password').click()
                page.get_by_role('button', name='Sign in', exact=True).click()
                expect(page.locator('#m-content')).to_contain_text('No monthly dataset is active')
                page.screenshot(path=str(EVIDENCE / 'monthly-empty-dashboard.png'), full_page=True)
                page.locator('.m-account summary').click()
                page.get_by_role('link', name='Security / Accounts').click()
                expect(page.locator('.m-auth')).to_contain_text('Manage accounts')
                page.screenshot(path=str(EVIDENCE / 'monthly-accounts.png'), full_page=True)
                page.get_by_role('link', name='Return to dashboard').click()
                navigate('Data & Quality')
                expect(page.locator('#m-activate-button')).to_be_disabled()
                expect(page.locator('#m-cancel')).to_be_disabled()
                expect(page.locator('#m-reject-button')).to_be_disabled()
                page.locator('#m-upload input[type=file]').set_input_files({'name': 'synthetic-browser.csv', 'mimeType': 'text/csv', 'buffer': frame().to_csv(index=False).encode()})
                expect(page.locator('#m-message')).to_contain_text('Upload validated', timeout=15000)
                expect(page.locator('#m-preview')).to_contain_text('Upload validation and coverage', timeout=30000)
                assert store.active() is None
                page.once('dialog', lambda dialog: dialog.dismiss())
                page.get_by_role('button', name='Confirm & Activate', exact=True).click()
                assert store.active() is None
                page.once('dialog', lambda dialog: dialog.accept())
                page.get_by_role('button', name='Confirm & Activate', exact=True).click()
                expect(page.locator('#m-message')).to_contain_text('Monthly dataset activated')
                navigate('Dashboard')
                expect(page.locator('#m-content')).to_contain_text('Latest observation')
                page.screenshot(path=str(EVIDENCE / 'monthly-dashboard.png'), full_page=True)
                navigate('Disease Trends')
                expect(page.locator('#m-content')).to_contain_text('Annual Top-5 history')
                expect(page.locator('#m-content .js-plotly-plot')).to_be_visible()
                page.screenshot(path=str(EVIDENCE / 'monthly-desktop.png'), full_page=True)
                navigate('Reports')
                with page.expect_download() as downloaded:
                    page.get_by_role('button', name='Download HTML report').click()
                assert downloaded.value.suggested_filename.endswith('.html')
                for module in ('Model Performance', 'Notifications', 'Help & About'):
                    navigate(module)
                    expect(page.locator('#m-heading')).to_contain_text(module)
                    expect(page.locator('#m-content .m-panel').first).to_be_visible()
                navigate('Forecasting')
                expect(page.locator('#m-content')).to_contain_text('No forecast has been generated')
                expect(page.locator('#m-run')).to_be_enabled()
                page.locator('#m-run').click()
                expect(page.locator('#m-message')).to_contain_text('PROTOTYPE: 2 valid blocks ranked', timeout=120000)
                expect(page.locator('#m-message')).to_contain_text('Projected Top Five unavailable')
                expect(page.locator('#m-content')).to_contain_text('Provisional estimates for research use. Not for clinical decisions.')
                page.locator('#m-horizon').get_by_text('3 months', exact=True).click()
                expect(page.locator('#m-content')).to_contain_text('showing 3 months')
                expect(page.locator('#m-content')).to_contain_text('Prediction intervals are not available')
                with store.connect() as db:
                    assert db.execute('SELECT count(*) FROM forecast_values').fetchone()[0] == 24
                page.screenshot(path=str(EVIDENCE / 'monthly-prototype-forecast.png'), full_page=True)
                navigate('Dashboard')
                expect(page.locator('#m-content')).to_contain_text('Overall ranking')
                expect(page.locator('#m-content')).to_contain_text('Next 12 months')
                page.get_by_text('All projected totals', exact=True).click()
                sort_button = page.get_by_role('button', name='Sort by Consultations · next 12 months')
                sort_button.click()
                values = page.locator('th[aria-sort=ascending]').locator('xpath=ancestor::table').locator('tbody tr td:last-child').all_text_contents()
                assert [float(v.replace(',', '')) for v in values] == sorted(float(v.replace(',', '')) for v in values)
                navigate('Model Performance')
                expect(page.locator('#m-content')).to_contain_text('Prophet baseline')
                expect(page.locator('#m-content')).to_contain_text('MAE improvement from correction')
                page.screenshot(path=str(EVIDENCE / 'monthly-prototype-performance.png'), full_page=True)
                navigate('Forecasting')
                expect(page.locator('#m-content')).to_contain_text('Saved forecast')
                page.set_viewport_size({'width': 390, 'height': 844})
                expect(page.locator('.m-mobile-nav')).to_be_visible()
                expect(page.locator('#m-forecast-controls')).to_be_visible()
                page.wait_for_function('document.documentElement.scrollWidth <= innerWidth + 1')
                page.screenshot(path=str(EVIDENCE / 'monthly-mobile.png'), full_page=True)
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'), page.evaluate("Array.from(document.querySelectorAll('body *')).filter(e=>e.getBoundingClientRect().right>innerWidth+1).slice(0,12).map(e=>({tag:e.tagName,id:e.id,cls:e.className,width:e.getBoundingClientRect().width}))")
                navigate('Dashboard')
                expect(page.locator('#m-content')).to_contain_text('Monthly consultation trend')
                page.locator('.m-account summary').click()
                page.get_by_role('link', name='Sign out', exact=True).click()
                page.get_by_role('button', name='Confirm sign out').click()
                page.locator('input[name=username]').fill('viewer')
                page.locator('input[name=password]').fill('viewer-test-password')
                page.get_by_role('button', name='Sign in', exact=True).click()
                navigate('Data & Quality')
                expect(page.locator('#m-data-controls')).to_be_hidden()
                expect(page.locator('#m-content')).to_contain_text('Data provenance')
                assert not errors, errors
                browser.close()
                print('PASS: login, activation, real prototype forecast callback, 24 persisted values, unavailable Top Five, baseline comparison, HTML report, mobile view and viewer permissions; no browser errors.')
        finally:
            server.shutdown()


if __name__ == '__main__':
    main()
