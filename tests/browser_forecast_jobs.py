"""Manual Edge/Playwright check of job controls using synthetic worker responses."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
EVIDENCE = ROOT / 'evidence' / 'forecast-jobs' / os.environ.get('WEEKLY_BROWSER_RUN', time.strftime('%Y%m%d-%H%M%S'))


def serve():
    import app
    from dashboard.weekly import ui, jobs
    from tests.test_forecast_jobs import active_data, result_for
    active = active_data()
    active['context'] = 'Synthetic / Demo Data'
    active['eligible'] = False
    active['metadata']['dataset_type'] = 'synthetic'
    active['metadata']['source_file'] = 'synthetic-job-ui-fixture'
    active['metadata']['provenance'] = 'Browser test fixture, not research evidence'
    queue = jobs.Queue(EVIDENCE / 'browser.sqlite3')
    attempts, submissions, polls = {}, [], {}
    def submit(dataset, disease, config):
        state = queue.submit(dataset, disease, config)
        if state['status'] == 'queued':
            identity, attempt = queue.claim()
            attempts[identity] = (attempt, dataset, config)
            submissions.append(identity)
            queue.progress(identity, attempt, {'stage': 'SARIMA screening', 'detail': 'Synthetic fixture: window 1/3; candidate 12/144'})
        return queue.status(state['id'])
    def poll(identity):
        state = queue.status(identity)
        polls[identity] = polls.get(identity, 0) + 1
        if state['status'] == 'cancelling':
            with queue.connect() as db:
                db.execute("UPDATE jobs SET status='cancelled' WHERE id=?", (identity,))
        elif len(submissions) >= 2 and polls[identity] >= 2 and state['status'] == 'running':
            attempt, dataset, config = attempts[identity]
            queue.finish(identity, attempt, result_for(dataset, config))
        return queue.status(identity)
    ui.jobs.submit, ui.jobs.poll, ui.jobs.cancel = submit, poll, queue.cancel
    def initialize(component):
        if getattr(component, 'id', None) == 'w-active':
            component.data = active
        children = getattr(component, 'children', None)
        for child in children if isinstance(children, (list, tuple)) else [children]:
            if child is not None:
                initialize(child)
    initialize(app.dash_app.layout)
    app.dash_app.run(host='127.0.0.1', port=8067, debug=False)


def browser():
    sys.path.insert(0, str(ROOT / '.browser-tools'))
    from playwright.sync_api import sync_playwright, expect
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    # A distinct directory per manual run avoids modifying any previous evidence.
    if (EVIDENCE / 'browser.sqlite3').exists():
        raise RuntimeError('Browser evidence already exists; choose a new evidence directory before rerunning.')
    log = (EVIDENCE / 'server.log').open('w', encoding='utf-8')
    process = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), '--serve'], cwd=ROOT,
                               env={**os.environ, 'WEEKLY_BROWSER_RUN': EVIDENCE.name},
                               stdout=log, stderr=log,
                               creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
    try:
        for _ in range(100):
            try:
                urlopen('http://127.0.0.1:8067/healthz', timeout=1).close()
                break
            except OSError:
                time.sleep(.1)
        with sync_playwright() as p:
            browser = p.chromium.launch(channel='msedge', headless=True)
            page = browser.new_page(viewport={'width': 1280, 'height': 900})
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.on('response', lambda response: errors.append(f'{response.status} {response.url}') if response.status >= 400 else None)
            page.goto('http://127.0.0.1:8067')
            page.get_by_text('Forecast', exact=True).first.click()
            page.locator('#w-run').click()
            expect(page.locator('#w-fitting')).to_contain_text('SARIMA screening')
            expect(page.locator('#w-run')).to_be_disabled()
            expect(page.locator('#w-cancel-forecast')).to_be_enabled()
            page.screenshot(path=str(EVIDENCE / 'running.png'), full_page=True)
            page.get_by_text('About', exact=True).first.click()
            expect(page.locator('#w-content')).to_contain_text('How the forecast works')
            page.get_by_text('Forecast', exact=True).first.click()
            page.locator('#w-cancel-forecast').click()
            expect(page.locator('#w-run')).to_be_enabled(timeout=15000)
            expect(page.locator('#w-content')).to_contain_text('Forecast cancelled')
            page.locator('#w-run').click()
            expect(page.locator('#w-fitting')).to_contain_text('Completed', timeout=20000)
            expect(page.locator('.legendtext').filter(has_text='primary')).to_be_visible()
            expect(page.locator('#w-cancel-forecast')).to_be_disabled()
            page.screenshot(path=str(EVIDENCE / 'completed.png'), full_page=True)
            page.evaluate("sessionStorage.removeItem('w-result'); sessionStorage.removeItem('w-result-timestamp')")
            page.reload()
            page.get_by_text('Forecast', exact=True).first.click()
            page.locator('#w-run').click()
            expect(page.locator('#w-fitting')).to_contain_text('Completed', timeout=5000)
            expect(page.locator('.legendtext').filter(has_text='primary')).to_be_visible()
            assert not errors, errors
            (EVIDENCE / 'checks.json').write_text(json.dumps({'running_progress': True, 'navigation_during_job': True,
                'cancel': True, 'completion': True, 'disk_cache_after_browser_result_clear': True,
                'browser_errors': errors, 'source': 'Synthetic UI fixture; no research models fitted'}, indent=2), encoding='utf-8')
            browser.close()
            print(EVIDENCE)
    finally:
        process.terminate()
        process.wait(timeout=10)
        log.close()


if __name__ == '__main__':
    serve() if '--serve' in sys.argv else browser()
