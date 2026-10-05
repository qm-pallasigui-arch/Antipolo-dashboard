"""Guided source upload, transformation review and weekly forecasting."""
import json

import plotly.graph_objects as go
from dash import ALL, Input, Output, State, ctx, dcc, html, no_update

from dashboard.app_instance import app
from dashboard.weekly.charts import forecast_chart
from dashboard.weekly.data import activate, demo, now
from dashboard.weekly.model import cache_key, interpretation, run
from dashboard.weekly.outputs import export_frame, historical_summary, reconcile, save_snapshot, reporting_period
from dashboard.weekly.presentation import (cards, disclosure, eligibility, facts, friendly_reason, notice,
                                           quality_details, quality_messages, table)
from dashboard.weekly.settings import model_configuration, research_requirements
from dashboard.weekly.transform import LABELS, plausible_columns, prepare, read_source, update_facts

PAGES = ['Overview', 'Forecast', 'Historical Trends', 'Data', 'About the Model']
FACT_OPTIONS = {
    'population': [('Ages 5–19', '5–19'), ('All ages', 'all-age')],
    'case_classification': [('Confirmed only', 'confirmed'), ('Suspected', 'suspected'), ('Probable', 'probable'), ('Mixed classifications', 'mixed')],
    'source_system': [('CESU/PIDSAR', 'CESU/PIDSAR'), ('FHSIS (reference data)', 'FHSIS')],
    'reporting_status': [('Historical reporting period complete', 'complete'), ('May still be incomplete', 'incomplete')],
    'dataset_type': [('Real surveillance records', 'real'), ('Synthetic / Demo Data', 'synthetic')],
    'location': [('Antipolo City', 'Antipolo City')],
}
FACT_LABELS = {'population': 'Population', 'case_classification': 'Case Classification', 'source_system': 'Source',
               'reporting_status': 'Reporting Status', 'dataset_type': 'Dataset Type', 'location': 'Location', 'provenance': 'Source reference',
               'reporting_reference': 'CESU/source evidence for historical completeness',
               'calendar_reference': 'CESU/source evidence for reporting-year lengths'}


def advanced(value):
    return html.Pre(json.dumps(value, indent=2, ensure_ascii=False), className='technical-readout')


def installed_protocol_label():
    try:
        return model_configuration().get('label', 'Installed model protocol')
    except (ValueError, OSError):
        return 'Installed model protocol needs administrator review.'


def build_layout():
    return html.Div(className='weekly-app', children=[
        dcc.Store(id='w-active', storage_type='session'), dcc.Store(id='w-pending'), dcc.Store(id='w-source'),
        dcc.Store(id='w-modal-open', data=False), dcc.Store(id='w-result', storage_type='session'), dcc.Download(id='w-download'),
        html.Header(className='outlook-header', children=[
            html.H1('Antipolo Disease Forecasting'),
            html.P('Weekly reports and forecasts for school preparedness.', className='subtitle'),
        ]),
        dcc.Tabs(id='w-page', value='Overview', className='nav-tabs', children=[
            dcc.Tab(label=p, value=p, className='nav-tab', selected_className='nav-tab-selected') for p in PAGES]),
        html.Div([html.Div([html.H2(id='w-page-title'), html.Div(id='w-context', className='context-line')]),
                  html.Div([html.Label('Selected disease', htmlFor='w-disease'), dcc.Dropdown(id='w-disease', clearable=False)],
                           id='w-disease-toolbar', className='disease-picker')], className='page-toolbar'),
        html.Div(id='w-flow-message', **{'aria-live': 'polite'}),
        html.Section(id='w-data-controls', style={'display': 'none'}, children=[
            html.Div([html.H2('Upload Data'), html.P('Upload your weekly disease records. The system will prepare the file automatically and show you what changed before using it.')]),
            dcc.Upload(id='w-upload', children=html.Div([html.Strong('Choose a file or drop it here'), html.P('CSV or Excel workbook · Up to 10 MB')]),
                       multiple=False, className='upload-zone', accept='.csv,.xlsx'),
            html.Div(id='w-upload-status', **{'aria-live': 'polite'}),
            html.Div(id='w-upload-progress', **{'aria-live': 'polite'}),
            html.Div([html.Button('View Transformation Details', id='w-reopen', n_clicks=0, className='secondary'),
                      html.Button('Update Source Information', id='w-edit-facts', n_clicks=0, className='secondary'),
                      html.Button('Reset Dataset', id='w-reset', n_clicks=0, className='quiet'),
                      html.Button('Try Synthetic / Demo Data', id='w-demo', n_clicks=0, className='quiet')], className='actions'),
            html.P('To replace your dataset, choose another file above. Your current data stay in use until you confirm the replacement.', className='muted'),
        ]),
        html.Section(id='w-forecast-controls', style={'display': 'none'}, children=[
            html.Label('How far ahead would you like to look?', htmlFor='w-horizon'),
            dcc.RadioItems(id='w-horizon', options=[{'label': f'Next {n} weeks', 'value': n} for n in (4, 13, 26, 52)], value=13, inline=True, className='choice-row'),
            html.P('Choose how far ahead you want to view the forecast. The underlying model is not retrained when you change the display range.', className='muted'),
            html.Div([html.Button('Generate Forecast', id='w-run', n_clicks=0), html.Button('Download Results', id='w-export', n_clicks=0, className='secondary')], className='actions'),
            html.Div(id='w-fitting', **{'aria-live': 'polite'}),
        ]),
        html.Section(id='w-history-controls', style={'display': 'none'}, children=[
            html.Label('View frequency'), dcc.RadioItems(id='w-aggregation', options=['Weekly', 'Monthly', 'Quarterly'], value='Weekly', inline=True, className='choice-row'),
            html.Div([html.Div([html.Label('From reporting week', id='w-start-label'), dcc.Dropdown(id='w-start', placeholder='First available period')]),
                      html.Div([html.Label('To reporting week', id='w-end-label'), dcc.Dropdown(id='w-end', placeholder='Latest available period')])], className='two-column'),
            html.P(id='w-history-guidance', className='muted'),
        ]),
        dcc.Loading(html.Main(id='w-content'), type='circle', delay_show=250),
        html.Section(id='w-technical-controls', style={'display': 'none'}, children=[
            disclosure('Advanced Details', [html.Div(id='w-advanced'),
                html.Button('Download Detailed Evidence', id='w-export-json', n_clicks=0, className='secondary'),
                disclosure('Future prospective validation', [html.P('Not yet completed. Save a forecast before outcomes are known, then compare it with later reports. Each comparison is retained separately.'),
                    html.Button('Save Forecast Record', id='w-snapshot', n_clicks=0, className='secondary'),
                    html.Label('Saved forecast reference'), dcc.Input(id='w-snapshot-id', placeholder='Reference from a saved forecast', type='text'),
                    html.Button('Compare with Current Reports', id='w-reconcile', n_clicks=0, className='secondary'), html.Div(id='w-snapshot-status')])]),
        ]),
        html.Div(id='w-modal', className='modal-backdrop', style={'display': 'none'}, children=[
            html.Div(className='review-dialog', role='dialog', **{'aria-modal': 'true', 'aria-labelledby': 'w-modal-title'}, children=[
                html.P('REVIEW BEFORE USING', className='eyebrow'), html.H2('Review Data Transformation', id='w-modal-title', tabIndex=-1),
                html.P('Review the worksheets, add source information where needed, then confirm at the bottom. Your active dataset stays unchanged until confirmation.', className='review-intro'),
                html.H3('1. Worksheets and preparation', className='review-step'),
                html.Div(id='w-review'), html.Div(id='w-mapping'),
                html.Button('Apply Worksheet Changes', id='w-apply-mapping', n_clicks=0, className='secondary', style={'display': 'none'},
                            title='Update the prepared preview after changing a field mapping. This does not activate the dataset.'),
                html.Section(id='w-fact-panel', className='review-source-section', style={'display': 'none'}, children=[
                    html.H3('2. Source information', className='review-step'),
                    html.P('Add only source-supported information. Completeness and calendar evidence may be needed for forecasting; unknown facts can remain unspecified.'),
                    html.Div(id='w-facts'),
                    html.Button('Apply Source Information', id='w-apply-facts', n_clicks=0, className='secondary'),
                    html.P('Updates the review below. Your active dataset is not changed yet.', className='muted')]),
                html.Details(id='w-review-extra', children=[html.Summary('3. Data checks and research eligibility'),
                    html.P('Read-only findings and supporting details. These are not another confirmation step.', className='review-detail-note'),
                    html.Div(id='w-review-extra-content')]),
                html.Fieldset(id='w-review-actions', className='modal-actions', children=[
                    html.Div([html.Strong('Final step: use this dataset'),
                              html.P('Confirm & Use Data applies the reviewed data and opens Overview. Cancel keeps your current dataset.', className='muted')], className='review-final-copy'),
                    html.Div(id='w-review-progress', role='status', **{'aria-live': 'polite'}),
                    html.Div(id='w-review-message', **{'aria-live': 'assertive'}),
                    html.Button('Confirm & Use Data', id='w-activate', n_clicks=0, disabled=True),
                    html.Button('Cancel', id='w-cancel', n_clicks=0, className='quiet'),
                    html.Button('Close', id='w-close', n_clicks=0, className='secondary', style={'display': 'none'})]),
            ])]),
        html.Footer('Research focus: ages 5–19 · Confirmed cases · CESU/PIDSAR. Projections support preparedness and should be read alongside current surveillance reports.'),
    ])


