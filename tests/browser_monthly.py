"""Real-browser acceptance with synthetic data and an isolated temporary store."""
from pathlib import Path
import sys
import tempfile
import threading

ROOT = Path(__file__).resolve().parents[1]
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
        store = Store(Path(directory) / 'state.sqlite3')
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
                    if page.viewport_size['width'] <= 800:
                        page.locator('.m-mobile-nav summary').click()
                        page.locator('.m-mobile-nav').get_by_role('link', name=name, exact=True).click()
                    else:
                        page.locator('.m-desktop-nav').get_by_text(name, exact=True).click()
                page.goto('http://127.0.0.1:8073/')
                expect(page.locator('.m-app-header')).to_be_visible()
                page.screenshot(path=str(ROOT / 'evidence' / 'monthly-login.png'), full_page=True)
                page.locator('input[name=username]').fill('researcher')
                page.locator('input[name=password]').fill('a-long-test-password')
                page.get_by_role('button', name='Sign in', exact=True).click()
                expect(page.locator('#m-content')).to_contain_text('No monthly dataset is active')
                page.screenshot(path=str(ROOT / 'evidence' / 'monthly-empty-dashboard.png'), full_page=True)
                page.locator('.m-account summary').click()
                page.get_by_role('link', name='Security / Accounts').click()
                expect(page.locator('.m-auth')).to_contain_text('Manage accounts')
                page.screenshot(path=str(ROOT / 'evidence' / 'monthly-accounts.png'), full_page=True)
                page.get_by_role('link', name='Return to dashboard').click()
                navigate('Data & Quality')
                page.locator('#m-upload input[type=file]').set_input_files({'name': 'synthetic-browser.csv', 'mimeType': 'text/csv', 'buffer': frame().to_csv(index=False).encode()})
                expect(page.locator('#m-preview')).to_contain_text('Candidate validation and coverage')
                assert store.active() is None
                page.once('dialog', lambda dialog: dialog.dismiss())
                page.get_by_role('button', name='Confirm & Activate', exact=True).click()
                assert store.active() is None
                page.once('dialog', lambda dialog: dialog.accept())
                page.get_by_role('button', name='Confirm & Activate', exact=True).click()
                expect(page.locator('#m-message')).to_contain_text('Monthly dataset activated')
                navigate('Dashboard')
                expect(page.locator('#m-content')).to_contain_text('Latest observation')
                page.screenshot(path=str(ROOT / 'evidence' / 'monthly-dashboard.png'), full_page=True)
                navigate('Disease Trends')
                expect(page.locator('#m-content')).to_contain_text('Annual Top-5 history')
                expect(page.locator('#m-content .js-plotly-plot')).to_be_visible()
                page.screenshot(path=str(ROOT / 'evidence' / 'monthly-desktop.png'), full_page=True)
                navigate('Reports')
                with page.expect_download() as downloaded:
                    page.get_by_role('button', name='Download HTML report').click()
                assert downloaded.value.suggested_filename.endswith('.html')
                for module in ('Model Performance', 'Notifications', 'Help & About'):
                    navigate(module)
                    expect(page.locator('#m-heading')).to_contain_text(module)
                    expect(page.locator('#m-content .m-panel').first).to_be_visible()
                navigate('Forecasting')
                expect(page.locator('#m-content')).to_contain_text('TO FINALIZE')
                expect(page.locator('#m-run')).to_be_disabled()
                page.set_viewport_size({'width': 390, 'height': 844})
                expect(page.locator('.m-mobile-nav')).to_be_visible()
                page.screenshot(path=str(ROOT / 'evidence' / 'monthly-mobile.png'), full_page=True)
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
                print('PASS: login, staging, preview, explicit activation, monthly chart, HTML report, pending model, mobile view, logout and viewer permissions; no browser errors.')
        finally:
            server.shutdown()


if __name__ == '__main__':
    main()
