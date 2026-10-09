"""Guided source upload, transformation review and weekly forecasting."""
import json

import plotly.graph_objects as go
from dash import ALL, Input, Output, State, ctx, dcc, html, no_update

from dashboard.app_instance import app
from dashboard.weekly.charts import forecast_chart
from dashboard.weekly.result_schema import current_result
from dashboard.weekly.data import activate, demo, now
from dashboard.weekly.model import cache_key, interpretation, run
from dashboard.weekly.outputs import export_frame, historical_summary, reconcile, save_snapshot, reporting_period
from dashboard.weekly.presentation import (cards, disclosure, eligibility, facts, friendly_reason, notice,
                                           quality_details, quality_messages, table, display_timestamp, source_freshness)
from dashboard.weekly.settings import model_configuration, research_requirements
from dashboard.weekly.transform import LABELS, plausible_columns, prepare, read_source, update_facts

PAGES = ['Overview', 'Forecast', 'Historical Trends', 'Data', 'About the Model']
NAV_LABELS = dict(zip(PAGES, ['Overview', 'Forecast', 'Trends', 'Data', 'About']))
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


FACT_GUIDANCE = {
    'provenance': ('Identify the original file or report and who supplied it. This records where the data came from; it does not certify completeness.',
                   'File/report title; provider; date; worksheet/page'),
    'reporting_reference': ('Required only when selecting Historical reporting period complete. Cite an actual report, email, or written confirmation from CESU (City Epidemiology and Surveillance Unit) or your data provider stating that reporting is complete for the covered period. If unavailable, leave Reporting Status as Not specified or May still be incomplete.',
                            'Report/email title; issuer; date; covered period; page/section'),
    'calendar_reference': ('Required only when choosing 52 or 53 reporting weeks below. Cite the source reporting calendar and the years it covers. Week 53 in a file alone does not establish the length of every year. Leave year lengths unspecified if no calendar is available.',
                           'Reporting calendar title; issuer; years covered; page/link'),
}