@app.callback(Output('w-source', 'data'), Output('w-upload-status', 'children'), Input('w-upload', 'contents'),
              State('w-upload', 'filename'), prevent_initial_call=True,
              running=[(Output('w-upload-progress', 'children'), 'Uploading file…', '')])
def receive_upload(contents, filename):
    if not contents:
        return no_update, no_update
    try:
        return read_source(contents, filename), 'File uploaded successfully. Preparing your weekly data…'
    except ValueError as exc:
        return {'error': str(exc)}, notice(str(exc))


# Clear immediately in the browser so a late server response cannot erase a
# newly chosen replacement file. Active and reviewed data are separate stores.
app.clientside_callback('function() { return null; }', Output('w-upload', 'contents'),
                        Input('w-cancel', 'n_clicks'), Input('w-close', 'n_clicks'),
                        Input('w-activate', 'n_clicks'), Input('w-reset', 'n_clicks'), prevent_initial_call=True)


def selections(ids, values, entered_ids, entered_values):
    chosen = {}
    for identity, value in zip(ids or [], values or []):
        if not isinstance(identity, dict):
            continue
        chosen.setdefault(str(identity['sheet']), {'mapping': {}})['mapping'][identity['field']] = value
    for identity, value in zip(entered_ids or [], entered_values or []):
        if not isinstance(identity, dict):
            continue
        chosen.setdefault(str(identity['sheet']), {'mapping': {}})[identity['field']] = value
    return chosen


def transition(trigger, source, pending, active, choices=None, declarations=None):
    """Single explicit lifecycle boundary, also exercised without the browser."""
    if trigger in ('w-cancel', 'w-close'):
        return active, None, False, 'Your current dataset has not changed.'
    if trigger == 'w-reset':
        return {'audit': (active or {}).get('audit', []) + [{'event': 'reset', 'at': now()}]}, None, False, 'Dataset reset. Upload a file to begin again.'
    if trigger == 'w-reopen':
        return active, None, 'history' if active and active.get('records') else False, ''
    if trigger == 'w-demo':
        return active, demo(), True, ''
    if trigger == 'w-activate':
        if not pending or pending.get('review_only'):
            raise ValueError('Please prepare and review a file before using it.')
        if any((choices or {}).get(str(u['index']), {}).get('included', u['included']) != u['included']
               for u in pending.get('worksheet_units', [])):
            raise ValueError('Worksheet selection changed. Review the updated worksheets before confirming.')
        for i, report in enumerate((pending.get('transformation') or {}).get('sheets', [])):
            choice = (choices or {}).get(str(i), {})
            if report.get('included', True) and any(value and value != report.get('mapping', {}).get(field)
                                                   for field, value in choice.get('mapping', {}).items()):
                raise ValueError('Worksheet mapping changed. Choose Apply Worksheet Changes and review the result before confirming.')
        reviewed = update_facts(pending, declarations or {})
        if reviewed['quality']['errors']:
            raise ValueError(' '.join(reviewed['quality']['errors']))
        return activate(reviewed, active), None, False, 'Your data are ready. Explore the overview or open Forecast.'
    if trigger == 'w-apply-facts':
        if not pending or pending.get('review_only'):
            raise ValueError('Please prepare a file first.')
        return active, update_facts(pending, declarations or {}), True, ''
    if trigger in ('w-apply-mapping', 'w-include') and pending:
        source = (pending.get('transformation') or {}).get('source', source)
    if source and source.get('error'):
        return active, None, False, source['error']
    if not source:
        return active, None, False, ''
    chosen = choices if trigger in ('w-apply-mapping', 'w-include') else None
    metadata = research_requirements()
    if chosen is not None and pending:
        metadata.update(pending.get('review_metadata', pending.get('metadata', {})))
    staged = prepare(source, chosen, metadata, allow_partial=True)
    return active, staged, True, ''


