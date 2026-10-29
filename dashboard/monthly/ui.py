"""Monthly presentation and callbacks; all authoritative state lives server-side."""
import base64
import json
import logging
from urllib.parse import quote

from dash import Input, Output, State, ctx, dcc, html, no_update

from .domain import LIMITATIONS
from .forecast import ForecastService, ModelFailure, NotEligible
from .reports import build_report, export_csv, export_html
from .security import current_user, install_security
from .store import Store, require_admin
from .components import button, confirm_action, message, page_heading, section, table
from .views import DESCRIPTIONS, page_content, provenance, filtered_notifications
from .navigation import PAGES, NAV_PAGES, NAV_LABELS, ROLE_LABELS
from .views import trend_chart as trend_chart  # Compatibility export for existing consumers.

__all__ = ['install', 'page_content', 'trend_chart']




def install(app, store=None, service=None):
    store = store or Store()
    service = service or ForecastService(store)
    # Allow base64/JSON overhead around a 10 MB source; parser enforces raw limit.
    app.server.config['MAX_CONTENT_LENGTH'] = 15 * 1024 * 1024
    install_security(app.server, store)
    app.title = 'Antipolo · Monthly ICD-10 Consultations'
    app.config.suppress_callback_exceptions = True
    app.layout = html.Div(className='monthly-app', children=[
        dcc.Location(id='m-location'), dcc.Store(id='m-revision', data=0), dcc.Store(id='m-pending-choice'), dcc.Download(id='m-download'),
        dcc.Interval(id='m-poll', interval=30000),
        html.Header([html.Div([html.Div([html.Span(), html.Span(), html.Span()], className='m-brand-mark', **{'aria-hidden': 'true'}),
            html.Div([html.H1('Antipolo Disease Forecasting'), html.P('Monthly ICD-10 consultations · Ages 5–19')])], className='m-brand'),
            html.Div([html.Span('No dataset loaded', id='m-dataset', className='m-header-badge'),
                html.A('Notifications', id='m-notifications-link', href='/?module=Notifications', className='m-header-control'),
                html.Details([html.Summary([html.Span('A', className='m-avatar'), ' Account']), html.Div([html.Span(id='m-user'),
                    html.A('Security / Accounts', href='/account', id='m-account'), html.A('Sign out', href='/logout')],
                    className='m-account-menu')], className='m-account')], className='m-header-tools')], className='m-app-header'),
        html.Nav(dcc.Tabs(id='m-page', value='Dashboard', className='m-nav-tabs', children=[
            dcc.Tab(label=NAV_LABELS.get(p, p), value=p, className='m-nav-tab', selected_className='m-nav-tab--selected') for p in NAV_PAGES]),
            className='m-desktop-nav', **{'aria-label': 'Main navigation'}),
        html.Nav(html.Details([html.Summary('Navigate modules'), html.Div([html.A(NAV_LABELS.get(p, p), href='/?module=' + quote(p)) for p in NAV_PAGES])]),
                 className='m-mobile-nav', **{'aria-label': 'Mobile navigation'}),
        html.Div(id='m-heading'),
        html.Div([html.Div([html.Label('Selected disease group', htmlFor='m-block'), dcc.Dropdown(id='m-block', clearable=False, placeholder='No groups available', persistence=True, persistence_type='session')]),
            html.P('No active dataset', id='m-source-context', className='m-muted')], id='m-context', className='m-context-toolbar'),
        dcc.Loading(html.Div(id='m-message', role='status', **{'aria-live': 'polite'}), delay_show=200),
        section('Upload and review a dataset', [
            html.P('CSV or XLSX · up to 10 MB. Required columns: year, month, icd10_block, icd10_description, consultation_count. One row per reported block/month. All workbook sheets must use this structure.'),
            dcc.Upload(id='m-upload', children=html.Div([button('Choose monthly dataset'), html.Span(' or drop a CSV / XLSX file here')]), accept='.csv,.xlsx', multiple=False, className='m-upload-zone'),
            html.Label('Pending upload', htmlFor='m-candidate'), dcc.Dropdown(id='m-candidate', clearable=True, placeholder='Choose an upload to review'),
            html.Div(id='m-preview'), html.Div([confirm_action('Confirm & Activate', 'm-activate', 'Activate the reviewed upload? It will replace the active dataset. Previous data and reports are retained.', disabled=True), button('Cancel upload', 'm-cancel', 'secondary', disabled=True),
                confirm_action('Reject upload', 'm-reject', 'Reject this pending upload? The active dataset will remain unchanged.', 'danger', disabled=True)], className='m-actions'),
            html.Label('Source annotation', htmlFor='m-note'), dcc.Textarea(id='m-note', placeholder='Record a researcher note without changing official values.'),
            button('Save annotation', 'm-save-note', 'secondary')], id='m-data-controls', style={'display': 'none'}),
        section('Forecast controls', [html.Label('Show forecast (months)', htmlFor='m-horizon'),
            dcc.RadioItems(id='m-horizon', options=[{'label': f'{n} months', 'value': n} for n in (3, 6, 12)], value=12, className='m-segmented'),
            html.P('Display window only. Overall rankings always use the next 12 months.', className='m-muted'),
            html.Fieldset(button('Generate forecasts and rankings', 'm-run'), id='m-run-fieldset', className='m-run-fieldset'),
            html.P(id='m-generation-status', role='status', **{'aria-live': 'polite'})], id='m-forecast-controls', style={'display': 'none'}),
        section('Download a report', [html.Div([button('Download HTML report', 'm-report-html'),
            button('Download research data (JSON)', 'm-report-json', 'secondary'), button('Download CSV values', 'm-report-csv', 'secondary')], className='m-actions')], id='m-report-controls', style={'display': 'none'}),
        section('Filter notifications', [html.Label('Read status', htmlFor='m-notification-status'),
            dcc.Dropdown(id='m-notification-status', options=['all', 'unread', 'read'], value='all', clearable=False),
            html.Label('Category', htmlFor='m-notification-type'), dcc.Dropdown(id='m-notification-type', options=[{'label': label, 'value': value} for value, label in [('all', 'All categories'), ('security', 'Accounts and security'), ('dataset', 'Dataset updates'), ('data_quality', 'Data quality'), ('eligibility', 'Forecast readiness'), ('forecast', 'Forecasts'), ('report', 'Reports'), ('system', 'System')]], value='all', clearable=False),
            button('Mark visible notifications read', 'm-read', 'secondary')], id='m-notification-controls', style={'display': 'none'}),
        dcc.Loading(html.Main(id='m-content'), type='circle', color='#13756f', delay_show=200), html.Footer(LIMITATIONS, className='m-app-footer')])

    @app.callback(Output('m-heading', 'children'), Output('m-context', 'style'), Input('m-page', 'value'))
    def heading(page):
        current_user()
        return page_heading(page, DESCRIPTIONS.get(page, '')), {}

    @app.callback(Output('m-page', 'value'), Input('m-location', 'search'))
    def route(search):
        from urllib.parse import parse_qs
        page = parse_qs((search or '').lstrip('?')).get('module', ['Dashboard'])[0]
        return page if page in PAGES else 'Dashboard'

    @app.callback(Output('m-block', 'options'), Output('m-block', 'value'), Output('m-candidate', 'options'),
                  Output('m-candidate', 'value'),
                  Output('m-user', 'children'), Output('m-account', 'style'), Output('m-dataset', 'children'),
                  Output('m-notifications-link', 'children'),
                  Output('m-source-context', 'children'),
                  Input('m-revision', 'data'), Input('m-poll', 'n_intervals'), Input('m-pending-choice', 'data'),
                  State('m-block', 'value'), State('m-candidate', 'value'))
    def refresh(_, __, choice, code, current_candidate):
        user = current_user()
        dataset = store.active()
        blocks = dataset['blocks'] if dataset else []
        codes = [b['icd10_block'] for b in blocks]
        options = [{'label': b['icd10_block'] + ' · ' + b['icd10_description'], 'value': b['icd10_block']} for b in blocks]
        pending = [{'label': r['uploaded_at'] + ' · ' + store.candidate(r['id'])['source_file'], 'value': r['id']} for r in store.pending()] if user['role'] == 'admin' else []
        pending_ids = {p['value'] for p in pending}
        selected = choice if 'm-pending-choice.data' in ctx.triggered_prop_ids else current_candidate
        selected = selected if selected in pending_ids else None
        unread = sum(not n['read_at'] for n in store.notifications(user))
        return options, code if code in codes else codes[0] if codes else None, pending, selected, f'{user["username"]} · ' + ROLE_LABELS[user['role']], {} if user['role'] == 'admin' else {'display': 'none'}, 'Dataset active' if dataset else 'No dataset loaded', [html.Span('\U0001f514', **{'aria-hidden': 'true'}), ' Notifications ', html.Span(str(unread), className='m-count')], 'Active dataset: ' + dataset['source_file'] + ' · Overall rankings include all disease groups.' if dataset else 'No active dataset'

    @app.callback(Output('m-content', 'children'), Output('m-data-controls', 'style'), Output('m-forecast-controls', 'style'),
                  Output('m-report-controls', 'style'), Output('m-notification-controls', 'style'), Output('m-run', 'disabled'),
                  Input('m-page', 'value'), Input('m-block', 'value'), Input('m-horizon', 'value'), Input('m-revision', 'data'), Input('m-poll', 'n_intervals'), Input('m-notification-status', 'value'), Input('m-notification-type', 'value'))
    def render(page, code, horizon, _, __, notification_status, notification_type):
        user = current_user()
        dataset = store.active()
        block = next((b for b in dataset['blocks'] if b['icd10_block'] == code), None) if dataset else None
        show = lambda condition: {} if condition else {'display': 'none'}
        return (page_content(store, user, page, dataset, code, horizon or 12, notification_status, notification_type),
                show(page == 'Data & Quality' and user['role'] == 'admin'), show(page == 'Forecasting'),
                show(page == 'Reports' and dataset is not None), show(page == 'Notifications'),
                user['role'] != 'admin' or not block or not service.configured)

    @app.callback(Output('m-activate-button', 'disabled'), Output('m-cancel', 'disabled'), Output('m-reject-button', 'disabled'), Input('m-candidate', 'value'), Input('m-revision', 'data'))
    def pending_actions(candidate_id, _):
        disabled = current_user()['role'] != 'admin' or not candidate_id or not store.candidate(candidate_id)
        return bool(disabled), bool(disabled), bool(disabled)

    @app.callback(Output('m-preview', 'children'), Input('m-candidate', 'value'), Input('m-revision', 'data'))
    def preview(candidate_id, _):
        user = current_user()
        if user['role'] != 'admin' or not candidate_id:
            return message('Select a pending upload to review. Uploads never replace the active dataset automatically.')
        candidate = store.candidate(candidate_id)
        if not candidate:
            return message('This upload is no longer pending.')
        return [provenance(candidate), html.H3('Upload validation and coverage'),
            table(candidate['blocks'], ['icd10_block', 'top5_year_count', 'reported_month_count', 'eligible', 'reason']),
            html.Ul([html.Li(w) for w in candidate['warnings']]),
            html.H3('Normalized preview — confirm year, month, block, description and count'),
            table(candidate['observations'], ['year', 'month', 'icd10_block', 'icd10_description', 'consultation_count', 'observation_status']),
            message('Review this upload before pressing Confirm & Activate.')]

    @app.callback(Output('m-message', 'children'), Output('m-revision', 'data'), Output('m-download', 'data'),
                  Output('m-pending-choice', 'data'),
                  Input('m-upload', 'contents'), Input('m-activate', 'submit_n_clicks'), Input('m-cancel', 'n_clicks'),
                  Input('m-reject', 'submit_n_clicks'), Input('m-save-note', 'n_clicks'), Input('m-run', 'n_clicks'),
                  Input('m-report-html', 'n_clicks'), Input('m-report-json', 'n_clicks'), Input('m-report-csv', 'n_clicks'), Input('m-read', 'n_clicks'),
                  State('m-upload', 'filename'), State('m-candidate', 'value'), State('m-note', 'value'), State('m-block', 'value'),
                  State('m-horizon', 'value'), State('m-revision', 'data'), State('m-notification-status', 'value'), State('m-notification-type', 'value'), prevent_initial_call=True,
                  running=[(Output('m-run-fieldset', 'disabled'), True, False), (Output('m-generation-status', 'children'), 'Processing your request…', '')])
    def action(contents, activate, cancel, reject, note_click, run, report_html, report_json, report_csv, read,
               filename, candidate_id, note, code, horizon, revision, notification_status, notification_type):
        user = current_user()
        trigger = ctx.triggered_id
        download, candidate = no_update, no_update
        tone = 'success'
        try:
            if trigger == 'm-upload':
                require_admin(user)
                if not contents or len(contents) > 14 * 1024 * 1024:
                    raise ValueError('Empty upload or file exceeds 10 MB.')
                raw = base64.b64decode(contents.split(',', 1)[1], validate=True)
                staged = store.stage(user, raw, filename or 'upload')
                candidate = staged['candidate_id']
                text = 'Upload validated and saved for review. Review the preview, then explicitly Confirm & Activate.'
            elif trigger == 'm-activate':
                store.activate(user, candidate_id)
                candidate, text = None, 'Monthly dataset activated. Saved results will match this dataset.'
            elif trigger in ('m-cancel', 'm-reject'):
                store.discard(user, candidate_id, 'cancelled' if trigger == 'm-cancel' else 'rejected')
                candidate, text = None, 'Upload dismissed. Active data remain unchanged.'
            elif trigger == 'm-save-note':
                store.add_note(user, note)
                text = 'Source annotation saved.'
            elif trigger == 'm-run':
                result = service.run_all(user)
                text = f'PROTOTYPE: {len(result["rankings"])} valid blocks ranked over twelve months. ' + ('Projected Top Five available.' if result['top_five_status'] == 'available' else 'Projected Top Five unavailable.')
            elif trigger in ('m-report-html', 'm-report-json', 'm-report-csv'):
                report = build_report(store, user, code)
                extension = trigger.rsplit('-', 1)[1]
                content = export_html(report) if extension == 'html' else export_csv(report) if extension == 'csv' else json.dumps(report, indent=2, ensure_ascii=False)
                download = dict(content=content, filename=f'antipolo-{code}-{report["report_id"][:8]}.{extension}', type={'html': 'text/html', 'csv': 'text/csv', 'json': 'application/json'}[extension])
                text = 'Report generated and recorded.'
            elif trigger == 'm-read':
                store.mark_read(user, [n['id'] for n in filtered_notifications(store, user, notification_status, notification_type)])
                text = 'Visible notifications marked read.'
            else:
                return no_update, no_update, no_update, no_update
        except PermissionError as exc:
            tone = 'error'
            text = 'Permission denied: ' + str(exc)
        except NotEligible as exc:
            tone = 'warning'
            text = 'Not eligible for forecasting: ' + str(exc)
        except (ValueError, ModelFailure) as exc:
            tone = 'error'
            text = str(exc)
        except Exception:
            tone = 'error'
            logging.getLogger(__name__).exception('Monthly action failed')
            store.notify('system', 'System processing failure', 'An operation failed. Check server logs.', 'Data & Quality', role='admin', severity='error')
            text = 'System failure. The operation could not be completed; check server logs.'
        return message(text, tone), (revision or 0) + 1, download, candidate

    return store, service
