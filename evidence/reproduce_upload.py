"""Exercise the registered Dash HTTP callbacks, including the Malaria approval gate."""
import base64
import json

import app


client = app.server.test_client()


def post(output_id, inputs, states=None, changed=None):
    key = next(k for k in app.dash_app.callback_map if k == output_id or output_id in k.strip('.').split('...'))
    info = app.dash_app.callback_map[key]
    outputs = info['output']
    encode = lambda o: {'id': o.component_id, 'property': o.component_property}
    response = client.post('/_dash-update-component', json={
        'output': key, 'outputs': [encode(o) for o in outputs] if isinstance(outputs, list) else encode(outputs),
        'inputs': [{'id': i['id'], 'property': i['property'], 'value': inputs.get(i['id'])} for i in info['inputs']],
        'state': [{'id': i['id'], 'property': i['property'], 'value': (states or {}).get(i['id'])} for i in info['state']],
        'changedPropIds': changed or [],
    })
    assert response.status_code == 200, response.data
    return response.json['response']


def run():
    assert client.get('/_dash-layout').status_code == 200
    assert client.get('/_dash-dependencies').status_code == 200
    initial = post('store-data.data', {})
    old = initial['store-data']['data']
    summary = initial['store-upload-summary']['data']
    data = base64.b64encode(b'year,month,disease,cases\n2025,1,Dengue,10\n2025,1,Malaria,500\n').decode()
    inputs = {'upload-csv': 'data:text/csv;base64,'+data, 'reset-session-data': 0, 'confirm-upload-catalog': 0}
    states = {'upload-csv': 'malaria.csv', 'store-data': old, 'store-upload-summary': summary,
              'date-convention': 'day-first', 'store-pending-upload': None}
    staged = post('store-data.data', inputs, states, ['upload-csv.contents'])
    assert 'store-data' not in staged and 'store-upload-summary' not in staged
    pending = staged['store-pending-upload']['data']
    ui = post('upload-summary-content.children', {'store-upload-summary': summary, 'store-pending-upload': pending})
    table = next(c for c in ui['upload-summary-content']['children'] if c['type'] == 'DataTable')
    assert [r['disease'] for r in table['props']['data']] == ['Dengue','Malaria']
    button = post('confirm-upload-catalog.children', {'store-pending-upload': pending})['confirm-upload-catalog']
    assert button == {'children':'Use these 2 diseases','disabled':False}
    print('Dash layout/dependencies: HTTP 200')
    print('Upload: Dengue=10; Malaria=500')
    print('Before confirmation: active store unchanged; active summary unchanged')
    print('Visible confirmation table: '+json.dumps(table['props']['data']))
    print('Confirmation button: '+json.dumps(button))
    before = post('metric-row.children', {'store-data':old,'f-year':[2016,2025],'f-disease':'all'})
    assert 'Malaria' not in json.dumps(before['metric-row'])
    print('Before confirmation: Malaria absent from active summary cards')
    inputs['confirm-upload-catalog'] = 1
    states['store-pending-upload'] = pending
    confirmed = post('store-data.data', inputs, states, ['confirm-upload-catalog.n_clicks'])
    active = confirmed['store-data']['data']
    assert confirmed['store-pending-upload']['data'] is None
    after = post('metric-row.children', {'store-data':active,'f-year':[2025,2025],'f-disease':'all'})
    print('After explicit confirmation, actual metric-row output:')
    print(json.dumps(after['metric-row'],ensure_ascii=True))
    assert 'Malaria' in json.dumps(after['metric-row'])
    print('PASS: Malaria is visible for approval before it becomes Top disease.')


if __name__ == '__main__':
    run()