@app.callback(Output('w-pending', 'data', allow_duplicate=True), Output('w-modal-open', 'data', allow_duplicate=True),
              Input('w-edit-facts', 'n_clicks'), State('w-active', 'data'), prevent_initial_call=True)
def edit_source_information(_clicks, active):
    if not active or not active.get('records'):
        return no_update, no_update
    return json.loads(json.dumps(active)), True


@app.callback(Output('w-active', 'data'), Output('w-pending', 'data'), Output('w-modal-open', 'data'),
              Output('w-flow-message', 'children'), Output('w-review-message', 'children'), Output('w-page', 'value'),
              Input('w-source', 'data'), Input('w-apply-mapping', 'n_clicks'), Input('w-activate', 'n_clicks'),
              Input('w-cancel', 'n_clicks'), Input('w-close', 'n_clicks'), Input('w-reopen', 'n_clicks'),
              Input('w-reset', 'n_clicks'), Input('w-demo', 'n_clicks'), Input('w-apply-facts', 'n_clicks'),
              Input({'type': 'w-include', 'sheet': ALL}, 'value'),
              State('w-pending', 'data'), State('w-active', 'data'), State('w-page', 'value'),
              State({'type': 'w-map', 'sheet': ALL, 'field': ALL}, 'id'), State({'type': 'w-map', 'sheet': ALL, 'field': ALL}, 'value'),
              State({'type': 'w-enter', 'sheet': ALL, 'field': ALL}, 'id'), State({'type': 'w-enter', 'sheet': ALL, 'field': ALL}, 'value'),
              State({'type': 'w-fact', 'field': ALL}, 'id'), State({'type': 'w-fact', 'field': ALL}, 'value'),
              State({'type': 'w-include', 'sheet': ALL}, 'id'), prevent_initial_call=True,
              running=[(Output('w-review-progress', 'children'), 'Checking and applying your changes…', ''),
                       (Output('w-review-actions', 'disabled'), True, False),
                       (Output('w-apply-facts', 'disabled'), True, False),
                       (Output('w-apply-mapping', 'disabled'), True, False)])
def manage_dataset(source, _map, _activate, _cancel, _close, _reopen, _reset, _demo, _facts, include_values, pending, active, page,
                   mapping_ids, mapping_values, entered_ids, entered_values, fact_ids, fact_values, include_ids):
    trigger = ctx.triggered_id
    try:
        choices = json.loads(json.dumps((pending or {}).get('worksheet_choices', {})))
        for key, choice in selections(mapping_ids, mapping_values, entered_ids, entered_values).items():
            existing = choices.setdefault(key, {})
            existing['mapping'] = {**existing.get('mapping', {}), **choice.get('mapping', {})}
            existing.update({k: v for k, v in choice.items() if k != 'mapping'})
        for identity, value in zip(include_ids or [], include_values or []):
            if isinstance(identity, dict):
                choices.setdefault(str(identity['sheet']), {})['included'] = value == 'include'
        if isinstance(trigger, dict) and trigger.get('type') == 'w-include':
            # Re-rendering worksheet cards must not restart preparation or
            # discard pending work when the effective selection is unchanged.
            units = (pending or {}).get('worksheet_units', [])
            if not units or all(choices.get(str(u['index']), {}).get('included', u['included']) == u['included'] for u in units):
                return (no_update,) * 6
            trigger = 'w-include'
        declarations = {identity['field']: value for identity, value in zip(fact_ids or [], fact_values or []) if isinstance(identity, dict)}
        current, staged, opened, message = transition(trigger, source, pending, active, choices, declarations)
        return (current if current != active else no_update), staged, opened, (html.Div(message, className='flow-status', role='status') if message and not opened else ''), (notice(message) if opened and message else ''), ('Overview' if trigger == 'w-activate' else no_update)
    except ValueError as exc:
        # A bad replacement never changes the active dataset or enables activation.
        opened = bool(source and not source.get('error')) or bool(pending)
        # Do not emit the same modal-open value on a failed submission: doing
        # so reruns review(), recreates the form, and erases unsaved choices.
        replace_preview = trigger in ('w-source', 'w-apply-mapping')
        error = html.Div([html.Strong('Changes were not applied. '), friendly_reason(str(exc))], role='alert', className='worksheet-error')
        return no_update, None if replace_preview else no_update, opened if replace_preview else no_update, no_update, error, no_update


FIELD_GUIDANCE = {'disease': 'Choose the disease-name column, use the worksheet name, or enter a source-established disease.',
                  'year': 'Choose the reporting year, such as 2025. Do not choose a case-count column.',
                  'morbidity_week': 'Choose the column containing week numbers 1–53.',
                  'case_count': 'Choose weekly case totals. Blank values will stay unreported.'}


def mapping_fields(sheet, index, choice):
    controls = []
    if sheet['unresolved']:
        controls.append(notice('We could not identify all required fields automatically. Please help us match the columns.'))
    for field in sheet['unresolved']:
        selected = choice.get('mapping', {}).get(field)
        fixed = [col for key, col in sheet['mapping'].items() if key not in sheet['unresolved'] and key != field]
        controls.append(html.Div([
            html.Label([LABELS[field], html.Span('Required', className='required-label')]),
            html.P(FIELD_GUIDANCE[field], className='field-guidance'),
            dcc.Dropdown(id={'type': 'w-map', 'sheet': index, 'field': field}, options=column_options(sheet, field, fixed),
                         value=selected, placeholder=f'Choose {LABELS[field]} for {sheet["name"]}', clearable=False),
            *([html.Div([html.Label(f'{LABELS[field]} value (only if entering a value)'),
                         dcc.Input(id={'type': 'w-enter', 'sheet': index, 'field': field}, type='number' if field == 'year' else 'text',
                                   value=choice.get(field), placeholder=f'Enter {LABELS[field].lower()} from the source')])] if field in ('disease', 'year') else []),
        ], id={'type': 'w-field', 'sheet': index, 'field': field}, className='form-field unresolved-field'))
    return controls


