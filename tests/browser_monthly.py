"""Real-browser acceptance with synthetic data and an isolated temporary store."""
from pathlib import Path
import sys
import os
import tempfile
import threading
import json

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / '.artifacts' / 'browser-monthly'
EVIDENCE.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT))

from dash import Dash
from playwright.sync_api import expect, sync_playwright
from werkzeug.serving import make_server

from dashboard.monthly.security import create_user
from dashboard.monthly.store import Store
from dashboard.monthly.ui import install
from dashboard.monthly.worker import run_once
from tests.test_monthly_system import frame


def main():
    with tempfile.TemporaryDirectory(prefix='monthly-browser-') as directory:
        os.environ['MPLCONFIGDIR'] = str(Path(directory) / 'matplotlib')
        store = Store(Path(directory) / 'state.sqlite3', is_prototype=True)
        admin_id = create_user(store, 'researcher', 'a-long-test-password', bootstrap=True)
        create_user(store, 'viewer', 'viewer-test-password', actor=dict(id=admin_id, role='admin', active=1))
        app = Dash('monthly_browser', assets_folder=str(ROOT / 'dashboard' / 'assets'))
        _, service = install(app, store)
        release_model = Path(directory) / 'release-model'
        worker_stop = threading.Event()
        def work():
            while not worker_stop.is_set():
                if not run_once(store, worker_stop, command=[sys.executable, '-m', 'tests.forecast_worker_fixture', str(release_model)]):
                    worker_stop.wait(0.1)
        worker_thread = threading.Thread(target=work, daemon=True)
        worker_thread.start()
        server = make_server('127.0.0.1', 8073, app.server, threaded=True)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        errors = []
        try:
            with sync_playwright() as browser_tools:
                browser = browser_tools.chromium.launch(channel='msedge', headless=True)
                context = browser.new_context(viewport={'width': 1440, 'height': 1050})
                page = context.new_page()
                measurements = []
                def measure_text(locator, label):
                    value = locator.evaluate('''e => {
                        const rgb = v => (v.match(/[\\d.]+/g) || []).map(Number);
                        const style = getComputedStyle(e), color = rgb(style.color);
                        let bg = [255,255,255];
                        const ancestors = []; for(let p=e;p;p=p.parentElement) ancestors.unshift(p);
                        for(const p of ancestors) {
                            const c=rgb(getComputedStyle(p).backgroundColor), a=c.length===4?c[3]:1;
                            bg=bg.map((v,i)=>c[i]*a+v*(1-a));
                        }
                        const lum = c => c.slice(0,3).map(v=>{v/=255;return v<=.04045?v/12.92:((v+.055)/1.055)**2.4;})
                            .reduce((s,v,i)=>s+v*[.2126,.7152,.0722][i],0);
                        const a=lum(color), b=lum(bg);
                        return {color:style.color,background:bg,fontSize:parseFloat(style.fontSize),contrast:(Math.max(a,b)+.05)/(Math.min(a,b)+.05)};
                    }''')
                    measurements.append({'label': label, **value})
                    (EVIDENCE / 'phase2-measurements.json').write_text(json.dumps(measurements, indent=2))
                    assert value['contrast'] >= 4.5, (label, value)
                    assert value['fontSize'] >= 14, (label, value)
                page.on('pageerror', lambda error: errors.append(str(error)))
                def capture_final_layout(name):
                    output = ROOT / '.artifacts' / 'layout-final' / os.environ.get('LAYOUT_CAPTURE_STAGE', 'after')
                    output.mkdir(parents=True, exist_ok=True)
                    for width in (1920, 1440, 1024, 768, 375):
                        page.set_viewport_size({'width': width, 'height': 1050})
                        page.wait_for_function('document.documentElement.scrollWidth <= innerWidth + 1')
                        if os.environ.get('LAYOUT_CAPTURE_STAGE') != 'before':
                            if name == 'Notifications':
                                filters = page.locator('#m-notification-controls').bounding_box()
                                activity = page.locator('#m-content').bounding_box()
                                if width >= 1200:
                                    assert activity['x'] > filters['x'] + filters['width']
                                    assert activity['width'] > filters['width'] * 2
                                else:
                                    assert activity['y'] >= filters['y'] + filters['height']
                            if name == 'Help-&-About' and width >= 1200:
                                assert page.locator('.m-help-grid .m-span-8').bounding_box()['width'] > page.locator('.m-help-grid .m-span-4').bounding_box()['width']
                            if name == 'Reports':
                                cards = page.locator('.m-report-grid>.m-panel')
                                assert cards.count() == 3
                                boxes = [cards.nth(i).bounding_box() for i in range(3)]
                                if width > 800:
                                    assert max(b['y'] for b in boxes) - min(b['y'] for b in boxes) < 2
                                else:
                                    assert boxes[1]['y'] >= boxes[0]['y'] + boxes[0]['height']
                            if name == 'Security':
                                create = page.locator('#m-create-account').bounding_box()
                                manage = page.locator('#m-manage-accounts').bounding_box()
                                assert (manage['x'] > create['x'] if width >= 1200 else manage['y'] >= create['y'] + create['height'])
                        page.screenshot(path=str(output / f'{name}-{width}.png'), full_page=True)
                    page.set_viewport_size({'width': 1440, 'height': 1050})
                def capture_phase2(name, phase='layout-phase2', has_plot=True):
                    output = ROOT / '.artifacts' / phase / 'after'
                    output.mkdir(parents=True, exist_ok=True)
                    sizes = []
                    for width in (1920, 1440, 1024, 768, 375):
                        page.set_viewport_size({'width': width, 'height': 1050})
                        page.wait_for_function('document.documentElement.scrollWidth <= innerWidth + 1')
                        if has_plot:
                            page.wait_for_function('document.querySelector("#m-content .js-plotly-plot")?._fullLayout?._size?.h > 150')
                            plot = page.locator('#m-content .js-plotly-plot')
                            # Wait for Plotly's responsive width, not just the CSS container.
                            page.wait_for_function('Math.abs(document.querySelector("#m-content .js-plotly-plot")._fullLayout.width - document.querySelector("#m-content .js-plotly-plot").clientWidth) < 3')
                            if phase == 'layout-phase3':
                                assert plot.evaluate('e => e._fullLayout._size.w') >= 150
                        sizes.append({'width': width, 'plot': plot.evaluate('e => e._fullLayout._size') if has_plot else None})
                        page.evaluate('document.activeElement.blur();window.scrollTo(0,0)')
                        page.screenshot(path=str(output / f'{name}-{width}.png'), full_page=True)
                        if width < 1200:
                            page.locator('#m-menu-toggle').click()
                            page.screenshot(path=str(output / f'{name}-{width}-open.png'), full_page=True)
                            page.keyboard.press('Escape')
                            expect(page.locator('#m-menu-toggle')).to_be_focused()
                    (output / f'{name}-measurements.json').write_text(json.dumps(sizes, indent=2))
                    page.set_viewport_size({'width': 1440, 'height': 1050})

                def navigate(name):
                    if name == 'Notifications':
                        page.locator('#m-notifications-link').click()
                    else:
                        if page.viewport_size['width'] < 1200:
                            page.locator('#m-menu-toggle').click()
                        page.locator('#m-sidebar').get_by_role('link', name=name, exact=True).click()
                    content_name = 'Model Performance & Insights' if name == 'Model Performance' else name
                    expect(page.locator('#m-content > [data-page]')).to_have_attribute('data-page', content_name, timeout=15000)
                    expect(page.locator('#m-heading h1')).to_be_focused()
                    expect(page.locator('main')).to_have_count(1)
                    expect(page.locator('nav[aria-label="Main navigation"]')).to_have_count(1)
                    expect(page.locator('.m-skip-link')).to_have_attribute('href', '#m-main')
                    active = page.locator('#m-notifications-link') if name == 'Notifications' else page.locator('#m-sidebar').get_by_role('link', name=name, exact=True, include_hidden=True)
                    expect(active).to_have_attribute('aria-current', 'page')
                    expect(page.locator('[aria-current=page]')).to_have_count(1)
                    if name != 'Notifications':
                        assert active.evaluate('e => getComputedStyle(e).textDecorationLine') == 'none'
                    if page.viewport_size['width'] >= 1200:
                        idle = page.locator('.m-sidebar-link:not([aria-current])').first
                        idle.hover()
                        assert idle.evaluate('e => getComputedStyle(e).backgroundColor') == 'rgb(36, 70, 94)'
                        page.mouse.move(1439, 0)
                    expect(page.locator('#m-content .m-panel--featured')).to_have_count(1 if name == 'Dashboard' else 0)
                    if name in ('Help & About', 'Notifications', 'Data & Quality'):
                        expect(page.locator('#m-context')).to_be_hidden()

                page.goto('http://127.0.0.1:8073/')
                expect(page.locator('.m-app-header')).to_be_visible()
                expect(page.get_by_role('heading', level=1)).to_have_text('Sign in')
                assert page.locator('.m-auth').bounding_box()['width'] == 420
                assert page.get_by_role('button', name='Sign in', exact=True).bounding_box()['height'] >= 48
                assert page.locator('#login-username').evaluate('e => getComputedStyle(e).borderColor') == 'rgb(67, 90, 111)'
                page.screenshot(path=str(EVIDENCE / 'monthly-login.png'), full_page=True)
                page.set_viewport_size({'width': 375, 'height': 844})
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                page.screenshot(path=str(EVIDENCE / 'monthly-login-mobile.png'), full_page=True)
                page.set_viewport_size({'width': 1440, 'height': 1050})
                page.get_by_role('link', name='Forgot password?').click()
                page.locator('input[name=username]').fill('viewer')
                page.get_by_role('button', name='Notify administrator').click()
                expect(page.get_by_role('status')).to_contain_text('If this account exists')
                page.get_by_role('link', name='Return to sign in').click()
                page.locator('input[name=username]').fill('researcher')
                page.locator('input[name=username]').focus()
                page.keyboard.press('Tab')
                expect(page.locator('#login-password')).to_be_focused()
                page.locator('#login-password').dispatch_event('keyup', {'key': 'CapsLock', 'modifierCapsLock': True})
                expect(page.locator('#caps-lock')).to_be_visible()
                assert page.locator('.m-password-field').evaluate('e => getComputedStyle(e).outlineStyle') == 'solid'
                assert page.locator('#login-password').evaluate('e => getComputedStyle(e).outlineStyle') == 'none'
                assert page.locator('.m-password-field').evaluate('e => getComputedStyle(e).outlineColor') == 'rgb(19, 117, 111)'
                page.screenshot(path=str(EVIDENCE / 'headers-login-focused.png'), full_page=True)
                page.keyboard.press('Tab')
                expect(page.get_by_role('button', name='Show password')).to_be_focused()
                assert page.get_by_role('button', name='Show password').evaluate('e => getComputedStyle(e).outlineStyle') != 'none'
                page.keyboard.press('Tab')
                expect(page.get_by_role('button', name='Sign in', exact=True)).to_be_focused()
                page.locator('input[name=password]').fill('wrong-password')
                page.get_by_role('button', name='Sign in', exact=True).click()
                expect(page.get_by_role('alert')).to_contain_text('Login failed.')
                expect(page.locator('input[name=username]')).to_have_value('researcher')
                expect(page.locator('input[name=password]')).to_have_value('')
                page.screenshot(path=str(EVIDENCE / 'monthly-login-error.png'), full_page=True)
                page.locator('input[name=password]').fill('a-long-test-password')
                page.get_by_role('button', name='Show password').focus()
                page.keyboard.press('Enter')
                expect(page.locator('input[name=password]')).to_have_attribute('type', 'text')
                page.keyboard.press('Enter')
                expect(page.locator('input[name=password]')).to_have_attribute('type', 'password')
                # Hold navigation after the real submit handler to inspect its pending state.
                page.evaluate("document.addEventListener('submit', e => e.preventDefault(), {once:true})")
                page.get_by_role('button', name='Sign in', exact=True).click()
                expect(page.get_by_role('button', name='Signing in…')).to_be_disabled()
                expect(page.locator('[data-busy-form]')).to_have_attribute('aria-busy', 'true')
                page.screenshot(path=str(EVIDENCE / 'monthly-login-submitting.png'), full_page=True)
                assert page.locator('[data-busy-form]').evaluate("e => !e.dispatchEvent(new Event('submit', {bubbles:true,cancelable:true}))")
                page.evaluate("window.dispatchEvent(new Event('pageshow'))")
                page.get_by_role('button', name='Sign in', exact=True).click()
                expect(page.locator('#m-content')).to_contain_text('No monthly dataset is active')
                page.locator('#m-notifications-link').focus()
                assert page.locator('#m-notifications-link').evaluate("e => getComputedStyle(e).outlineStyle") != 'none'
                page.keyboard.press('Enter')
                expect(page.locator('#m-heading')).to_contain_text('Notifications')
                navigate('Dashboard')
                page.screenshot(path=str(EVIDENCE / 'monthly-empty-dashboard.png'), full_page=True)
                page.locator('.m-account summary').click()
                page.get_by_role('link', name='Security / Accounts').click()
                page.wait_for_load_state('load')
                expect(page.locator('.m-auth')).to_contain_text('Manage accounts')
                capture_final_layout('Security')
                own_account = page.locator('.m-user-row').first
                expect(own_account.locator('select[name=role]')).to_be_disabled()
                expect(own_account.locator('select[name=active]')).to_be_disabled()
                account_form = page.locator('.m-user-row').nth(1)
                expect(account_form.get_by_role('button', name='Save account')).to_be_disabled()
                account_form.locator('select[name=role]').select_option('admin')
                expect(account_form.get_by_role('button', name='Save account')).to_be_enabled()
                account_form.locator('select[name=role]').select_option('viewer')
                expect(account_form.get_by_role('button', name='Save account')).to_be_disabled()
                expect(page.locator('.m-account-menu a[aria-current=page]')).to_have_text('Security / Accounts')
                create_toggle = page.locator('[data-password-toggle=create-password]')
                page.locator('#create-password').focus()
                assert page.locator('#create-password').locator('..').evaluate('e => getComputedStyle(e).outlineStyle') == 'solid'
                create_toggle.focus()
                page.keyboard.press('Enter')
                expect(page.locator('#create-password')).to_have_attribute('type', 'text')
                expect(create_toggle).to_have_attribute('aria-pressed', 'true')
                page.keyboard.press('Enter')
                expect(page.locator('#create-password')).to_have_attribute('type', 'password')
                measure_text(page.locator('#password-help'), 'Security password help')
                page.set_viewport_size({'width': 375, 'height': 844})
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
                page.screenshot(path=str(EVIDENCE / 'phase2-security-mobile.png'), full_page=True)
                page.set_viewport_size({'width': 1440, 'height': 1050})
                page.get_by_text('Reset password for viewer', exact=True).click()
                reset_form = page.locator('details').filter(has=page.get_by_text('Reset password for viewer', exact=True)).locator('form')
                reset_form.locator('[name=identity_verified]').select_option('yes')
                reset_form.locator('[name=password]').fill('viewer-test-password')
                page.once('dialog', lambda dialog: dialog.dismiss())
                reset_form.get_by_role('button', name='Reset password', exact=True).click()
                expect(reset_form).to_be_visible()
                page.once('dialog', lambda dialog: dialog.accept())
                reset_form.get_by_role('button', name='Reset password', exact=True).click()
                expect(page.get_by_role('status')).to_contain_text('Password reset completed')
                page.screenshot(path=str(EVIDENCE / 'monthly-accounts.png'), full_page=True)
                page.get_by_role('link', name='Return to dashboard').click()
                navigate('Data & Quality')
                measure_text(page.locator('.m-upload-zone'), 'Upload hint')
                invalid = frame().iloc[:1].copy()
                invalid.loc[:, 'icd10_block'] = 'invalid-' + 'x' * 300
                page.locator('#m-upload input[type=file]').set_input_files({
                    'name': 'invalid-accessibility.csv', 'mimeType': 'text/csv',
                    'buffer': invalid.to_csv(index=False).encode()})
                expect(page.locator('#m-message [role=alert]')).to_contain_text('Invalid infectious-disease ICD-10 block')
                page.set_viewport_size({'width': 375, 'height': 844})
                page.wait_for_function('document.documentElement.scrollWidth <= innerWidth + 1')
                page.screenshot(path=str(EVIDENCE / 'accessibility-long-error.png'), full_page=True)
                page.set_viewport_size({'width': 1440, 'height': 1050})
                assert page.locator('#m-candidate').evaluate('e => getComputedStyle(e).borderColor') == 'rgb(67, 90, 111)'
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
                expect(page.get_by_text('Dataset active', exact=True)).to_have_count(1)
                expect(page.get_by_text('Selected disease group', exact=True)).to_have_count(1)
                measure_text(page.locator('#m-source-context'), 'Dataset source context')
                measure_text(page.locator('.m-metric small').first, 'Metric helper')
                measure_text(page.locator('.m-app-footer'), 'Footer')
                page.screenshot(path=str(EVIDENCE / 'monthly-dashboard.png'), full_page=True)
                navigate('Disease Trends')
                expect(page.locator('#m-content')).to_contain_text('Annual Top-5 history')
                expect(page.locator('#m-content .js-plotly-plot')).to_be_visible()
                capture_phase2('Disease-Trends')
                expect(page.get_by_role('heading', name='Monthly records', exact=True)).to_be_visible()
                history_box = page.locator('#m-annual-history').bounding_box()
                records_box = page.locator('#m-monthly-records').bounding_box()
                assert abs(history_box['y'] - records_box['y']) < 2
                assert records_box['x'] > history_box['x'] and records_box['width'] > history_box['width']
                count_cell = page.locator('td[data-dash-column=consultation_count]').first
                expect(count_cell).to_have_text('0')
                assert count_cell.evaluate('e => getComputedStyle(e).textAlign') == 'right'
                count_header = page.locator('th[data-dash-column=consultation_count]').first
                assert count_header.evaluate('e => getComputedStyle(e).textAlign') == 'right'
                expect(page.locator('td[data-dash-column=month]').first).to_have_text('January')
                assert page.locator('td[data-dash-column=month]').first.evaluate('e => getComputedStyle(e).textAlign') == 'left'
                paged_sort = count_header.get_by_role('button', name='Sort by Consultations', exact=True)
                page.keyboard.press('Tab')
                paged_sort.focus()
                assert paged_sort.evaluate('e => getComputedStyle(e).outlineStyle') != 'none', paged_sort.evaluate('e => ({focusVisible:e.matches(":focus-visible"),style:getComputedStyle(e).outline})')
                page.keyboard.press('Enter')
                expect(count_header).to_have_attribute('aria-sort', 'ascending')
                page.keyboard.press('Space')
                expect(count_header).to_have_attribute('aria-sort', 'descending')
                expect(count_cell).to_have_text('4')
                assert paged_sort.bounding_box()['x'] > count_header.locator('.column-header-name').bounding_box()['x']
                for control in page.locator('.previous-next-container button').all():
                    size = control.bounding_box()
                    assert size['height'] >= 44 and size['width'] >= 44, size
                    measurements.append({'label': 'Pagination target', **size})
                page.screenshot(path=str(EVIDENCE / 'monthly-desktop.png'), full_page=True)
                navigate('Reports')
                with page.expect_download() as downloaded:
                    page.get_by_role('button', name='Download HTML report').click()
                assert downloaded.value.suggested_filename.endswith('.html')
                for module in ('Model Performance', 'Notifications', 'Help & About'):
                    navigate(module)
                    expect(page.locator('#m-heading')).to_contain_text(module)
                    expect(page.locator('#m-content .m-panel').first).to_be_visible()
                    if module in ('Notifications', 'Help & About'):
                        expect(page.locator('#m-context')).to_be_hidden()
                navigate('Forecasting')
                expect(page.get_by_role('heading', name='Chart window', exact=True)).to_have_count(0)
                expect(page.locator('#m-horizon input').first).to_be_disabled()
                page.screenshot(path=str(EVIDENCE / 'headers-forecast-none.png'), full_page=True)
                page.set_viewport_size({'width': 375, 'height': 844})
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
                page.screenshot(path=str(EVIDENCE / 'headers-forecast-none-mobile.png'), full_page=True)
                page.set_viewport_size({'width': 1440, 'height': 1050})
                expect(page.locator('#m-content')).to_contain_text('No completed forecast for the latest model run')
                expect(page.locator('#m-run-button')).to_be_enabled()
                page.once('dialog', lambda dialog: dialog.accept())
                page.locator('#m-run-button').click()
                expect(page.locator('#m-forecast-feedback')).to_contain_text('Forecast request accepted', timeout=10000)
                expect(page.locator('#m-generation-status')).to_contain_text('Processing A00-A09', timeout=30000)
                progress_details = page.locator('#m-generation-summary summary').first
                progress_details.focus()
                page.keyboard.press('Enter')
                page.evaluate("window.progressNotice = document.querySelector('#m-generation-summary').firstElementChild; window.elapsedBefore = document.querySelector('#m-generation-elapsed').textContent")
                page.wait_for_function("document.querySelector('#m-generation-elapsed').textContent !== window.elapsedBefore")
                assert page.evaluate("window.progressNotice === document.querySelector('#m-generation-summary').firstElementChild")
                expect(progress_details).to_be_focused()
                expect(progress_details.locator('..')).to_have_attribute('open', '')
                page.screenshot(path=str(EVIDENCE / 'phase2-forecast-processing.png'), full_page=True)
                page.set_viewport_size({'width': 375, 'height': 844})
                batch_table = page.locator('#m-generation-summary .m-table')
                assert batch_table.evaluate("e => getComputedStyle(e).overflowWrap === 'normal' && e.scrollWidth > e.clientWidth")
                batch_table.focus()
                page.keyboard.press('ArrowRight')
                page.wait_for_function("document.querySelector('#m-generation-summary .m-table').scrollLeft > 0")
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
                page.screenshot(path=str(EVIDENCE / 'headers-forecast-running-mobile.png'), full_page=True)
                page.set_viewport_size({'width': 1440, 'height': 1050})
                other = page.context.new_page()
                other.goto('http://127.0.0.1:8073/?module=Forecasting')
                expect(other.locator('#m-run-button')).to_be_disabled()
                expect(other.locator('#m-generation-status')).to_contain_text('Processing A00-A09')
                other.reload()
                expect(other.locator('#m-generation-status')).to_contain_text('Processing A00-A09')
                expect(other.locator('#m-run-button')).to_be_disabled()
                other.locator('.m-account summary').click()
                other.get_by_role('link', name='Sign out', exact=True).click()
                expect(other.locator('.m-auth')).to_contain_text('A forecast is running')
                other.screenshot(path=str(EVIDENCE / 'phase3-running-signout.png'), full_page=True)
                other.get_by_role('link', name='Cancel sign out').click()
                expect(other.locator('.m-topbar')).to_be_visible()
                other.close()
                page.once('dialog', lambda dialog: dialog.dismiss())
                with page.expect_event('dialog'):
                    page.locator('#m-stop-button').click()
                expect(page.locator('#m-generation-status')).to_contain_text('Processing A00-A09')
                page.once('dialog', lambda dialog: dialog.accept())
                with page.expect_event('dialog'):
                    page.locator('#m-stop-button').click()
                expect(page.locator('#m-generation-status')).to_contain_text('Batch cancelled', timeout=15000)
                expect(page.locator('#m-run-button')).to_be_enabled()
                page.once('dialog', lambda dialog: dialog.accept())
                page.locator('#m-run-button').click()
                expect(page.locator('#m-generation-status')).to_contain_text('Processing A00-A09', timeout=30000)
                release_model.touch()
                expect(page.locator('#m-generation-status')).to_contain_text('Batch partial', timeout=120000)
                expect(page.locator('#m-generation-status')).to_contain_text('7 of 7 groups processed', timeout=15000)
                expect(page.locator('#m-generation-status')).to_contain_text('5 failed')
                expect(page.locator('#m-generation-status')).to_contain_text('No monthly observations supplied to the model workflow.')
                expect(page.locator('#m-generation-status')).not_to_contain_text('xgboost_insufficient_history')
                expect(page.locator('#m-generation-status [role=timer]')).to_have_attribute('aria-live', 'off')
                expect(page.locator('#m-generation-summary .m-notice--warning')).to_be_visible()
                expect(page.locator('#m-content')).to_contain_text('Forecast period: 2026-01 to 2026-12')
                page.wait_for_function("document.querySelector('#m-content .js-plotly-plot')?.layout?.xaxis?.range?.[0] === '2025-01-01'")
                history_radio = page.locator('#m-history-window input[type=radio]').first
                expect(page.locator('.m-section-heading #m-chart-controls')).to_be_visible()
                expect(page.locator('#m-saved-forecast > .m-section-heading #m-chart-controls')).to_be_visible()
                capture_phase2('Forecasting-saved')
                chart_box = page.locator('#m-saved-forecast').bounding_box()
                estimates_box = page.locator('#m-forecast-estimates').bounding_box()
                assert abs(chart_box['y'] - estimates_box['y']) < 2
                assert chart_box['width'] > estimates_box['width']
                history_radio.focus()
                page.keyboard.press('ArrowRight')
                page.wait_for_function("document.querySelector('#m-content .js-plotly-plot')?.layout?.xaxis?.autorange !== false && !document.querySelector('#m-content .js-plotly-plot')?.layout?.xaxis?.range?.[0]?.startsWith('2025')")
                page.locator('#m-history-window').get_by_text('Recent history + forecast', exact=True).click()
                expect(page.locator('#m-generation-summary')).to_contain_text('Projected Top Five unavailable')
                expect(page.locator('#m-content')).to_contain_text('Provisional estimates for research use. Not for clinical decisions.')
                forecast_table = page.locator('#m-content .m-panel').filter(has=page.get_by_role('heading', name='Estimated consultations · first 12 forecast months'))
                expect(forecast_table.locator('tbody tr')).to_have_count(12)
                expect(forecast_table).to_contain_text('2026-12')
                page.screenshot(path=str(EVIDENCE / 'phase1-forecast-12-months.png'), full_page=True)
                page.locator('#m-horizon').get_by_text('3 months', exact=True).click()
                expect(page.locator('#m-content')).to_contain_text('showing 3 months')
                radio = page.locator('#m-horizon input[type=radio]').first
                radio.focus()
                page.keyboard.press('ArrowRight')
                expect(page.locator('#m-content')).to_contain_text('showing 6 months')
                page.locator('#m-horizon').get_by_text('3 months', exact=True).click()
                expect(page.locator('#m-content')).to_contain_text('Prediction intervals are not available')
                with store.connect() as db:
                    assert db.execute('SELECT count(*) FROM forecast_values').fetchone()[0] == 24
                page.screenshot(path=str(EVIDENCE / 'monthly-prototype-forecast.png'), full_page=True)
                navigate('Dashboard')
                expect(page.locator('#m-content')).to_contain_text('Overall ranking')
                expect(page.locator('#m-content')).to_contain_text('Estimated consultations, Jan to Dec 2026')
                expect(page.locator('#m-content')).to_contain_text('Incomplete ranking: 2 valid forecasts')
                expect(page.get_by_text('Provisional estimates for research use. Not for clinical decisions.', exact=True)).to_have_count(1)
                page.wait_for_function("document.querySelector('.js-plotly-plot')._fullLayout._size.h > 150")
                ranking_rows = page.locator('.m-ranking-card > .m-ranking-list > li')
                expect(page.locator('#m-content .m-panel--featured')).to_have_count(1)
                measure_text(page.locator('.m-panel--featured .m-panel-heading-text h3'), 'Featured white title on navy')
                measure_text(page.locator('.m-ranking-card .m-badge--warning'), 'Amber provisional badge')
                expect(ranking_rows).to_have_count(2)
                for index in range(2):
                    assert ranking_rows.nth(index).get_attribute('aria-label').startswith(f'Rank {index + 1} of 2,')
                expect(page.locator('.m-ranking-list .m-sort-button')).to_have_count(0)
                assert page.locator('#m-context').bounding_box()['y'] < page.locator('.m-ranking-card').bounding_box()['y']
                page.screenshot(path=str(EVIDENCE / 'phase1-incomplete-ranking.png'), full_page=True)
                navigate('Data & Quality')
                expect(page.locator('#m-coverage')).to_contain_text('No monthly observations supplied to the model workflow.')
                upload_box = page.locator('#m-data-controls').bounding_box()
                coverage_box = page.locator('#m-coverage').bounding_box()
                assert abs(upload_box['y'] - coverage_box['y']) < 2
                assert coverage_box['x'] > upload_box['x'] and coverage_box['width'] > upload_box['width']
                page.locator('#m-note').fill('Browser review note; source counts unchanged.')
                page.get_by_role('button', name='Save annotation', exact=True).click()
                expect(page.locator('#m-note-list')).to_contain_text('Browser review note; source counts unchanged.')
                absent = page.locator('#m-coverage .m-data-table').first.locator('tbody tr').filter(has_text='A80-A89')
                expect(absent).to_contain_text('Not in upload')
                expect(absent.locator('td').nth(2)).to_have_text('—')
                page.screenshot(path=str(EVIDENCE / 'phase1-quality.png'), full_page=True)
                capture_phase2('Data-Quality', phase='layout-phase3', has_plot=False)
                navigate('Disease Trends')
                annual = page.locator('#m-content .m-panel').filter(has=page.get_by_role('heading', name='Annual Top-5 history'))
                for year in ('2020', '2022'):
                    expect(annual.locator('tbody tr').filter(has_text=year)).to_contain_text('Unknown')
                navigate('Notifications')
                expect(page.locator('#m-content')).not_to_contain_text('xgboost_insufficient_history')
                expect(page.locator('#m-content')).to_contain_text('Forecast run: 2 completed, 5 failed')
                expect(page.get_by_role('heading', name='Dataset reporting coverage', exact=True)).to_have_count(1)
                page.screenshot(path=str(EVIDENCE / 'phase1-notifications.png'), full_page=True)
                measure_text(page.locator('.m-activity-item small').first, 'Notification timestamp')
                page.once('dialog', lambda dialog: dialog.dismiss())
                page.locator('#m-read-button').click()
                expect(page.locator('#m-content .m-badge').first).to_have_text('Unread')
                page.once('dialog', lambda dialog: dialog.accept())
                page.locator('#m-read-button').click()
                expect(page.locator('#m-message')).to_contain_text('Visible notifications marked read')
                read_filter = page.locator('#m-notification-status')
                read_filter.focus()
                read_filter.press('Enter')
                expect(read_filter).to_have_attribute('aria-expanded', 'true')
                page.get_by_role('option', name='Unread', exact=True).locator('input').press('Space')
                expect(read_filter).to_contain_text('Unread')
                expect(page.locator('#m-content')).to_contain_text('No matching notifications')
                navigate('Help & About')
                navigate('Notifications')
                expect(page.locator('#m-content')).to_contain_text('No matching notifications')
                read_filter.focus()
                read_filter.press('Enter')
                expect(read_filter).to_have_attribute('aria-expanded', 'true')
                page.get_by_role('option', name='All statuses', exact=True).click()
                expect(read_filter).to_contain_text('All statuses')
                expect(page.locator('#m-content')).to_contain_text('Forecast run')
                page.set_viewport_size({'width': 1440, 'height': 300})
                expect(page.locator('#m-notification-controls')).not_to_have_class(__import__('re').compile(r'.*m-sticky-fits.*'))
                page.set_viewport_size({'width': 1440, 'height': 1050})
                navigate('Model Performance')
                expect(page.locator('#m-content')).to_contain_text('Prophet baseline')
                expect(page.locator('#m-content')).to_contain_text('MAE improvement from correction')
                chart_box = page.locator('#m-performance-chart').bounding_box()
                comparison_box = page.locator('#m-performance-comparison').bounding_box()
                assert abs(chart_box['y'] - comparison_box['y']) < 2
                assert chart_box['width'] > comparison_box['width']
                assert page.locator('.m-performance-summary').bounding_box()['y'] < chart_box['y']
                capture_phase2('Model-Performance', phase='layout-phase3')
                comparison = page.get_by_text('View comparison values', exact=True)
                comparison.focus()
                page.keyboard.press('Enter')
                expect(comparison.locator('xpath=..')).to_have_attribute('open', '')
                expect(comparison.locator('xpath=..').locator('table')).to_be_visible()
                page.screenshot(path=str(EVIDENCE / 'monthly-prototype-performance.png'), full_page=True)
                for module in ('Dashboard', 'Disease Trends', 'Forecasting', 'Model Performance', 'Data & Quality', 'Reports', 'Notifications', 'Help & About'):
                    navigate(module)
                    if module in ('Reports', 'Notifications', 'Help & About'):
                        capture_final_layout(module.replace(' ', '-'))
                    if module == 'Reports':
                        for extension in ('html', 'json', 'csv'):
                            with page.expect_download() as downloaded:
                                page.locator('#m-report-' + extension).click()
                            assert downloaded.value.suggested_filename.endswith('.' + extension)
                    expect(page.locator('#m-heading')).to_contain_text(module)
                    page.screenshot(path=str(EVIDENCE / ('phase3-desktop-' + module.replace(' ', '-') + '.png')), full_page=True)
                    expect(page.locator('#m-content .m-panel--featured')).to_have_count(1 if module == 'Dashboard' else 0)
                    keyboard_target = page.locator('#m-content summary:visible, #m-content button:visible, #m-content a:visible').first
                    if keyboard_target.count():
                        keyboard_target.focus()
                        page.keyboard.press('Tab')
                        assert page.evaluate('getComputedStyle(document.activeElement).outlineStyle') != 'none'
                navigate('Forecasting')
                expect(page.locator('#m-content')).to_contain_text('Saved forecast')
                page.set_viewport_size({'width': 375, 'height': 844})
                page.emulate_media(reduced_motion='reduce')
                assert page.locator('#m-run-button').evaluate("e => e.getBoundingClientRect().height") >= 48
                assert page.locator('#m-run-button').evaluate("e => getComputedStyle(e).animationName") == 'none'
                assert page.locator('#m-run-button').evaluate("e => getComputedStyle(e).transitionDuration") == '0s'
                expect(page.locator('#m-menu-toggle')).to_be_visible()
                expect(page.locator('#m-forecast-controls')).to_be_visible()
                page.wait_for_function('document.documentElement.scrollWidth <= innerWidth + 1')
                page.screenshot(path=str(EVIDENCE / 'monthly-mobile.png'), full_page=True)
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'), page.evaluate("Array.from(document.querySelectorAll('body *')).filter(e=>e.getBoundingClientRect().right>innerWidth+1).slice(0,12).map(e=>({tag:e.tagName,id:e.id,cls:e.className,width:e.getBoundingClientRect().width}))")
                for module in ('Dashboard', 'Disease Trends', 'Data & Quality', 'Notifications', 'Model Performance', 'Reports', 'Help & About'):
                    navigate(module)
                    expect(page.locator('#m-heading')).to_contain_text(module)
                    page.wait_for_function('document.documentElement.scrollWidth <= innerWidth + 1')
                    page.screenshot(path=str(EVIDENCE / ('phase1-mobile-' + module.replace(' ', '-') + '.png')), full_page=True)
                navigate('Dashboard')
                expect(page.locator('#m-content')).to_contain_text('Monthly consultation trend')
                page.locator('.m-account summary').click()
                page.get_by_role('link', name='Sign out', exact=True).click()
                expect(page.get_by_role('heading', name='Sign in', exact=True)).to_be_visible()
                page.locator('input[name=username]').fill('viewer')
                page.locator('input[name=password]').fill('viewer-test-password')
                page.get_by_role('button', name='Sign in', exact=True).click()
                navigate('Data & Quality')
                expect(page.locator('#m-data-controls')).to_be_hidden()
                expect(page.locator('#m-content')).to_contain_text('Data provenance')
                expect(page.locator('#m-coverage')).to_contain_text('Coverage and data quality')
                expect(page.locator('#m-coverage')).to_have_class('m-span-12')
                expect(page.locator('#m-note-form')).to_be_hidden()
                navigate('Reports')
                for extension in ('html', 'json', 'csv'):
                    with page.expect_download() as downloaded:
                        page.locator('#m-report-' + extension).click()
                    assert downloaded.value.suggested_filename.endswith('.' + extension)
                assert not errors, errors
                (EVIDENCE / 'phase2-measurements.json').write_text(json.dumps(measurements, indent=2))
                browser.close()
                print('PASS: login, activation, real prototype forecast callback, 24 persisted values, unavailable Top Five, baseline comparison, HTML report, mobile view and viewer permissions; no browser errors.')
        finally:
            worker_stop.set()
            worker_thread.join(timeout=30)
            server.shutdown()


if __name__ == '__main__':
    main()