def advanced(value):
    return html.Pre(json.dumps(current_result(value), indent=2, ensure_ascii=False), className='technical-readout')


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
            html.Div([html.Div([html.Span(), html.Span(), html.Span()], className='brand-symbol', **{'aria-hidden': 'true'}),
                      html.Div([html.H1('Antipolo Disease Forecasting'),
                                html.P('Weekly surveillance and school preparedness', className='subtitle')])], className='brand-identity'),
            html.Span('No dataset loaded', id='w-dataset-badge', className='dataset-badge', role='status'),
        ]),
        html.Nav(dcc.Tabs(id='w-page', value='Overview', className='nav-tabs', children=[
            dcc.Tab(label=NAV_LABELS[p], value=p, className='nav-tab nav-' + str(i), selected_className='nav-tab-selected')
            for i, p in enumerate(PAGES)]), className='primary-navigation', **{'aria-label': 'Main navigation'}),
        html.Div(id='w-navigation-progress', className='action-progress navigation-progress',
                 role='status', **{'aria-live': 'polite', 'aria-atomic': 'true'}),
        html.Div([html.Div([html.H2(id='w-page-title'), html.Div(id='w-context', className='context-line')]),
                  html.Div([html.Label('Selected disease', htmlFor='w-disease'), dcc.Dropdown(closeOnSelect=True, id='w-disease', clearable=False)],
                           id='w-disease-toolbar', className='disease-picker')], className='page-toolbar'),
        *[html.Div(id=identity, className='action-progress', role='status', **{'aria-live': 'polite'})
          for identity in ('w-data-progress', 'w-edit-progress', 'w-export-progress', 'w-snapshot-progress')],
        html.Div(id='w-flow-message', **{'aria-live': 'polite'}),
        html.Section(id='w-data-controls', style={'display': 'none'}, children=[
            html.Div([html.H3('Upload Data', className='module-section-title'), html.P('Upload your weekly disease records. The system will prepare the file automatically and show you what changed before using it.')]),
            dcc.Upload(id='w-upload', children=html.Div([html.Strong('Choose a file or drop it here'), html.P('CSV or Excel workbook · Up to 10 MB')]),
                       multiple=False, className='upload-zone', accept='.csv,.xlsx'),
            html.Div(id='w-upload-status', **{'aria-live': 'polite'}),
            html.Div(id='w-upload-progress', className='action-progress', role='status', **{'aria-live': 'polite'}),
            html.Div([html.Button('View Transformation Details', id='w-reopen', n_clicks=0, className='secondary'),
                      html.Button('Update Source Information', id='w-edit-facts', n_clicks=0),
                      html.Button('Reset Dataset', id='w-reset', n_clicks=0, className='quiet'),
                      html.Button('Try Synthetic / Demo Data', id='w-demo', n_clicks=0, className='quiet')], className='actions'),
            html.P('To replace your dataset, choose another file above. Your current data stay in use until you confirm the replacement.', className='muted'),
        ]),
        html.Section(id='w-forecast-controls', style={'display': 'none'}, children=[
            html.Label('How far ahead would you like to look?', htmlFor='w-horizon'),
            dcc.RadioItems(id='w-horizon', options=[{'label': f'Next {n} weeks', 'value': n} for n in (4, 13, 26, 52)], value=13, inline=True, className='choice-row'),
            html.P('Choose how far ahead you want to view the forecast. The underlying model is not retrained when you change the display range.', className='muted'),
            html.Div([html.Button('Generate Forecast', id='w-run', n_clicks=0), html.Button('Download Results', id='w-export', n_clicks=0, className='secondary')], className='actions'),
            html.Div(id='w-fitting', className='action-progress', role='status', **{'aria-live': 'polite'}),
        ]),
        html.Section(id='w-history-controls', style={'display': 'none'}, children=[
            html.Label('View frequency'), dcc.RadioItems(id='w-aggregation', options=['Weekly', 'Monthly', 'Quarterly'], value='Weekly', inline=True, className='choice-row'),
            html.Div([html.Div([html.Label('From reporting week', id='w-start-label'), dcc.Dropdown(closeOnSelect=True, id='w-start', placeholder='First available period')]),
                      html.Div([html.Label('To reporting week', id='w-end-label'), dcc.Dropdown(closeOnSelect=True, id='w-end', placeholder='Latest available period')])], className='two-column'),
            html.P(id='w-history-guidance', className='muted'),
        ]),
        dcc.Loading(html.Main(id='w-content'), type='circle', delay_show=250,
                    overlay_style={'visibility': 'visible', 'backgroundColor': 'rgba(255,255,255,0.65)'},
                    custom_spinner=html.Div('Updating view...', className='action-progress view-progress', role='status')),
        html.Section(id='w-technical-controls', style={'display': 'none'}, children=[
            disclosure('Advanced Details', [html.Div(id='w-advanced'),
                html.Button('Download Detailed Evidence', id='w-export-json', n_clicks=0, className='secondary'),
                disclosure('Future prospective validation', [html.P('Not yet completed. Save a forecast before outcomes are known, then compare it with later reports. Each comparison is retained separately.'),
                    html.Button('Save Forecast Record', id='w-snapshot', n_clicks=0, className='secondary'),
                    html.Label('Saved forecast reference'), dcc.Input(id='w-snapshot-id', placeholder='Reference from a saved forecast', type='text'),
                    html.Button('Compare with Current Reports', id='w-reconcile', n_clicks=0, className='secondary'), html.Div(id='w-snapshot-status')])]),
        ]),
        html.Div(id='w-modal', className='modal-backdrop', style={'display': 'none'}, children=[
            html.Div(id='w-applying', className='applying-overlay', hidden=True, role='status',
                     **{'aria-live': 'polite'}, children=[
                         html.Div([html.Strong('Applying your dataset...'),
                                   html.P('Please wait while we check your changes and update Overview.')],
                                  className='applying-panel action-progress')]),
            html.Div(className='review-dialog', role='dialog', **{'aria-modal': 'true', 'aria-labelledby': 'w-modal-title'}, children=[
                html.P('REVIEW BEFORE USING', className='eyebrow'), html.H2('Review Data Transformation', id='w-modal-title', tabIndex=-1),
                html.P('Review the worksheets, add source information where needed, then confirm at the bottom. Your active dataset stays unchanged until confirmation.', className='review-intro'),
                html.Div(id='w-review-sticky', className='review-sticky', **{'aria-label': 'Review reminders'}),
                html.Div(id='w-review'), html.Div(id='w-mapping'),
                html.Button('Apply Worksheet Changes', id='w-apply-mapping', n_clicks=0, className='secondary', style={'display': 'none'},
                            title='Update the prepared preview after changing a field mapping. This does not activate the dataset.'),
                html.Section(id='w-fact-panel', className='review-source-section', style={'display': 'none'}, children=[
                    html.H3('2. Source information', className='review-step'),
                    html.P('Add only source-supported information. The indicators below show which evidence is needed for your selections. Unknown facts can remain unspecified; confirming a dataset does not establish forecasting or research eligibility.'),
                    html.Div([html.H4('Source evidence checklist'),
                              html.P(id='w-reporting-requirement', role='status'),
                              html.P(id='w-calendar-requirement', role='status')], className='source-requirements'),
                    html.Div(id='w-facts'),
                    html.Button('Apply Source Information', id='w-apply-facts', n_clicks=0, className='secondary'),
                    html.P('Updates the review below. Your active dataset is not changed yet.', className='muted')]),
                html.Details(id='w-review-extra', children=[html.Summary('3. Data checks and research eligibility', className='review-step'),
                    html.P('Read-only findings and supporting details. These are not another confirmation step.', className='review-detail-note'),
                    dcc.Loading(html.Div(id='w-review-extra-content'), type='circle', delay_show=200)]),
                html.Fieldset(id='w-review-actions', className='modal-actions', children=[
                    html.Div([html.Strong('Final step: use this dataset'),
                              html.P('Confirm & Use Data applies the reviewed data and opens Overview. Cancel keeps your current dataset.', className='muted')], className='review-final-copy'),
                    html.Div(id='w-review-progress', className='action-progress', role='status', **{'aria-live': 'polite'}),
                    html.Div(id='w-review-message', **{'aria-live': 'assertive'}),
                    html.Button('Confirm & Use Data', id='w-activate', n_clicks=0, disabled=True),
                    html.Button('Cancel', id='w-cancel', n_clicks=0, className='secondary'),
                    html.Button('Close', id='w-close', n_clicks=0, className='secondary', style={'display': 'none'})]),
            ])]),
        html.Footer('Research focus: ages 5–19 · Confirmed cases · CESU/PIDSAR. Projections support preparedness and should be read alongside current surveillance reports.'),
    ])