def column_options(sheet, field, used=()):
    options = []
    for col in plausible_columns(sheet, field):
        if col in used:
            continue
        samples = [str(r[col]) for r in sheet['rows'][:3] if r.get(col) not in (None, '')]
        options.append({'label': f'{col} · {", ".join(samples) or "blank values"}', 'value': col})
    if field == 'disease' and sheet['worksheet']:
        options.append({'label': 'Use worksheet name as Disease: ' + sheet['worksheet'], 'value': '__worksheet__'})
    if field in ('disease', 'year'):
        options.append({'label': 'Enter a value from the source', 'value': '__entered__'})
    return options


@app.callback(Output({'type': 'w-map', 'sheet': ALL, 'field': ALL}, 'options'),
              Input({'type': 'w-map', 'sheet': ALL, 'field': ALL}, 'value'),
              State({'type': 'w-map', 'sheet': ALL, 'field': ALL}, 'id'), State('w-source', 'data'))
def mapping_options(values, identities, source):
    if not source or source.get('error'):
        return [no_update for _ in identities]
    return [column_options(source['sheets'][identity['sheet']], identity['field'],
                           [value for other, value in zip(identities, values) if isinstance(other, dict) and other['sheet'] == identity['sheet'] and other['field'] != identity['field']]
                           + [value for field, value in source['sheets'][identity['sheet']]['mapping'].items() if field not in source['sheets'][identity['sheet']]['unresolved'] and field != identity['field']]) if isinstance(identity, dict) else no_update
            for identity in identities]


@app.callback(Output({'type': 'w-field', 'sheet': ALL, 'field': ALL}, 'className'),
              Input({'type': 'w-map', 'sheet': ALL, 'field': ALL}, 'value'),
              Input({'type': 'w-enter', 'sheet': ALL, 'field': ALL}, 'value'),
              State({'type': 'w-map', 'sheet': ALL, 'field': ALL}, 'id'),
              State({'type': 'w-enter', 'sheet': ALL, 'field': ALL}, 'id'),
              State({'type': 'w-field', 'sheet': ALL, 'field': ALL}, 'id'))
def required_field_styles(values, entered_values, ids, entered_ids, field_ids):
    chosen = selections(ids, values, entered_ids, entered_values)
    styles = []
    for identity in field_ids:
        if not isinstance(identity, dict):
            styles.append(no_update)
            continue
        choice = chosen.get(str(identity['sheet']), {})
        value = choice.get('mapping', {}).get(identity['field'])
        resolved = bool(value) and (value != '__entered__' or choice.get(identity['field']) not in (None, ''))
        styles.append('form-field resolved-field' if resolved else 'form-field unresolved-field')
    return styles


def fact_fields(dataset):
    controls = []
    meta = dataset['metadata']
    for field, label in FACT_LABELS.items():
        if meta.get(field) not in (None, '', 'unknown'):
            controls.append(html.P([html.Strong(label + ': '), str(meta[field])]))
            continue
        identity = {'type': 'w-fact', 'field': field}
        if field in FACT_OPTIONS:
            control = dcc.Dropdown(id=identity, options=[{'label': 'Not specified', 'value': ''}] +
                                  [{'label': label, 'value': value} for label, value in FACT_OPTIONS[field]], value='', clearable=False)
        else:
            control = dcc.Input(id=identity, type='text', placeholder='Not specified', value='')
        controls.append(html.Div([html.Label(label), control], className='form-field'))
    years = sorted({r['year'] for r in dataset['records']})
    if years:
        calendar = [html.P('Only choose a year length if the source reporting calendar establishes it. This is needed to place weeks across year boundaries; it does not change source week 53 records.')]
        for year in years + [years[-1] + 1]:
            if str(year) in meta.get('year_lengths', {}):
                calendar.append(html.P(f"{year}: {meta['year_lengths'][str(year)]} reporting weeks"))
            else:
                calendar.append(html.Div([html.Label(f'{year} reporting calendar'),
                    dcc.Dropdown(id={'type': 'w-fact', 'field': f'calendar:{year}'}, options=[
                        {'label': 'Not specified', 'value': ''}, {'label': '52 reporting weeks', 'value': 52},
                        {'label': '53 reporting weeks', 'value': 53}], value='', clearable=False)], className='form-field'))
        controls.append(disclosure('Confirm source reporting calendar (optional)', calendar))
    blanks = []
    for index, row in enumerate(dataset['records']):
        if row['case_count'] is not None:
            continue
        blanks.append(html.Div([
            html.Label(f"{row['disease']} · {row['year']} · Week {row['morbidity_week']}"),
            dcc.Dropdown(id={'type': 'w-fact', 'field': f'resolution:{index}'}, value='', clearable=False,
                         options=[{'label': label, 'value': value} for label, value in [
                             ('Leave unchanged', ''), ('Confirmed zero', 'zero'), ('Unreported / missing', 'missing'),
                             ('Nonexistent reporting week (documented calendar required)', 'nonexistent'),
                             ('Corrected source value', 'corrected')]]),
            html.Label('Corrected count (only for corrected source value)'),
            dcc.Input(id={'type': 'w-fact', 'field': f'corrected:{index}'}, type='number', min=0, step=1),
            html.Label('Source evidence for this decision'),
            dcc.Input(id={'type': 'w-fact', 'field': f'evidence:{index}'}, type='text', placeholder='Document/reference and relevant page or cell'),
        ], className='form-field'))
    if blanks:
        controls.append(disclosure('Resolve blank counts individually (source evidence required)', blanks))
    return controls


