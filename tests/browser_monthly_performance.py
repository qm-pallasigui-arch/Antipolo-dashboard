"""Repeatable navigation benchmark; synthetic seven-group data, isolated database."""
import json
import logging
from pathlib import Path
import sys
import tempfile
import threading
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pandas as pd
from dash import Dash
from playwright.sync_api import expect, sync_playwright
from plotly.utils import PlotlyJSONEncoder
from werkzeug.serving import make_server
from dashboard.monthly.forecasting.config import CANDIDATE_BLOCKS
from dashboard.monthly.security import create_user
from dashboard.monthly.store import Store
from dashboard.monthly.ui import install
from dashboard.monthly.views import page_content
from tests.test_monthly_system import frame


def main():
    logging.getLogger('werkzeug').setLevel(logging.ERROR)
    result = {'server': {}, 'browser': []}
    with tempfile.TemporaryDirectory(prefix='monthly-performance-') as directory:
        store = Store(Path(directory) / 'state.sqlite3')
        uid = create_user(store, 'researcher', 'long-test-password', bootstrap=True)
        user = dict(id=uid, username='researcher', role='admin', active=1)
        base = frame()
        base = base[base.icd10_block == 'A00-A09']
        data = pd.concat([base.assign(icd10_block=c, icd10_description='Synthetic ' + c) for c in CANDIDATE_BLOCKS])
        years = sorted(data.year.unique())
        codes = list(CANDIDATE_BLOCKS)
        data = data[[((codes.index(row.icd10_block) - years.index(row.year)) % 7) < 5 for row in data.itertuples()]]
        raw = data.to_csv(index=False).encode()
        staged = store.stage(user, raw, 'synthetic.csv')
        store.activate(user, staged['candidate_id'])
        dataset = store.active()
        pages = ['Dashboard', 'Disease Trends', 'Forecasting', 'Model Performance & Insights', 'Data & Quality', 'Reports', 'Notifications', 'Help & About']
        for name in pages:
            start = perf_counter()
            payload = json.dumps(page_content(store, user, name, dataset, 'A00-A09'), cls=PlotlyJSONEncoder)
            result['server'][name] = dict(ms=round((perf_counter()-start)*1000), bytes=len(payload), components=payload.count('dash_html_components'))
        app = Dash('monthly_performance', assets_folder=str(ROOT / 'dashboard/assets'))
        install(app, store)
        server = make_server('127.0.0.1', 8074, app.server, threaded=True)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        errors = []
        try:
            with sync_playwright() as pw:
                browser = pw.chromium.launch(channel='msedge', headless=True)
                page = browser.new_page(viewport={'width': 1440, 'height': 1000})
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.goto('http://127.0.0.1:8074/login')
                page.locator('[name=username]').fill('researcher')
                page.locator('[name=password]').fill('long-test-password')
                page.get_by_role('button', name='Sign in', exact=True).click()
                page.wait_for_load_state('networkidle')
                markers = {'Data & Quality': 'Normalized observations', 'Disease Trends': 'Annual Top-5 history',
                           'Dashboard': 'Monthly consultation trend', 'Forecasting': 'No forecast has been generated',
                           'Model Performance': 'Forecast accuracy', 'Reports': 'What your report includes', 'Help & About': 'About this study'}
                for name in ['Data & Quality', 'Disease Trends', 'Dashboard', 'Forecasting', 'Model Performance', 'Reports', 'Help & About', 'Data & Quality']:
                    start = perf_counter()
                    page.locator('.m-desktop-nav').get_by_text(name, exact=True).click()
                    expect(page.locator('#m-heading')).to_contain_text(name)
                    expect(page.locator('#m-content')).to_contain_text(markers[name])
                    expect(page.locator('#m-content [data-dash-is-loading=true]')).to_have_count(0)
                    if name in ('Data & Quality', 'Disease Trends'):
                        expect(page.locator('#m-content .dash-spreadsheet-container')).to_be_visible()
                    page.wait_for_load_state('networkidle')
                    result['browser'].append(dict(page=name, ms=round((perf_counter()-start)*1000), nodes=page.locator('*').count()))
                page.locator('#m-upload input[type=file]').set_input_files({'name': 'preview.csv', 'mimeType': 'text/csv', 'buffer': raw})
                start = perf_counter()
                expect(page.locator('#m-preview')).to_contain_text('Upload validation and coverage', timeout=30000)
                page.wait_for_load_state('networkidle')
                result['upload'] = dict(ms=round((perf_counter()-start)*1000), nodes=page.locator('*').count())
                # The upload and active dataset both remain fully accessible in pages.
                tables = page.locator('.dash-spreadsheet-container')
                expect(tables).to_have_count(2)
                assert page.locator('.dash-spreadsheet-container tbody tr').count() <= 54
                assert result['upload']['nodes'] < 4000
                page.locator('#m-preview .next-page').click()
                page.locator('.m-desktop-nav').get_by_text('Dashboard', exact=True).click()
                expect(page.locator('#m-content')).to_contain_text('Monthly consultation trend')
                expect(page.locator('#m-preview')).to_be_empty()
                # An unchanged poll must not replace the content or reset local table state.
                with page.expect_response(lambda r: '/_dash-update-component' in r.url and r.request.post_data_json.get('output') == 'm-server-state.data'):
                    page.evaluate("window.dash_clientside.set_props('m-poll', {n_intervals: 499})")
                page.wait_for_timeout(750)
                page.evaluate("window.performanceContent = document.querySelector('#m-content').firstElementChild; window.dash_clientside.set_props('m-poll', {n_intervals: 500})")
                page.wait_for_timeout(1000)
                assert page.evaluate("window.performanceContent === document.querySelector('#m-content').firstElementChild")
                start = perf_counter()
                page.locator('#m-notifications-link').click()
                expect(page.locator('#m-notification-controls')).to_be_visible()
                expect(page.locator('#m-content .m-activity-item').first).to_be_visible()
                result['browser'].append(dict(page='Notifications', ms=round((perf_counter()-start)*1000), nodes=page.locator('*').count()))
                page.locator('.m-desktop-nav').get_by_text('Data & Quality', exact=True).click()
                expect(page.locator('#m-content .dash-spreadsheet-container')).to_be_visible()
                page.locator('#m-notifications-link').click()
                expect(page.locator('#m-content .m-activity-item').first).to_be_visible()
                page.locator('.m-desktop-nav').get_by_text('Data & Quality', exact=True).click()
                expect(page.locator('#m-content .dash-spreadsheet-container')).to_be_visible()
                page.set_viewport_size({'width': 390, 'height': 844})
                page.wait_for_function('document.documentElement.scrollWidth <= innerWidth + 1')
                page.screenshot(path=str(ROOT / 'evidence/ui-refinement-20261030/performance-mobile-data.png'), full_page=True)
                assert not errors, errors
                browser.close()
        finally:
            server.shutdown()
    print(json.dumps(result, indent=2))
    if len(sys.argv) > 1:
        Path(sys.argv[1]).write_text(json.dumps(result, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