@app.callback(Output('w-source', 'data'), Output('w-upload-status', 'children'), Input('w-upload', 'contents'),
              State('w-upload', 'filename'), prevent_initial_call=True,
              running=[(Output('w-upload-progress', 'children'), 'Reading your file...', ''), (Output('w-upload', 'disabled'), True, False)])
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
              Input('w-edit-facts', 'n_clicks'), State('w-active', 'data'), prevent_initial_call=True,
              running=[(Output('w-edit-progress', 'children'), 'Opening source information...', ''),
                       (Output('w-edit-facts', 'disabled'), True, False)])
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
              running=[(Output('w-data-progress', 'children'), 'Preparing and checking your data...', ''),
                       (Output('w-review-progress', 'children'), 'Checking and applying your changes…', ''),
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
            dcc.Dropdown(closeOnSelect=True, id={'type': 'w-map', 'sheet': index, 'field': field}, options=column_options(sheet, field, fixed),
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


app.clientside_callback(
    """function(values, pending, ids) {
        const meta = (pending || {}).metadata || {};
        const facts = {...meta};
        const lengths = {...(meta.year_lengths || {})};
        (ids || []).forEach((id, i) => {
            const value = (values || [])[i];
            if (id.field.startsWith('calendar:')) {
                if (value) lengths[id.field.split(':')[1]] = value;
            } else if (value !== undefined && value !== null) facts[id.field] = value;
        });
        const supplied = value => String(value || '').trim().length > 0;
        const complete = facts.reporting_status === 'complete';
        const ref = supplied(facts.reporting_reference);
        let reporting = complete
            ? (ref ? 'Completeness evidence entered — will be checked when you apply or confirm.'
                   : 'Required now: enter CESU/source evidence for historical completeness because you selected Historical reporting period complete.')
            : 'To establish historical completeness: choose Historical reporting period complete only when documented, and enter CESU/source evidence for historical completeness. Otherwise leave the status unspecified or incomplete.';
        const years = [...new Set(((pending || {}).records || []).map(row => Number(row.year)))].sort((a,b) => a-b);
        const missing = years.filter(year => !lengths[String(year)]);
        const declared = Object.values(lengths).some(value => value === 52 || value === 53);
        let calendar = declared && !supplied(facts.calendar_reference)
            ? 'Required now: enter CESU/source evidence for reporting-year lengths for the 52/53-week calendar you declared.'
            : (missing.length ? 'Calendar still needed for historical years: ' + missing.join(', ') + '. Open Reporting calendar below and enter only source-supported year lengths and their evidence.'
                              : 'Historical year lengths entered. Calendar evidence and consistency are checked when you apply or confirm.');
        if (years.length && !lengths[String(years[years.length-1] + 1)])
            calendar += ' The following year also needs a calendar to label future weeks across that boundary.';
        return [reporting, 'requirement-status ' + (complete && ref ? 'evidence-entered' : 'evidence-needed'),
                calendar, 'requirement-status ' + (!missing.length && declared && supplied(facts.calendar_reference) ? 'evidence-entered' : 'evidence-needed')];
    }""",
    Output('w-reporting-requirement', 'children'), Output('w-reporting-requirement', 'className'),
    Output('w-calendar-requirement', 'children'), Output('w-calendar-requirement', 'className'),
    Input({'type': 'w-fact', 'field': ALL}, 'value'), Input('w-pending', 'data'),
    State({'type': 'w-fact', 'field': ALL}, 'id'),
)


def fact_fields(dataset):
    controls = []
    meta = dataset['metadata']
    for field, label in FACT_LABELS.items():
        if meta.get(field) not in (None, '', 'unknown'):
            controls.append(html.P([html.Strong(label + ': '), str(meta[field])]))
            continue
        identity = {'type': 'w-fact', 'field': field}
        if field in FACT_OPTIONS:
            control = dcc.Dropdown(closeOnSelect=True, id=identity, options=[{'label': 'Not specified', 'value': ''}] +
                                  [{'label': label, 'value': value} for label, value in FACT_OPTIONS[field]], value='', clearable=False)
        else:
            control = dcc.Input(id=identity, type='text', placeholder=FACT_GUIDANCE.get(field, ('', 'Not specified'))[1], value='')
        requirement = {'reporting_status': 'For training completeness',
                       'reporting_reference': 'Required if reporting is complete',
                       'calendar_reference': 'Required when declaring a calendar'}.get(field)
        controls.append(html.Div([html.Label([label, *([html.Span(requirement, className='evidence-indicator')] if requirement else [])]), control,
            *([html.Small(FACT_GUIDANCE[field][0], id='guidance-' + field, className='field-guidance')] if field in FACT_GUIDANCE else [])], className='form-field'))
    years = sorted({r['year'] for r in dataset['records']})
    if years:
        calendar = [html.P('Only choose a year length if the source reporting calendar establishes it. This is needed to place weeks across year boundaries; it does not change source week 53 records.')]
        for year in years + [years[-1] + 1]:
            if str(year) in meta.get('year_lengths', {}):
                calendar.append(html.P(f"{year}: {meta['year_lengths'][str(year)]} reporting weeks"))
            else:
                calendar.append(html.Div([html.Label([f'{year} reporting calendar', html.Span('Source calendar needed', className='evidence-indicator')]),
                    dcc.Dropdown(closeOnSelect=True, id={'type': 'w-fact', 'field': f'calendar:{year}'}, options=[
                        {'label': 'Not specified', 'value': ''}, {'label': '52 reporting weeks', 'value': 52},
                        {'label': '53 reporting weeks', 'value': 53}], value='', clearable=False)], className='form-field'))
        controls.append(disclosure('Reporting calendar — needed across year boundaries', calendar))
    blanks = []
    for index, row in enumerate(dataset['records']):
        if row['case_count'] is not None:
            continue
        blanks.append(html.Div([
            html.Label(f"{row['disease']} · {row['year']} · Week {row['morbidity_week']}"),
            dcc.Dropdown(closeOnSelect=True, id={'type': 'w-fact', 'field': f'resolution:{index}'}, value='', clearable=False,
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


def preparation_note(text):
    # Older session datasets can retain the previous directional wording.
    return text.replace('Review the excluded rows below before confirming.',
                        'Open "Review automatically excluded rows" in this worksheet\'s "Review and adjust" section before confirming.')


def worksheet_cards(dataset, editable=False):
    history = dataset['transformation']
    source = history['source']
    units = {u['index']: u for u in dataset.get('worksheet_units', [])}
    children = []
    for i, (sheet, report) in enumerate(zip(source['sheets'], history['sheets'])):
        after = [r for r in dataset.get('records', []) if r.get('source_worksheet') == sheet['worksheet']]
        unit = units.get(i, {'included': report.get('included', True), 'records': after, 'errors': [], 'status': 'ready'})
        included = unit['included']
        body = [html.Div([
            html.Div([html.P(f'Worksheet {i + 1} of {len(source["sheets"])}', className='worksheet-kicker'),
                      html.H3(f'Reviewing worksheet: {sheet["name"]}.')]),
            html.Span('Status: ' + unit['status'].replace('_', ' '), className='worksheet-status-badge'),
        ], className='worksheet-header')]
        if editable:
            body.append(dcc.RadioItems(id={'type': 'w-include', 'sheet': i},
                        options=[{'label': html.Span([html.Strong('Include'), html.Small('Use this worksheet')]), 'value': 'include'},
                                 {'label': html.Span([html.Strong('Exclude'), html.Small('Leave out of this dataset')]), 'value': 'exclude'}],
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
                html.Div([html.Div([html.Span('SOURCE', className='preview-tag'), html.H4('Original Uploaded Data'),
                                    html.P('As supplied in your file.')], className='preview-heading'),
                          cards({'Source rows': sheet['original_row_count']}),
                          html.P(f"{source['filename']} · Header on row {sheet['header_row']}", className='preview-caption'),
                          table(sheet['rows'], {c: c for c in sheet['columns']}, limit=8)], className='source-preview'),
                html.Div([html.Div([html.Span('PREPARED', className='preview-tag'), html.H4('Prepared Weekly Data'),
                                    html.P('Restructured for weekly analysis. Review before using.')], className='preview-heading'),
                          cards({"Weekly observations": len(unit["records"])}),
                          html.P('Preview of the first 8 observations, where available.', className='preview-caption'),
                          table(unit['records'], LABELS, limit=8) if unit['records'] else html.P('Resolve the highlighted fields or source values to prepare this worksheet.')], className='prepared-preview'),
            ], className='before-after'))
            detected = [html.H4('How your worksheet was interpreted')]
            if sheet['kind'] == 'week_by_year':
                detected += [html.P('Week × year table recognized.', className='detection-lead'),
                             html.P('Reporting years and case counts are read automatically from the year columns.'),
                             html.P('Year columns detected', className='detection-label'),
                             html.Ul([html.Li(str(year)) for year in sheet['year_columns']], className='year-chips',
                                     **{'aria-label': 'Year columns detected'})]
            else:
                detected.append(html.P('Row table recognized. Review the identified fields below.'))
            mapping = {**sheet['mapping'], **(report.get('mapping') or {})}
            mapped_fields = []
            for field, value in mapping.items():
                if field in LABELS and field not in sheet['unresolved']:
                    shown = f"worksheet name: {sheet['worksheet']}" if value == '__worksheet__' else value
                    mapped_fields.append(html.Div([html.Dt(LABELS[field]), html.Dd([
                        html.Span('Identified from ', className='mapping-prefix'), html.Strong(str(shown))])], className='mapping-item'))
            if mapped_fields:
                detected.append(html.Dl(mapped_fields, className='detected-mappings'))
            body.append(html.Div(detected, className='detection-summary'))
            review_actions = []
            if editable and unit['status'] == 'needs_mapping':
                body.extend(mapping_fields(sheet, i, dataset.get('worksheet_choices', {}).get(str(i), {})))
            elif editable and mapping.get('disease') == '__worksheet__':
                review_actions.append(disclosure('Change inferred Disease', [
                    dcc.Dropdown(closeOnSelect=True, id={'type': 'w-map', 'sheet': i, 'field': 'disease'},
                                 options=column_options(sheet, 'disease'), value='__worksheet__', clearable=False),
                    html.Label('Disease value (only if entering a value)'),
                    dcc.Input(id={'type': 'w-enter', 'sheet': i, 'field': 'disease'}, type='text'),
                    html.P('Choose Apply Worksheet Changes to update the preview before confirming.')]))
            excluded_rows = report.get('excluded_rows', [])
            if excluded_rows:
                originals = {sheet['header_row'] + j + 1: row for j, row in enumerate(sheet['rows'])}
                excluded_preview = [{'Worksheet row': r['row'], 'Reason': r['reason'],
                                     'Original values': json.dumps(originals.get(r['row'], {}), ensure_ascii=False)} for r in excluded_rows]
                review_actions.append(disclosure('Review automatically excluded rows', [
                    html.P(f'{len(excluded_rows)} source rows were excluded. Check the reasons and original values below.'),
                    table(excluded_preview, {k: k for k in excluded_preview[0]}, limit=len(excluded_preview))]))
            if review_actions:
                body.append(html.Div([html.H4('Review and adjust'), *review_actions], className='worksheet-review-actions'))
            if report['changes']:
                body.append(html.Div([html.H4('What changed?'), html.Ul([html.Li(c) for c in report['changes']])],
                                     className='transformation-changes'))
            body += [notice(preparation_note(w)) for w in report['warnings']]
        children.append(html.Section(body, id=f'w-worksheet-{i}', className='worksheet-card' + ('' if included else ' worksheet-excluded'),
                                     **{'data-worksheet-index': str(i)}))
    return children


def review_overview(dataset, editable=False):
    sheets = (dataset.get('transformation') or {}).get('sheets', [])
    included = [(i, sheet) for i, sheet in enumerate(sheets) if sheet.get('included', True)]
    excluded = [(i, sheet) for i, sheet in enumerate(sheets) if not sheet.get('included', True)]
    warnings = [] if dataset.get('review_only') else quality_messages(dataset)
    needs_fields = dataset.get('review_only', False)
    def sheet_list(items):
        return html.Ul([html.Li(html.A(sheet['worksheet'], href=f'#w-worksheet-{i}',
                                      **{'data-review-target': f'w-worksheet-{i}'})) for i, sheet in items], className='sheet-inventory') if items else html.P('None', className='muted')
    return html.Div([
        html.H3('Review overview'),
        html.P('Check the overall findings first, then review each section before confirming.'),
        *([html.Div([
            html.Div([html.H4(f'Included ({len(included)})'), sheet_list(included)], className='included-sheets'),
            html.Div([html.H4(f'Excluded ({len(excluded)})'), sheet_list(excluded)], className='excluded-sheets'),
        ], className='worksheet-inventory'), html.P(f'{len(included)} included worksheet(s). Only included worksheets will be used when you confirm.')]
          if sheets else [html.P('Worksheet inclusion details are not available for this dataset.')]),
        html.P('No missing values were converted to zero.', className='integrity-note'),
        *([html.Div([html.Strong(f'{len(warnings)} items to review'), html.Ul([html.Li(w) for w in warnings])],
                    className='review-findings')] if warnings else
          [html.P('Resolve required worksheet fields or exclude those worksheets before using this file.' if needs_fields
                  else 'No data notices were found in the current checks.')]),
        html.Nav([
            html.A('1. Worksheets and preparation', href='#w-step-worksheets', **{'data-review-target': 'w-step-worksheets'}),
            *([html.A('2. Source information', href='#w-fact-panel', **{'data-review-target': 'w-fact-panel'})] if editable and not needs_fields else []),
            html.A('3. Data checks and research eligibility', href='#w-review-extra', **{'data-review-target': 'w-review-extra'}),
        ], className='review-section-nav', **{'aria-label': 'Review sections'}),
    ], className='review-overview', id='w-review-overview', tabIndex=-1)


def transformation_review(dataset, editable=False):
    history = dataset.get('transformation')
    children = [review_overview(dataset, editable), html.H3('1. Worksheets and preparation', className='review-step', id='w-step-worksheets', tabIndex=-1)]
    if history:
        decisions = dataset.get('metadata', {}).get('blank_resolutions', {})
        if decisions:
            children.append(disclosure('Source-supported blank-count decisions', table([
                {'Disease': d['original']['disease'], 'Year': d['original']['year'], 'Week': d['original']['morbidity_week'],
                 'Decision': d['resolution'], 'Revised count': d['value'], 'Source evidence': d['reference']}
                for d in decisions.values()])))
        problems = [error for unit in dataset.get('worksheet_units', []) if unit['included'] for error in unit['errors']]
        fixes = [f"Worksheet “{report['worksheet']}”: {preparation_note(warning)}" for report in history['sheets']
                 for warning in report['warnings'] if warning.startswith('Automatic fix:')]
        if problems:
            children.append(html.Div([html.Strong('Action needed before confirmation'),
                                      html.Ul([html.Li(error) for error in problems])], className='worksheet-error', role='alert'))
        if fixes:
            children.append(html.Div([html.Strong('Automatic fixes applied — review before confirming'),
                                      html.Ul([html.Li(fix) for fix in fixes])], className='worksheet-suggestion', role='alert'))
        children += worksheet_cards(dataset, editable)
    else:
        explanation = ('Synthetic / Demo Data — generated for demonstration, not actual surveillance.'
                       if dataset['metadata'].get('dataset_type') == 'synthetic'
                       else 'The original transformation preview is not available for this dataset. Preserved weekly records are shown below.')
        children += [notice(explanation),
                     html.H3('Prepared Weekly Data'), table(dataset['records'], LABELS, limit=8)]
    if dataset.get('review_only'):
        children.append(notice('Resolve the highlighted fields on included worksheets, or exclude those worksheets. Include at least one worksheet with weekly records.'))
        return children
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


@app.callback(Output('w-review-extra-content', 'children'), Output('w-review-sticky', 'children'), Input('w-pending', 'data'),
              Input('w-modal-open', 'data'), State('w-active', 'data'))
def prepare_review_checks(pending, opened, active):
    # Prepare once per dataset/review change. Opening the section is browser-local,
    # with no repeated dataset upload or server round trip.
    dataset = pending or active
    sticky = []
    if opened and dataset:
        count = 0 if dataset.get('review_only') else len(quality_messages(dataset))
        fixes = sum(len(s.get('warnings', [])) for s in (dataset.get('transformation') or {}).get('sheets', []))
        sticky = [html.Span('⚠', className='reminder-icon', **{'aria-hidden': 'true'}), html.Strong('Review reminders'),
                  html.Span('Worksheet fields need attention' if dataset.get('review_only') else f'{count} data notices · {fixes} preparation ' + ('note' if fixes == 1 else 'notes')),
                  html.A('View overview and notes', href='#w-review-overview', **{'data-review-target': 'w-review-overview'})]
    return review_checks(True, pending, opened, active), sticky


def review_checks(expanded, pending, opened, active):
    if not expanded or not opened:
        return ''
    dataset = pending or active
    if not dataset or dataset.get('review_only'):
        return html.P('Resolve required worksheet fields first. Data checks will appear here after preparation.')
    status = eligibility(dataset)
    return [html.H4('Research eligibility'), html.Strong(status.children[0].children), status.children[1],
            *quality_details(dataset, limit=20), cards(facts(dataset))]


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


# The dataset and disease are State, not Input. As Inputs this callback also fired
# whenever the dataset was activated, the disease dropdown was repopulated, or the
# page reloaded -- each time returning None and clearing a forecast the user had
# already generated. `render` already discards a result whose dataset or disease no
# longer matches the active one, so a stale forecast cannot be shown.
@app.callback(Output('w-result', 'data'), Input('w-run', 'n_clicks'), State('w-active', 'data'),
              State('w-disease', 'value'), State('w-result', 'data'), prevent_initial_call=True,
              running=[(Output('w-run', 'disabled'), True, False),
                       (Output('w-run', 'children'), 'Generating forecast...', 'Generate Forecast'),
                       (Output('w-fitting', 'children'), 'Generating your forecast. This may take a few minutes. Results will appear automatically.', '')])
def forecast(_clicks, active, disease, prior):
    if ctx.triggered_id != 'w-run' or not active or not active.get('records') or not disease:
        return None
    try:
        config = model_configuration()
        if prior and prior.get('cache_key') == cache_key(active, disease, config):
            return current_result(prior)
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
        rows.append({'Model': label, 'Evaluation status': status, 'MAPE nonzero weeks': metrics.get('mape_n', 'N/A'), **{{'mae': 'MAE (cases)', 'rmse': 'RMSE (cases)', 'mape': 'MAPE (%)'}[key]: round(metrics[key], 3) if metrics.get(key) is not None else 'N/A'
                                      for key in ['mae', 'rmse', 'mape']}})
    return table(rows, {key: key for key in rows[0]})


def horizon_metrics_table(result):
    rows = []
    for horizon, evidence in (result or {}).get('horizon_metrics', {}).items():
        for model, label in [('hybrid', 'Hybrid SARIMA–NNAR'), ('sarima', 'SARIMA-only')]:
            values = evidence['metrics'].get(model) or {}
            rows.append({'Weeks': f'1–{horizon}', 'Model': label, 'Scored weeks': evidence['scored_weeks'],
                         'Missing actuals excluded': evidence['excluded_missing_actuals'], 'MAPE nonzero weeks': values.get('mape_n', 'N/A'),
                         **{{'mae': 'MAE (cases)', 'rmse': 'RMSE (cases)', 'mape': 'MAPE (%)'}[key]: round(values[key], 3) if values.get(key) is not None else 'N/A'
                            for key in ['mae', 'rmse', 'mape']}})
    return table(rows, {key: key for key in rows[0]}) if rows else html.P('Horizon-specific evaluation is not available yet.')


def warning_summary(messages):
    if not messages:
        return []
    return [disclosure(f"{len(messages)} data {'notice' if len(messages) == 1 else 'notices'} to review",
                       [html.P(message) for message in messages])]


@app.callback(Output('w-page-title', 'children'), Output('w-disease-toolbar', 'style'),
              Input('w-page', 'value'), Input('w-active', 'data'))
def page_toolbar(page, active):
    return NAV_LABELS.get(page, page), {} if active and active.get('records') and page != 'About the Model' else {'display': 'none'}


def empty_overview():
    figure = go.Figure()
    figure.update_layout(
        template='plotly_white', height=340,
        margin={'l': 40, 'r': 15, 't': 20, 'b': 85},
        xaxis={'title': 'Reporting week', 'showticklabels': False},
        yaxis={'title': 'Cases', 'rangemode': 'tozero', 'range': [0, 1], 'tickvals': [0]},
        annotations=[{'text': 'Weekly trends will appear after you confirm a dataset.',
                      'xref': 'paper', 'yref': 'paper', 'x': 0.5, 'y': 0.5,
                      'showarrow': False, 'align': 'center'}],
    )
    return [
        html.Div([html.Span('Active Dataset', className='card-label'),
                  html.Strong('No dataset uploaded'),
                  html.Span('0 included diseases', className='muted')], className='dataset-strip'),
        cards({'Weekly Observations': 0, 'Latest Supplied Week': 'Not available yet',
               'Latest Complete Week': 'Not available yet', 'Forecast Direction': 'Not available yet'}),
        html.Div([
            html.Div([html.H3('Weekly trend'), html.P('No disease data available', className='muted'),
                      dcc.Graph(figure=figure, config={'displaylogo': False, 'displayModeBar': False}),
                      html.P('Upload and confirm weekly records to see reported history here.')],
                     className='dashboard-panel'),
            html.Aside([html.H3('Data status'), html.P('No dataset uploaded', className='status-label'),
                        html.P('Zero observations means no records are loaded. It does not indicate zero reported cases.'),
                        source_freshness({}, missing='Not available yet'),
                        html.Button('Go to data upload', **{'data-app-action': 'upload'})], className='dashboard-panel data-status-panel'),
        ], className='overview-columns'),
    ]


def about_model():
    return [html.H3('How the forecast works', className='module-section-title'),
            html.P('The system learns from weekly case reports. SARIMA describes patterns and changes over time. A neural network autoregression model (NNAR) learns patterns in the errors SARIMA leaves behind. Adding that correction produces the Hybrid SARIMA–NNAR forecast.'),
            html.P('The Hybrid is the main projection. SARIMA-only is shown separately for comparison; it never replaces an unavailable Hybrid forecast.'),
            html.H3('Performance measures', className='module-section-title'), html.Ul([
                html.Li('MAE: the average forecast error in number of cases. Lower values mean closer forecasts.'),
                html.Li('RMSE: an error measure that gives more weight to large misses.'),
                html.Li('MAPE: average percentage error for weeks with nonzero reported counts. Zero-case weeks are excluded from this percentage, but remain in the data and other measures.')]),
            html.H3('Limitations', className='module-section-title'), html.P('Forecasts are projections, not outbreak declarations. Recent reports may be incomplete, and missing weeks can affect performance. Weekly model settings and the final evaluation protocol remain subject to adviser approval where applicable.'),
            html.P('The shaded forecast uncertainty range is provisional. It does not carry a formally validated coverage guarantee. Evaluation results from historical records are retrospective; a future prospective study has not yet been completed.')]


@app.callback(Output('w-content', 'children'), Output('w-context', 'children'), Output('w-forecast-controls', 'style'),
              Output('w-history-controls', 'style'), Output('w-data-controls', 'style'), Output('w-technical-controls', 'style'),
              Output('w-advanced', 'children'), Input('w-page', 'value'), Input('w-active', 'data'), Input('w-disease', 'value'),
              Input('w-result', 'data'), Input('w-horizon', 'value'), Input('w-aggregation', 'value'), Input('w-start', 'value'), Input('w-end', 'value'),
              running=[(Output('w-navigation-progress', 'children'), 'Loading view...', ''),
                       (Output('w-content', 'aria-busy'), 'true', 'false')])
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
                 html.P('Provisional range: Hybrid ± training SARIMA residual RMSE, clipped at zero. MAPE uses nonzero actuals (coverage is recorded). Missing actuals are excluded using the same holdout positions for both models.')] if page == 'About the Model' else []
    if page == 'About the Model':
        if active and active.get('records'):
            technical.append(disclosure('Source information and eligibility evidence', advanced({'metadata': active['metadata'], 'quality': active['quality'], 'eligibility_reasons': active['eligibility_reasons']})))
        return about_model(), (active or {}).get('context', ''), *styles, technical
    if not active or not active.get('records'):
        if page == 'Overview':
            return empty_overview(), '', *styles, technical
        return [html.H2('Your weekly outlook starts with your data'), html.P('Open Data to upload weekly records, review the changes, and confirm the dataset you want to use.'),
                notice('No dataset is currently in use.'),
                html.Button('Go to data upload', **{'data-app-action': 'upload'})], '', *styles, technical
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
                            source_freshness(meta),
                            html.Button('Review source information', **{'data-app-action': 'source'})], className='dashboard-panel data-status-panel')
            ], className='overview-columns')]
    elif page == 'Forecast':
        content.append(html.H3('Forecast status and next steps', className='module-section-title'))
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
        if result and result.get('failure_reason'):
            reason = result['failure_reason']
            source_issue = any(term in reason.lower() for term in ['no complete, reported weeks', 'complete for training', 'calendar', 'source metadata', 'reporting status'])
            content.append(html.Div([
                html.H4('Source information needs attention' if source_issue else 'Why this forecast is unavailable'),
                html.P(friendly_reason(reason)),
                *([html.Button('Update source information', **{'data-app-action': 'source'})] if source_issue else []),
            ], className='forecast-action-panel'))
        content += [html.P((result or {}).get('context', active['context'])),
                    html.P((result or {}).get('configuration_label') or installed_protocol_label()),
                    html.H3('Weekly outlook', className='module-section-title'),
                    html.P(f'Displaying next {horizon} forecast weeks. The first weeks remain the same across display ranges; historical evaluation uses a separate fixed holdout.' if (result or {}).get('hybrid') or (result or {}).get('sarima') else 'No future forecast is available yet. The chart below shows historical reports only; changing the horizon cannot change those reports.'),
                    dcc.Graph(figure=forecast_chart(active, disease, result, horizon), config={'displaylogo': False}),
                    html.H3('Historical model performance', className='module-section-title'), metrics_table(result),
                    html.P('Complete reports and incomplete/unknown reports are separate groups on the chart. Incomplete/unknown reports are retained for inspection but excluded from model training.'),
                    html.P('MAE shows average error in cases. RMSE emphasizes larger errors. MAPE measures percentage error on nonzero reported counts; its coverage is shown and N/A means unavailable. Historical performance is retrospective.'),
                    *warning_summary(messages)]
    elif page == 'Historical Trends':
        content.append(html.H3('Historical observations', className='module-section-title'))
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
        content += [html.H3('Data notes', className='module-section-title'),
                    html.P('Changing this view does not change the weekly forecast.'), *warning_summary(messages),
                    html.Button('Review source information', **{'data-app-action': 'source'})]
    elif page == 'Data':
        content = [html.H3('Current Dataset', className='module-section-title'), html.H4(meta.get('source_file') or 'Not specified'), cards(facts(active)), eligibility(active),
                   disclosure('View Data Summary', [html.P(f"{q['observation_count']} weekly observations · {len(q['diseases'])} diseases · {q['year_coverage'][0]}–{q['year_coverage'][1]}"),
                       *[notice(w) for w in messages], *quality_details(active, limit=20),
                       html.P(f"Preview: first {min(100, len(active['records']))} of {len(active['records'])} records. Download Results on Forecast includes all records."),
                       table(active['records'], LABELS, limit=100, page_size=10)]),
                   disclosure('View Source Details', [html.P('Source reference: ' + str(meta.get('provenance') or 'Not specified')),
                       source_freshness(meta),
                       table([{'Step': {'validated': 'Checked', 'confirmed': 'Reviewed', 'prepared': 'Prepared'}.get(r['event'], r['event'].title()), 'Date': display_timestamp(r['at'])} for r in active['audit']])])]
    return content, banner, *styles, technical