def worksheet_cards(dataset, editable=False):
    history = dataset['transformation']
    source = history['source']
    units = {u['index']: u for u in dataset.get('worksheet_units', [])}
    children = []
    for i, (sheet, report) in enumerate(zip(source['sheets'], history['sheets'])):
        after = [r for r in dataset.get('records', []) if r.get('source_worksheet') == sheet['worksheet']]
        unit = units.get(i, {'included': report.get('included', True), 'records': after, 'errors': [], 'status': 'ready'})
        included = unit['included']
        body = [html.H3(f'Reviewing worksheet: {sheet["name"]}.')]
        body.append(html.P(f"Detected layout: {'week × year table' if sheet['kind'] == 'week_by_year' else 'row table'} · Status: {unit['status'].replace('_', ' ')}"))
        if editable:
            body.append(dcc.RadioItems(id={'type': 'w-include', 'sheet': i},
                        options=[{'label': 'Include', 'value': 'include'}, {'label': 'Exclude', 'value': 'exclude'}],
                        value='include' if included else 'exclude', inline=True, className='worksheet-choice'))
        else:
            body.append(html.P('Included in this dataset' if included else 'Excluded from this dataset', className='worksheet-status'))
        if sheet.get('suggest_exclude'):
            body.append(html.P('Suggested: Exclude. ' + sheet['exclusion_reason'], className='worksheet-suggestion'))
        if not included:
            body += [html.P('No field matching or confirmation is required for this excluded worksheet.'),
                     disclosure('View excluded source data', table(sheet['rows'], {c: c for c in sheet['columns']}, limit=8))]
        else:
            body += [html.Div(friendly_reason(error), className='worksheet-error', role='alert') for error in unit['errors']]
            body.append(html.Div([
                html.Div([html.H4('Original Uploaded Data'), html.P(source['filename']),
                          html.P(f"{sheet['original_row_count']} source rows · Header on row {sheet['header_row']}"),
                          table(sheet['rows'], {c: c for c in sheet['columns']}, limit=8)]),
                html.Div([html.H4('Prepared Weekly Data'), html.P(f"{len(unit['records'])} weekly observations"),
                          table(unit['records'], LABELS, limit=8) if unit['records'] else html.P('Resolve the highlighted fields or source values to prepare this worksheet.')]),
            ], className='before-after'))
            if sheet['kind'] == 'week_by_year':
                body.append(html.P('Year columns detected: ' + ', '.join(sheet['year_columns'])))
                body.append(html.P('Week × year table recognized. Reporting years and case counts are read automatically from the year columns.', className='inferred-field'))
            mapping = {**sheet['mapping'], **(report.get('mapping') or {})}
            for field, value in mapping.items():
                if field in LABELS and field not in sheet['unresolved']:
                    shown = f"worksheet name: {sheet['worksheet']}" if value == '__worksheet__' else value
                    body.append(html.P(f'{LABELS[field]} identified from {shown}.', className='inferred-field'))
            if editable and unit['status'] == 'needs_mapping':
                body.extend(mapping_fields(sheet, i, dataset.get('worksheet_choices', {}).get(str(i), {})))
            elif editable and mapping.get('disease') == '__worksheet__':
                body.append(disclosure('Change inferred Disease', [
                    dcc.Dropdown(id={'type': 'w-map', 'sheet': i, 'field': 'disease'},
                                 options=column_options(sheet, 'disease'), value='__worksheet__', clearable=False),
                    html.Label('Disease value (only if entering a value)'),
                    dcc.Input(id={'type': 'w-enter', 'sheet': i, 'field': 'disease'}, type='text'),
                    html.P('Choose Apply Worksheet Changes to update the preview before confirming.')]))
            if report['changes']:
                body += [html.H4('What changed?'), html.Ul([html.Li(c) for c in report['changes']])]
            body += [notice(w) for w in report['warnings']]
            excluded_rows = report.get('excluded_rows', [])
            if excluded_rows:
                originals = {sheet['header_row'] + j + 1: row for j, row in enumerate(sheet['rows'])}
                excluded_preview = [{'Worksheet row': r['row'], 'Reason': r['reason'],
                                     'Original values': json.dumps(originals.get(r['row'], {}), ensure_ascii=False)} for r in excluded_rows]
                body.append(disclosure('Review automatically excluded rows',
                                       table(excluded_preview, {k: k for k in excluded_preview[0]}, limit=len(excluded_preview))))
        children.append(html.Section(body, className='worksheet-card' + ('' if included else ' worksheet-excluded'),
                                     **{'data-worksheet-index': str(i)}))
    return children


def transformation_review(dataset, editable=False):
    history = dataset.get('transformation')
    children = []
    if history:
        decisions = dataset.get('metadata', {}).get('blank_resolutions', {})
        if decisions:
            children.append(disclosure('Source-supported blank-count decisions', table([
                {'Disease': d['original']['disease'], 'Year': d['original']['year'], 'Week': d['original']['morbidity_week'],
                 'Decision': d['resolution'], 'Revised count': d['value'], 'Source evidence': d['reference']}
                for d in decisions.values()])))
        problems = [error for unit in dataset.get('worksheet_units', []) if unit['included'] for error in unit['errors']]
        fixes = [f"Worksheet “{report['worksheet']}”: {warning}" for report in history['sheets']
                 for warning in report['warnings'] if warning.startswith('Automatic fix:')]
        if problems:
            children.append(html.Div([html.Strong('Action needed before confirmation'),
                                      html.Ul([html.Li(error) for error in problems])], className='worksheet-error', role='alert'))
        if fixes:
            children.append(html.Div([html.Strong('Automatic fixes applied — review before confirming'),
                                      html.Ul([html.Li(fix) for fix in fixes])], className='worksheet-suggestion', role='alert'))
        children += worksheet_cards(dataset, editable)
        included = sum(report.get('included', True) for report in history['sheets'])
        children.append(html.P(f'{included} included worksheet(s). Only included worksheets will be used when you confirm.'))
    else:
        explanation = ('Synthetic / Demo Data — generated for demonstration, not actual surveillance.'
                       if dataset['metadata'].get('dataset_type') == 'synthetic'
                       else 'The original transformation preview is not available for this dataset. Preserved weekly records are shown below.')
        children += [notice(explanation),
                     html.H3('Prepared Weekly Data'), table(dataset['records'], LABELS, limit=8)]
    children.append(html.P('No missing values were converted to zero.', className='integrity-note'))
    if dataset.get('review_only'):
        children.append(notice('Resolve the highlighted fields on included worksheets, or exclude those worksheets. Include at least one worksheet with weekly records.'))
        return children
    warnings = quality_messages(dataset)
    if warnings:
        children.append(notice(f'We prepared your data, but found {len(warnings)} items you may want to review.'))
        children += [html.P(w) for w in warnings]
    elif not dataset['quality']['errors']:
        children.append(notice('Transformation complete. Your data is ready to use.'))
    if dataset['quality']['errors']:
        children.append(notice('Please resolve the repeated or conflicting source records before using this file.'))
    return children


