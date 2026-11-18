"""Sidebar state captures and keyboard/contrast checks with isolated accounts."""
from pathlib import Path
import json
import sys
import tempfile
import threading
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dash import Dash
from playwright.sync_api import sync_playwright, expect
from werkzeug.serving import make_server
from dashboard.monthly.store import Store
from dashboard.monthly.security import create_user
from dashboard.monthly.ui import install


def contrast(a, b):
    def lum(color):
        values = [int(color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        return sum((v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4) * w
                   for v, w in zip(values, (.2126, .7152, .0722)))
    x, y = sorted((lum(a), lum(b)))
    return (y + .05) / (x + .05)


def main():
    before = '--before' in sys.argv
    output = ROOT / '.artifacts/sidebar-states' / ('before' if before else 'after')
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='sidebar-') as directory:
        store = Store(Path(directory) / 'state.sqlite3')
        create_user(store, 'researcher', 'a-long-test-password', bootstrap=True)
        app = Dash(__name__, assets_folder=str(ROOT / 'dashboard/assets'))
        install(app, store)
        server = make_server('127.0.0.1', 8074, app.server, threaded=True)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            with sync_playwright() as pw:
                browser = pw.chromium.launch(channel='msedge', headless=True)
                page = browser.new_page()
                errors = []
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.goto('http://127.0.0.1:8074/')
                page.locator('#login-username').fill('researcher')
                page.locator('#login-password').fill('a-long-test-password')
                page.get_by_role('button', name='Sign in', exact=True).click()
                expect(page.locator('#m-heading h1')).to_have_text('Dashboard')
                def visit(name, width):
                    page.goto('http://127.0.0.1:8074/?module=' + quote(name))
                    expect(page.locator('#m-heading h1')).to_have_text(name)
                    if width < 1200:
                        expect(page.locator('#m-sidebar')).to_be_hidden()
                        page.screenshot(path=str(output / f'{width}-closed.png'))
                        page.locator('#m-menu-toggle').click()
                    expect(page.locator('#m-sidebar')).to_be_visible()
                for width in (1440, 1024, 375):
                    page.set_viewport_size({'width': width, 'height': 900})
                    for group, name in [('Analyze', 'Dashboard'), ('Data', 'Data & Quality'), ('Support', 'Help & About')]:
                        visit('Reports' if name == 'Dashboard' else 'Dashboard', width)
                        link = page.locator('#m-sidebar').get_by_role('link', name=name, exact=True)
                        default_box = link.bounding_box()
                        for state in ('default', 'hover', 'focus', 'selected', 'selected-hover', 'selected-focus'):
                            if state == 'selected':
                                visit(name, width)
                            page.mouse.move(width - 1, 899)
                            link.evaluate('e => e.blur()')
                            if 'hover' in state:
                                link.hover()
                            if 'focus' in state:
                                page.keyboard.press('Tab')
                                link.focus()
                            if not before:
                                expect(page.locator('[aria-current=page]')).to_have_count(1)
                                assert link.evaluate('e => getComputedStyle(e).textDecorationLine') == 'none'
                                assert link.bounding_box()['height'] >= 48
                                if state == 'hover':
                                    assert link.evaluate('e => getComputedStyle(e).backgroundColor') == 'rgb(36, 70, 94)'
                                if state.startswith('selected'):
                                    assert link.evaluate('e => getComputedStyle(e).backgroundColor') == 'rgb(40, 81, 106)'
                                    assert link.evaluate('e => getComputedStyle(e).borderLeftColor') == 'rgb(131, 213, 206)'
                                    assert link.bounding_box() == default_box
                                assert link.evaluate('e => getComputedStyle(e).color') == 'rgb(255, 255, 255)'
                                if 'focus' in state:
                                    assert link.evaluate("e => e.matches(':focus-visible') && getComputedStyle(e).outlineOffset === '-8px'")
                                    assert link.evaluate('e => getComputedStyle(e).outlineColor') == 'rgb(255, 255, 255)'
                            page.screenshot(path=str(output / f'{width}-{group}-{state}.png'))
                    # Actual Tab order, Enter activation, overlay focus recovery and short-height scroll.
                    visit('Dashboard', width)
                    if width == 1440:
                        page.keyboard.press('Tab')
                        expect(page.locator('.m-skip-link')).to_be_focused()
                    else:
                        expect(page.locator('#m-menu-close')).to_be_focused()
                    links = page.locator('.m-sidebar-link')
                    for i in range(links.count()):
                        page.keyboard.press('Tab')
                        expect(links.nth(i)).to_be_focused()
                    page.keyboard.press('Enter')
                    expect(page.locator('#m-heading h1')).to_have_text('Help & About')
                    if width < 1200:
                        expect(page.locator('#m-sidebar')).to_be_hidden()
                        page.locator('#m-menu-toggle').click()
                    if not before:
                        assert page.locator('.m-sidebar .m-brand p').count() == 0
                        x = page.locator('.m-sidebar .m-brand strong').bounding_box()['x']
                        labels = page.locator('.m-nav-group-label')
                        assert labels.first.evaluate('e => getComputedStyle(e).color') == 'rgb(197, 215, 229)'
                        assert page.locator('#m-sidebar').evaluate('e => getComputedStyle(e).backgroundColor') == 'rgb(23, 50, 77)'
                        assert labels.evaluate_all("els => els.every(e => e.tagName === 'P' && e.tabIndex === -1)")
                        assert abs(labels.first.bounding_box()['x'] - x) < 1
                        assert links.first.evaluate("e => {const r=document.createRange();r.selectNodeContents(e);return r.getBoundingClientRect().x}") == x
                        assert links.first.bounding_box()['x'] == page.locator('#m-sidebar').bounding_box()['x']
                    page.set_viewport_size({'width': width, 'height': 320})
                    sidebar = page.locator('#m-sidebar')
                    assert sidebar.evaluate('e => e.scrollHeight > e.clientHeight')
                    links.last.focus()
                    assert sidebar.evaluate('e => e.scrollTop > 0')
                    page.screenshot(path=str(output / f'{width}-short.png'))
                    if width < 1200:
                        page.keyboard.press('Escape')
                        expect(page.locator('#m-menu-toggle')).to_be_focused()
                if not before:
                    for width in (1024, 375):
                        touch_context = browser.new_context(viewport={'width': width, 'height': 900}, has_touch=True, is_mobile=True)
                        touch_context.add_cookies(page.context.cookies())
                        touch = touch_context.new_page()
                        touch.goto('http://127.0.0.1:8074/')
                        expect(touch.locator('#m-heading h1')).to_have_text('Dashboard')
                        touch.locator('#m-menu-toggle').tap()
                        touch.locator('#m-sidebar').get_by_role('link', name='Reports', exact=True).tap()
                        expect(touch.locator('#m-heading h1')).to_have_text('Reports')
                        expect(touch.locator('#m-sidebar')).to_be_hidden()
                        touch.locator('#m-menu-toggle').tap()
                        expect(touch.locator('.m-sidebar-link[aria-current=page]')).to_have_text('Reports')
                        touch.screenshot(path=str(output / f'{width}-touch.png'))
                        touch_context.close()
                    pairs = {'item/rail': ('#ffffff', '#17324d'), 'label/rail': ('#c5d7e5', '#17324d'),
                             'selected text/fill': ('#ffffff', '#28516a'), 'focus/rail': ('#ffffff', '#17324d'),
                             'focus/hover': ('#ffffff', '#24465e'), 'focus/selected': ('#ffffff', '#28516a'),
                             'hover/rail': ('#24465e', '#17324d'), 'bar/selected': ('#83d5ce', '#28516a')}
                    ratios = {k: round(contrast(*v), 2) for k, v in pairs.items()}
                    (output / 'contrast.json').write_text(json.dumps(ratios, indent=2))
                    assert all(v >= (4.5 if k in ('item/rail', 'label/rail', 'selected text/fill') else 3)
                               for k, v in ratios.items() if k != 'hover/rail')
                assert not errors, errors
                browser.close()
                print('PASS: sidebar states, keyboard navigation and short-window scrolling; stage=' + ('before' if before else 'after'))
        finally:
            server.shutdown()


if __name__ == '__main__':
    main()