@app.callback(Output('w-download', 'data'), Input('w-export', 'n_clicks'), Input('w-export-json', 'n_clicks'),
              State('w-active', 'data'), State('w-result', 'data'), prevent_initial_call=True,
              running=[(Output('w-export-progress', 'children'), 'Preparing your download...', ''),
                       (Output('w-export', 'children'), 'Preparing download...', 'Download Results'),
                       (Output('w-export-json', 'children'), 'Preparing download...', 'Download Detailed Evidence'),
                       (Output('w-export', 'disabled'), True, False), (Output('w-export-json', 'disabled'), True, False)])
def export(_csv, _json, active, result):
    result = current_result(result)
    if not active or not active.get('records'):
        return no_update
    if result and result.get('dataset_id') != active['id']:
        result = None
    if ctx.triggered_id == 'w-export-json':
        return dcc.send_string(json.dumps({'dataset': active, 'forecast': result}, indent=2, ensure_ascii=False), 'weekly-evidence.json')
    return dcc.send_data_frame(export_frame(active, result).to_csv, 'weekly-forecast.csv', index=False)


@app.callback(Output('w-snapshot-status', 'children'), Input('w-snapshot', 'n_clicks'), Input('w-reconcile', 'n_clicks'),
              State('w-active', 'data'), State('w-result', 'data'), State('w-snapshot-id', 'value'), prevent_initial_call=True,
              running=[(Output('w-snapshot-progress', 'children'), 'Processing forecast record...', ''),
                       (Output('w-snapshot', 'disabled'), True, False), (Output('w-reconcile', 'disabled'), True, False)])
def prospective(_issue, _reconcile, active, result, identifier):
    try:
        if not active or not active.get('records'):
            raise ValueError('Choose a dataset first.')
        if ctx.triggered_id == 'w-snapshot':
            return notice('Forecast saved. Reference: ' + save_snapshot(active, result or {}))
        return advanced(reconcile(identifier, active))
    except Exception as exc:
        return notice(str(exc))


@app.callback(Output('w-dataset-badge', 'children'), Input('w-active', 'data'))
def dataset_badge(active):
    if not active or not active.get('records'):
        return 'No dataset loaded'
    return 'Demo data' if active.get('metadata', {}).get('dataset_type') == 'synthetic' else 'Uploaded data'