@app.callback(Output('w-modal', 'style'), Output('w-review', 'children'), Output('w-mapping', 'children'),
              Output('w-apply-mapping', 'style'), Output('w-activate', 'disabled'), Output('w-activate', 'style'),
              Output('w-cancel', 'style'), Output('w-close', 'style'), Output('w-facts', 'children'),
              Output('w-fact-panel', 'style'),
              Input('w-modal-open', 'data'), Input('w-pending', 'data'), State('w-active', 'data'), State('w-source', 'data'))
def review(opened, pending, active, source):
    hidden = {'display': 'none'}
    if not opened:
        return hidden, '', '', hidden, True, hidden, hidden, hidden, '', hidden
    dataset = pending or (active if opened == 'history' and active and active.get('records') else None)
    if not dataset:
        return {}, [notice('Please check the source values and upload a corrected file.'),
                    *[table(s['rows'], {c: c for c in s['columns']}, limit=8) for s in (source or {}).get('sheets', [])]], '', hidden, True, hidden, {}, hidden, '', hidden
    needs_review = dataset.get('review_only', False)
    return ({}, transformation_review(dataset, editable=bool(pending)), '', {} if pending and dataset.get('transformation') else hidden,
            not pending or needs_review or bool(dataset['quality']['errors']),
            {} if pending else hidden, {} if pending else hidden, hidden if pending else {},
            fact_fields(dataset) if pending and not needs_review else '', {} if pending and not needs_review else hidden)


@app.callback(Output('w-review-extra-content', 'children'), Input('w-review-extra', 'open'),
              Input('w-pending', 'data'), Input('w-modal-open', 'data'), State('w-active', 'data'))
def review_checks(expanded, pending, opened, active):
    if not expanded or not opened:
        return ''
    dataset = pending or active
    if not dataset or dataset.get('review_only'):
        return html.P('Resolve required worksheet fields first. Data checks will appear here after preparation.')
    status = eligibility(dataset)
    return [html.H4('Research eligibility'), html.Strong(status.children[0].children), status.children[1],
            *quality_details(dataset), cards(facts(dataset))]


@app.callback(Output('w-disease', 'options'), Output('w-disease', 'value'), Input('w-active', 'data'))
def diseases(active):
    labels = (active or {}).get('quality', {}).get('diseases', [])
    return labels, labels[0] if labels else None


@app.callback(Output('w-start', 'options'), Output('w-end', 'options'), Output('w-start', 'value'), Output('w-end', 'value'),
              Output('w-start-label', 'children'), Output('w-end-label', 'children'),
              Input('w-active', 'data'), Input('w-disease', 'value'), Input('w-aggregation', 'value'))
def history_options(active, disease, aggregation='Weekly'):
    try:
        periods = sorted({reporting_period(r, aggregation) for r in (active or {}).get('records', []) if r['disease'] == disease})
    except ValueError:
        periods = []
    unit = {'Weekly': 'week', 'Monthly': 'month', 'Quarterly': 'quarter'}[aggregation]
    return periods, periods, None, None, f'From reporting {unit}', f'To reporting {unit}'


@app.callback(Output('w-aggregation', 'options'), Output('w-history-guidance', 'children'), Output('w-aggregation', 'value'),
              Input('w-active', 'data'), Input('w-disease', 'value'), State('w-aggregation', 'value'))
def history_availability(active, disease, aggregation='Weekly'):
    rows = [r for r in (active or {}).get('records', []) if r['disease'] == disease]
    available = bool(rows)
    try:
        for row in rows:
            reporting_period(row, 'Monthly')
    except ValueError:
        available = False
    return ([{'label': label, 'value': label, 'disabled': label != 'Weekly' and not available}
             for label in ['Weekly', 'Monthly', 'Quarterly']],
            'Monthly and quarterly totals group whole weeks by their source week-start date; they do not split cases across months.' if available else
            'Monthly and quarterly views need source-established Week Start Date values. Add those dates and upload again. Weekly data remain available.',
            aggregation if available else 'Weekly')


@app.callback(Output('w-result', 'data'), Input('w-run', 'n_clicks'), Input('w-active', 'data'),
              Input('w-disease', 'value'), State('w-result', 'data'), prevent_initial_call=True,
              running=[(Output('w-run', 'disabled'), True, False), (Output('w-fitting', 'children'), 'Preparing your forecast…', '')])
def forecast(_clicks, active, disease, prior):
    if ctx.triggered_id != 'w-run' or not active or not active.get('records') or not disease:
        return None
    try:
        config = model_configuration()
        if prior and prior.get('cache_key') == cache_key(active, disease, config):
            return prior
        return run(active, disease, config)
    except Exception as exc:
        return {'dataset_id': active['id'], 'disease': disease, 'hybrid_status': 'Hybrid unavailable',
                'sarima_status': 'SARIMA-only unavailable', 'failure_reason': str(exc), 'metrics': {}}


def metrics_table(result, technical=False):
    rows = []
    for model, label in [('hybrid', 'Hybrid SARIMA–NNAR'), ('sarima', 'SARIMA-only')]:
        metrics = (result or {}).get('metrics', {}).get(model) or {}
        evaluation = (result or {}).get('evaluation', {})
        status = evaluation.get('status', 'Generate a forecast to evaluate the models.')
        if status == 'Retrospective evaluation':
            status = evaluation.get(model + '_status', 'Not available')
        rows.append({'Model': label, 'Evaluation status': status, **{key.upper(): round(metrics[key], 3) if metrics.get(key) is not None else 'Not available'
                                      for key in (['mae', 'rmse', 'mape', 'wape'] if technical else ['mae', 'wape'])}})
    return table(rows)


