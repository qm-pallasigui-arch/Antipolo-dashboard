"""Exercise the live Dash review and confirmation callbacks without browser state."""
import base64
import json
from pathlib import Path
from urllib.request import Request, urlopen

from dashboard.weekly.transform import read_source

BASE = 'http://127.0.0.1:8050/'
dependencies = json.load(urlopen(BASE + '_dash-dependencies'))
flow = next(d for d in dependencies if 'w-active.data' in d['output'] and 'w-pending.data' in d['output'])
review = next(d for d in dependencies if 'w-activate.disabled' in d['output'])


def invoke(callback, values, changed):
    outputs = [dict(zip(('id', 'property'), part.rsplit('.', 1)))
               for part in callback['output'].strip('.').split('...')]
    body = {'output': callback['output'], 'outputs': outputs, 'changedPropIds': [changed]}
    for kind in ('inputs', 'state'):
        body[kind] = [{**item, 'value': values.get(item['id'] + '.' + item['property'],
                                                [] if item['id'].startswith('{') else None)}
                      for item in callback[kind]]
    request = Request(BASE + '_dash-update-component', data=json.dumps(body).encode(),
                      headers={'Content-Type': 'application/json'})
    return json.load(urlopen(request))['response']


def run():
    path = Path('Antipolo_Disease_Surveillance_2016-2025.xlsx')
    source = read_source('data:;base64,' + base64.b64encode(path.read_bytes()).decode(), path.name)
    values = {'w-source.data': source, 'w-page.value': 'Overview'}
    pending = invoke(flow, values, 'w-source.data')['w-pending']['data']
    # Simulate a review still holding the pre-fix validation error in its store.
    pending['quality']['errors'] = ['Cached blank Week 53 calendar conflict']
    values['w-pending.data'] = pending
    pending = invoke(flow, values, 'w-apply-facts.n_clicks')['w-pending']['data']
    assert pending['quality']['errors'] == [], pending['quality']['errors']
    result = invoke(review, {'w-modal-open.data': True, 'w-pending.data': pending,
                             'w-source.data': source}, 'w-pending.data')
    assert result['w-activate']['disabled'] is False
    values['w-pending.data'] = pending
    result = invoke(flow, values, 'w-activate.n_clicks')
    assert result['w-active']['data']['records'] == pending['records']
    assert result['w-pending']['data'] is None
    assert result['w-page']['value'] == 'Overview'
    print('PASS: live workbook review clears cached errors, enables Confirm & Use Data, and activates all three diseases.')


if __name__ == '__main__':
    run()