def horizon_metrics_table(result):
    rows = []
    for horizon, evidence in (result or {}).get('horizon_metrics', {}).items():
        for model, label in [('hybrid', 'Hybrid SARIMA–NNAR'), ('sarima', 'SARIMA-only')]:
            values = evidence['metrics'].get(model) or {}
            rows.append({'Weeks': f'1–{horizon}', 'Model': label, 'Scored weeks': evidence['scored_weeks'],
                         'Missing actuals excluded': evidence['excluded_missing_actuals'],
                         **{key.upper(): round(values[key], 3) if values.get(key) is not None else 'Not available'
                            for key in ['mae', 'rmse', 'mape', 'wape']}})
    return table(rows) if rows else html.P('Horizon-specific evaluation is not available yet.')


def warning_summary(messages):
    if not messages:
        return []
    return [disclosure(f"{len(messages)} data {'notice' if len(messages) == 1 else 'notices'} to review",
                       [html.P(message) for message in messages])]


@app.callback(Output('w-page-title', 'children'), Output('w-disease-toolbar', 'style'),
              Input('w-page', 'value'), Input('w-active', 'data'))
def page_toolbar(page, active):
    return page, {} if active and active.get('records') and page != 'About the Model' else {'display': 'none'}


def about_model():
    return [html.H3('How the forecast works'),
            html.P('The system learns from weekly case reports. SARIMA describes patterns and changes over time. A neural network autoregression model (NNAR) learns patterns in the errors SARIMA leaves behind. Adding that correction produces the Hybrid SARIMA–NNAR forecast.'),
            html.P('The Hybrid is the main projection. SARIMA-only is shown separately for comparison; it never replaces an unavailable Hybrid forecast.'),
            html.H3('Performance measures'), html.Ul([
                html.Li('MAE: the average forecast error in number of cases. Lower values mean closer forecasts.'),
                html.Li('WAPE: total absolute error as a percentage of reported cases. It is undefined when the total reported count is zero.'),
                html.Li('RMSE: an error measure that gives more weight to large misses.'),
                html.Li('MAPE: average percentage error for weeks with nonzero reported counts. Zero-case weeks are excluded from this percentage, but remain in the data and other measures.')]),
            html.H3('Limitations'), html.P('Forecasts are projections, not outbreak declarations. Recent reports may be incomplete, and missing weeks can affect performance. Weekly model settings and the final evaluation protocol remain subject to adviser approval where applicable.'),
            html.P('The shaded forecast uncertainty range is provisional. It does not carry a formally validated coverage guarantee. Evaluation results from historical records are retrospective; a future prospective study has not yet been completed.')]


@app.callback(Output('w-content', 'children'), Output('w-context', 'children'), Output('w-forecast-controls', 'style'),
              Output('w-history-controls', 'style'), Output('w-data-controls', 'style'), Output('w-technical-controls', 'style'),
              Output('w-advanced', 'children'), Input('w-page', 'value'), Input('w-active', 'data'), Input('w-disease', 'value'),
              Input('w-result', 'data'), Input('w-horizon', 'value'), Input('w-aggregation', 'value'), Input('w-start', 'value'), Input('w-end', 'value'))
def render(page, active, disease, result, horizon, aggregation, start=None, end=None):
    if active and disease not in active.get('quality', {}).get('diseases', []):
        disease = next(iter(active.get('quality', {}).get('diseases', [])), None)
    if result and (not active or result.get('dataset_id') != active.get('id') or result.get('disease') != disease):
        result = None
    styles = [({} if page == p else {'display': 'none'}) for p in ['Forecast', 'Historical Trends', 'Data', 'About the Model']]
    technical = [html.P('Model settings are maintained by the study administrator. Unapproved settings produce exploratory results only.'),
                 html.P((result or {}).get('configuration_label') or installed_protocol_label()),
                 disclosure('Horizon-specific retrospective evaluation', horizon_metrics_table(result)),
                 metrics_table(result, True), disclosure('Model status, configuration and diagnostics', advanced(result or {'status': 'No forecast generated; installed protocol may still be pending.'})),
                 html.P('Provisional range: Hybrid ± training SARIMA residual RMSE, clipped at zero. MAPE uses nonzero actuals (coverage is recorded); WAPE is undefined for zero total actuals. Missing actuals are excluded using the same holdout positions for both models.')]
    if page == 'About the Model':
        if active and active.get('records'):
            technical.append(disclosure('Source information and eligibility evidence', advanced({'metadata': active['metadata'], 'quality': active['quality'], 'eligibility_reasons': active['eligibility_reasons']})))
        return about_model(), (active or {}).get('context', ''), *styles, technical
    if not active or not active.get('records'):
        return [html.H2('Your weekly outlook starts with your data'), html.P('Open Data to upload weekly records, review the changes, and confirm the dataset you want to use.'),
                notice('No dataset is currently in use.')], '', *styles, technical
    if result and (result.get('dataset_id') != active['id'] or result.get('disease') != disease):
        result = None
    meta, q = active['metadata'], active['quality']
    rows = [r for r in active['records'] if r['disease'] == disease]
    complete = [r for r in rows if r['case_count'] is not None and str(r.get('reporting_status') or meta.get('reporting_status', '')).lower() == 'complete']
    latest = f"{complete[-1]['year']} · Week {complete[-1]['morbidity_week']}" if complete else 'Not established'
    messages = quality_messages(active)
    banner = 'Synthetic / Demo Data — not actual surveillance' if meta.get('dataset_type') == 'synthetic' else active['context']
    content = []
    if page == 'Overview':
        path = (result or {}).get('hybrid') or []
        direction = 'Not available yet' if not path else ('Projected to rise' if path[min(horizon, len(path)) - 1] > path[0] else 'Projected to fall' if path[min(horizon, len(path)) - 1] < path[0] else 'Relatively stable')
        overview_figure = forecast_chart(active, disease, result, horizon)
        overview_figure.update_layout(height=340, margin={'l': 40, 'r': 15, 't': 20, 'b': 85})
        overview_figure.update_xaxes(nticks=6, tickangle=0)
        content += [
            html.Div([html.Span('Active Dataset', className='card-label'), html.Strong(meta.get('source_file') or 'Not specified'),
                      html.Span(f"{len(q['diseases'])} included {'disease' if len(q['diseases']) == 1 else 'diseases'}", className='muted')], className='dataset-strip'),
            cards({'Weekly Observations': len(rows),
                   'Latest Supplied Week': f"{rows[-1]['year']} / Week {rows[-1]['morbidity_week']}" if rows else 'None',
                   'Latest Complete Week': latest, 'Forecast Direction': direction}),
            html.Div([
                html.Div([html.H3('Weekly trend'), html.P(disease or 'Select a disease', className='muted'),
                          dcc.Graph(figure=overview_figure, config={'displaylogo': False, 'displayModeBar': False}),
                          html.P(interpretation(result, horizon) if path else 'Reported history only. Open Forecast to generate a projection.')], className='dashboard-panel'),
                html.Aside([html.H3('Data status'),
                            html.P('Review recommended' if messages else 'Checks complete', className='status-label'),
                            *warning_summary(messages), eligibility(active),
                            html.H4('Source freshness'), html.P('Source date: ' + str(meta.get('source_date') or 'Not specified')),
                            html.P('Uploaded: ' + str(meta.get('uploaded_at') or 'Not specified'))], className='dashboard-panel')
            ], className='overview-columns')]
    elif page == 'Forecast':
        if not result:
            content.append(notice('Choose Generate Forecast to prepare the weekly outlook.'))
        elif not result.get('hybrid'):
            content.append(notice('Hybrid forecast is currently unavailable for this dataset.'))
            if result.get('sarima'):
                content.append(html.P('SARIMA-only results are shown separately below.'))
            else:
                content.append(html.P('The data or study settings may need review. See About the Model for more information.'))
        else:
            content.append(html.P(interpretation(result, horizon)))
        content += [html.P((result or {}).get('context', active['context'])),
                    html.P((result or {}).get('configuration_label') or installed_protocol_label()),
                    html.P(f'Displaying next {horizon} forecast weeks. The first weeks remain the same across display ranges; historical evaluation uses a separate fixed holdout.' if (result or {}).get('hybrid') or (result or {}).get('sarima') else 'No future forecast is available yet. The chart below shows historical reports only; changing the horizon cannot change those reports.'),
                    *([notice(friendly_reason(result['failure_reason']))] if result and result.get('failure_reason') else []),
                    dcc.Graph(figure=forecast_chart(active, disease, result, horizon), config={'displaylogo': False}), metrics_table(result),
                    html.P('Complete reports and incomplete/unknown reports are separate groups on the chart. Incomplete/unknown reports are retained for inspection but excluded from model training.'),
                    html.P('MAE shows average error in cases. WAPE shows total error as a percentage of reported cases. Historical performance is retrospective.'),
                    *warning_summary(messages)]
    elif page == 'Historical Trends':
        try:
            if start and end and start > end:
                raise ValueError('Choose an end week on or after the start week.')
            within = lambda r: (not start or reporting_period(r, aggregation) >= start) and (not end or reporting_period(r, aggregation) <= end)
            filtered = {**active, 'records': [r for r in rows if within(r)],
                        'quality': {**q, 'missing_weeks': [r for r in q['missing_weeks'] if aggregation != 'Weekly' or within(r)],
                                    'excluded_from_training': [r for r in q['excluded_from_training'] if aggregation != 'Weekly' or within(r)]}}
            if aggregation == 'Weekly':
                figure = forecast_chart(filtered, disease, None, horizon)
            else:
                x, y, explanation = historical_summary(filtered, disease, aggregation)
                figure = go.Figure(go.Bar(x=x, y=y)).update_layout(template='plotly_white', yaxis_title='Reported cases', xaxis_title=aggregation + ' reporting period')
                content.append(html.P(explanation))
            content += [html.P('Weekly observations' if aggregation == 'Weekly' else f'{aggregation} summary · Weekly records remain unchanged.'), dcc.Graph(figure=figure, config={'displaylogo': False})]
        except ValueError as exc:
            content.append(notice(str(exc)))
        content += [html.P('Changing this view does not change the weekly forecast.'), *warning_summary(messages)]
    elif page == 'Data':
        content = [html.H2('Current Dataset'), html.H3(meta.get('source_file') or 'Not specified'), cards(facts(active)), eligibility(active),
                   disclosure('View Data Summary', [html.P(f"{q['observation_count']} weekly observations · {len(q['diseases'])} diseases · {q['year_coverage'][0]}–{q['year_coverage'][1]}"),
                       *[notice(w) for w in messages], *quality_details(active), table(active['records'], LABELS, limit=100)]),
                   disclosure('View Source Details', [html.P('Source reference: ' + str(meta.get('provenance') or 'Not specified')),
                       html.P('Uploaded: ' + str(meta.get('uploaded_at') or 'Not specified')),
                       table([{'Step': {'validated': 'Checked', 'confirmed': 'Reviewed', 'prepared': 'Prepared'}.get(r['event'], r['event'].title()), 'Date': r['at']} for r in active['audit']])])]
    technical += [disclosure('Source information and eligibility evidence', advanced({'metadata': meta, 'quality': q, 'eligibility_reasons': active['eligibility_reasons']}))]
    return content, banner, *styles, technical


@app.callback(Output('w-download', 'data'), Input('w-export', 'n_clicks'), Input('w-export-json', 'n_clicks'),
              State('w-active', 'data'), State('w-result', 'data'), prevent_initial_call=True)
def export(_csv, _json, active, result):
    if not active or not active.get('records'):
        return no_update
    if result and result.get('dataset_id') != active['id']:
        result = None
    if ctx.triggered_id == 'w-export-json':
        return dcc.send_string(json.dumps({'dataset': active, 'forecast': result}, indent=2, ensure_ascii=False), 'weekly-evidence.json')
    return dcc.send_data_frame(export_frame(active, result).to_csv, 'weekly-forecast.csv', index=False)


@app.callback(Output('w-snapshot-status', 'children'), Input('w-snapshot', 'n_clicks'), Input('w-reconcile', 'n_clicks'),
              State('w-active', 'data'), State('w-result', 'data'), State('w-snapshot-id', 'value'), prevent_initial_call=True)
def prospective(_issue, _reconcile, active, result, identifier):
    try:
        if not active or not active.get('records'):
            raise ValueError('Choose a dataset first.')
        if ctx.triggered_id == 'w-snapshot':
            return notice('Forecast saved. Reference: ' + save_snapshot(active, result or {}))
        return advanced(reconcile(identifier, active))
    except Exception as exc:
        return notice(str(exc))
