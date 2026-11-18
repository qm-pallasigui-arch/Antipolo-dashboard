"""Monthly presentation and callbacks; all authoritative state lives server-side."""
import base64
import json
import logging
import time

from .repositories.batch_repository import BatchRepository, ACTIVE_STATUSES
from urllib.parse import quote

from dash import Input, Output, State, ctx, dcc, html, no_update
from dash.exceptions import PreventUpdate

from .forecast import ForecastService, ModelFailure
from .reports import build_report, export_csv, export_html
from .security import current_user, install_security
from .store import Store, require_admin
from .components import button, confirm_action, disclosure, message, page_heading, section, table, readable_text, empty_state, chart_controls, disease_label, application_shell
from .views import DESCRIPTIONS, page_content, provenance, filtered_notifications, grouped_failures, coverage_rows, coverage_panel
from .navigation import PAGES, ROLE_LABELS
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
    app.layout = application_shell([
        dcc.Location(id='m-location', refresh=False), dcc.Store(id='m-display-options', data={'horizon': 12, 'history': 'recent'}), dcc.Store(id='m-revision', data=0), dcc.Store(id='m-server-state'), dcc.Store(id='m-pending-choice'), dcc.Download(id='m-download'),
        dcc.Interval(id='m-poll', interval=30000),
        dcc.Interval(id='m-batch-poll', interval=2000), dcc.Store(id='m-batch-state'),
        dcc.Input(id='m-page', value='Dashboard', type='hidden'),
        html.Div([html.Div(id='m-heading'),
            html.Div([html.Label('Selected disease group', htmlFor='m-block'),
                dcc.Dropdown(id='m-block', clearable=False, placeholder='No groups available', persistence=True, persistence_type='session')],
                id='m-context', className='m-page-controls')], className='m-page-header'),
        dcc.Loading(html.Div(id='m-message', role='status', **{'aria-live': 'polite'}), delay_show=200),
        html.Div([section('Upload and review a dataset', [
            html.P('CSV or XLSX · up to 10 MB. Required columns: year, month, icd10_block, icd10_description, consultation_count. One row per reported block/month. All workbook sheets must use this structure.'),
            dcc.Upload(id='m-upload', children=html.Div([button('Choose monthly dataset'), html.Span(' or drop a CSV / XLSX file here')]), accept='.csv,.xlsx', multiple=False, className='m-upload-zone'),
            html.Label('Pending upload', htmlFor='m-candidate'), dcc.Dropdown(id='m-candidate', clearable=True, placeholder='Choose an upload to review'),
            html.Div(id='m-preview'), html.Fieldset([html.Legend('Actions for the selected pending upload'),
                html.Div([confirm_action('Confirm & Activate', 'm-activate', 'Activate the reviewed upload? It will replace the active dataset. Previous data and reports are retained.', disabled=True), button('Withdraw pending upload', 'm-cancel', 'secondary', disabled=True),
                confirm_action('Reject reviewed upload', 'm-reject', 'Reject this pending upload? The active dataset will remain unchanged.', 'danger', disabled=True)], className='m-actions'),
                html.P('Withdraw removes the selected pending upload from review. Reject records that the reviewed upload was not accepted. Both retain the source file and leave active data unchanged.', className='m-muted')], className='m-run-fieldset')], id='m-data-controls', className='m-panel m-span-5', style={'display': 'none'}),
            html.Div(id='m-coverage', className='m-span-7')], id='m-quality-grid', className='m-layout-grid m-quality-grid', style={'display': 'none'}),
        section('Researcher notes / source annotations', [html.Div([
            html.Label('Source annotation', htmlFor='m-note'), dcc.Textarea(id='m-note', title='Record a researcher note without changing official values.'),
            html.P('Record a researcher note without changing official values.', id='m-note-help', className='m-muted'),
            button('Save annotation', 'm-save-note', 'secondary')], id='m-note-form'), html.Div(id='m-note-list')], id='m-notes', style={'display': 'none'}),
        section('Forecast controls', [dcc.Loading(html.Div(id='m-forecast-feedback', role='status', **{'aria-live': 'polite'}), delay_show=200),
            html.Div(id='m-stop-feedback'),
            button('Cancel forecast', 'm-stop-button', 'secondary', disabled=True),
            dcc.Store(id='m-stop-target'),
            dcc.ConfirmDialog(id='m-stop', message='Cancel this forecast batch? Completed results are retained. Remaining groups will not run and no new ranking will be generated.'),
            html.Div([html.Div(id='m-generation-summary'),
                      html.P(id='m-generation-elapsed', role='timer', **{'aria-live': 'off'})], id='m-generation-status')],
            'Generating again regenerates all seven groups. Overall rankings use all 12 forecast months.',
            right=html.Fieldset(confirm_action('Generate forecasts and rankings', 'm-run', 'Generate a new forecast attempt for all seven groups? Existing results are retained; the latest attempt will be shown.'), id='m-run-fieldset', className='m-run-fieldset'),
            id='m-forecast-controls', className='m-panel m-generation-strip', style={'display': 'none'}),
        section('Download a report', [html.Div([section(title, [html.P(description), button(label, identity, variant)]) for title, description, label, identity, variant in [
            ('HTML report', 'Readable and printable report for the selected group, including overall projected rankings.', 'Download HTML report', 'm-report-html', 'primary'),
            ('Research data (JSON)', 'Structured selected-group results, model details and overall projected rankings.', 'Download research data (JSON)', 'm-report-json', 'secondary'),
            ('CSV values', 'Selected-group monthly history and saved forecasts, with explicit availability labels.', 'Download CSV values', 'm-report-csv', 'secondary')]], className='m-report-grid')], id='m-report-controls', style={'display': 'none'}),
        html.Div([section('Filter notifications', [html.Label('Read status', htmlFor='m-notification-status'),
            dcc.Dropdown(id='m-notification-status', options=[{'label': label, 'value': value} for value, label in [('all', 'All statuses'), ('unread', 'Unread'), ('read', 'Read')]], value='all', clearable=False),
            html.Label('Category', htmlFor='m-notification-type'), dcc.Dropdown(id='m-notification-type', options=[{'label': label, 'value': value} for value, label in [('all', 'All categories'), ('security', 'Accounts and security'), ('dataset', 'Dataset updates'), ('data_quality', 'Data quality'), ('forecast', 'Forecasts'), ('report', 'Reports'), ('system', 'System')]], value='all', clearable=False),
            confirm_action('Mark visible notifications read', 'm-read', 'Mark notifications matching the current filters as read?', 'secondary')], id='m-notification-controls', style={'display': 'none'}),
        dcc.Loading(html.Div(html.Div(chart_controls(), hidden=True), id='m-content'), type='circle', delay_show=200)], id='m-secondary-layout')])

    @app.callback(Output('m-generation-summary', 'children'), Output('m-generation-elapsed', 'children'), Output('m-run-fieldset', 'disabled'),
                  Output('m-batch-state', 'data'), Output('m-stop-button', 'disabled'), Input('m-batch-poll', 'n_intervals'),
                  State('m-batch-state', 'data'))
    def batch_progress(_, previous):
        user = current_user()
        with store.connect() as db:
            active = db.execute("SELECT signature FROM datasets WHERE state='active'").fetchone()
        batch = BatchRepository(store).latest(active[0]) if active else None
        if not batch:
            return '', '', False, None if previous else no_update, True
        running = batch['status'] in ACTIVE_STATUSES
        stop_disabled = user['role'] != 'admin' or batch['status'] not in ('queued', 'running')
        elapsed = max(0, int((time.time() if running else batch.get('finished', time.time())) - batch['started']))
        text = f"{batch['completed']} of 7 groups processed; {batch['successes']} completed, {len(batch['failures'])} failed. "
        if batch['status'] == 'queued':
            text += 'Queued; waiting for the forecast worker. You may leave this page.'
        elif batch['status'] == 'cancelling':
            text += 'Cancellation requested; waiting for the forecast process to stop.'
        elif running:
            text += f"Processing {batch['current'] or 'batch preparation'}."
        else:
            text += f"Batch {batch['status']}. " + batch.get('error', '')
        tone = 'info' if running else 'success' if batch['status'] == 'completed' else 'error' if batch['status'] in ('failed', 'interrupted') else 'warning'
        token = [batch['id'], batch['status'], batch['completed'], batch['current'],
                 batch['successes'], batch['failures'], batch.get('error', '')]
        if token == previous:
            return no_update, f'Elapsed: {elapsed}s', running, no_update, stop_disabled
        if not running and batch['completed'] == 7:
            from .repositories.ranking_repository import RankingRepository
            ranking = RankingRepository(store).latest(active[0])
            if ranking and ranking['forecast_run_group_id'] == batch['id']:
                text += f" PROTOTYPE: {len(ranking['rankings'])} valid blocks ranked over twelve months. "
                text += 'Projected Top Five available.' if ranking['top_five_status'] == 'available' else 'Projected Top Five unavailable.'
        children = [message(text, tone)]
        if batch['failures']:
            dataset = store.active()
            causes = grouped_failures(store, dataset, batch) if dataset else []
            children.extend(html.P(cause) for cause in causes)
        history = BatchRepository(store).history(active[0])
        children.append(disclosure('Run details', [html.P('Batch reference: ' + batch['id']),
            html.P('Recent batches for this dataset and configuration (up to 20; all records retained).'),
            table([{'batch': b['id'], 'status': b['status'], 'processed': b['completed'],
                    'completed': b['successes'], 'failed': len(b['failures'])} for b in history])]))
        return children, f'Elapsed: {elapsed}s', running, token, stop_disabled

    @app.callback(Output('m-stop', 'displayed'), Output('m-stop-target', 'data'),
                  Input('m-stop-button', 'n_clicks'), prevent_initial_call=True)
    def confirm_stop(_):
        user = current_user()
        require_admin(user)
        dataset = store.active()
        batch = BatchRepository(store).latest(dataset['dataset_signature']) if dataset else None
        if not batch or batch['status'] not in ('queued', 'running'):
            raise PreventUpdate
        return True, batch['id']

    @app.callback(Output('m-stop-feedback', 'children'), Input('m-stop', 'submit_n_clicks'),
                  Input('m-run', 'submit_n_clicks'),
                  State('m-stop-target', 'data'), prevent_initial_call=True)
    def stop_batch(_, __, identity):
        if ctx.triggered_id == 'm-run':
            return ''
        try:
            BatchRepository(store).cancel(current_user(), identity)
            return message('Cancellation requested. Follow the batch status below.')
        except (PermissionError, ValueError) as exc:
            return message(str(exc), 'error')

    @app.callback(Output('m-heading', 'children'), Output('m-context', 'style'), Output('m-secondary-layout', 'className'), Input('m-page', 'value'))
    def heading(page):
        current_user()
        return (page_heading(page, DESCRIPTIONS.get(page, '')),
                {'display': 'none'} if page in ('Notifications', 'Help & About', 'Data & Quality') else {},
                'm-notifications-layout' if page == 'Notifications' else '')

    @app.callback(Output('m-display-options', 'data'), Input('m-horizon', 'value'), Input('m-history-window', 'value'), State('m-display-options', 'data'))
    def display_options(horizon, history, previous):
        current_user()
        value = {'horizon': horizon or 12, 'history': history or 'recent'}
        return no_update if value == previous else value

    @app.callback(Output('m-notes', 'style'), Output('m-note-form', 'style'), Output('m-note-list', 'children'), Output('m-save-note', 'disabled'),
                  Input('m-page', 'value'), Input('m-revision', 'data'), Input('m-server-state', 'data'))
    def annotations(page, _, __):
        user = current_user()
        dataset = store.active()
        notes = store.notes(dataset['dataset_signature']) if dataset and page == 'Data & Quality' else []
        return ({} if page == 'Data & Quality' else {'display': 'none'}, {} if user['role'] == 'admin' else {'display': 'none'},
                table(notes) if notes else empty_state('No annotations yet', 'Use the Source annotation field above to add a note.' if user['role'] == 'admin' and dataset else 'Activate a dataset before adding notes.' if user['role'] == 'admin' else 'An administrator can add source annotations here.'),
                not dataset or user['role'] != 'admin')

    @app.callback(Output('m-page', 'value'), Output('m-location', 'search'), Input('m-location', 'search'), Input('m-page', 'value'))
    def route(search, selected):
        from urllib.parse import parse_qs
        if ctx.triggered_id == 'm-page':
            target = '?module=' + quote(selected if selected in PAGES else 'Dashboard')
            return no_update, target if target != search else no_update
        page = parse_qs((search or '').lstrip('?')).get('module', ['Dashboard'])[0]
        page = page if page in PAGES else 'Dashboard'
        return page if page != selected else no_update, no_update

    @app.callback(Output('m-server-state', 'data'), Input('m-poll', 'n_intervals'), State('m-server-state', 'data'))
    def poll(_, previous):
        token = store.state_token(current_user())
        return token if token != previous else no_update

    @app.callback(Output('m-block', 'options'), Output('m-block', 'value'), Output('m-candidate', 'options'),
                  Output('m-candidate', 'value'),
                  Output('m-user', 'children'), Output('m-account', 'style'), Output('m-dataset', 'children'),
                  Output('m-notifications-link', 'children'),
                  Output('m-source-context', 'children'),
                  Input('m-revision', 'data'), Input('m-server-state', 'data'), Input('m-pending-choice', 'data'),
                  State('m-block', 'value'), State('m-candidate', 'value'))
    def refresh(_, __, choice, code, current_candidate):
        user = current_user()
        dataset = store.active()
        blocks = dataset['blocks'] if dataset else []
        codes = [b['icd10_block'] for b in blocks]
        options = [{'label': b['icd10_block'] + ' · ' + disease_label(b['icd10_description']), 'value': b['icd10_block']} for b in blocks]
        pending = [{'label': r['uploaded_at'] + ' · ' + r['source_file'], 'value': r['id']} for r in store.pending()] if user['role'] == 'admin' else []
        pending_ids = {p['value'] for p in pending}
        selected = choice if 'm-pending-choice.data' in ctx.triggered_prop_ids else current_candidate
        selected = selected if selected in pending_ids else None
        unread = store.unread_count(user)
        return options, no_update if code in codes else codes[0] if codes else None, pending, no_update if selected == current_candidate else selected, f'{user["username"]} · ' + ROLE_LABELS[user['role']], {} if user['role'] == 'admin' else {'display': 'none'}, 'Dataset active' if dataset else 'No dataset loaded', ['Notifications ', html.Span(str(unread), className='m-count')], dataset['source_file'] if dataset else 'No active dataset'

    @app.callback(Output('m-content', 'children'), Output('m-data-controls', 'style'), Output('m-forecast-controls', 'style'),
                  Output('m-report-controls', 'style'), Output('m-notification-controls', 'style'), Output('m-run-button', 'disabled'),
                  Output('m-quality-grid', 'style'), Output('m-coverage', 'children'), Output('m-coverage', 'className'),
                  Input('m-page', 'value'), Input('m-block', 'value'), Input('m-display-options', 'data'), Input('m-revision', 'data'), Input('m-server-state', 'data'), Input('m-notification-status', 'value'), Input('m-notification-type', 'value'), Input('m-batch-state', 'data'))
    def render(page, code, display_options, _, __, notification_status, notification_type, batch_state):
        horizon = (display_options or {}).get('horizon', 12)
        history_window = (display_options or {}).get('history', 'recent')
        user = current_user()
        triggered = set(ctx.triggered_prop_ids)
        if (triggered == {'m-display-options.data'} and page != 'Forecasting'
                or triggered <= {'m-notification-status.value', 'm-notification-type.value'} and triggered and page != 'Notifications'
                or triggered == {'m-block.value'} and page in ('Data & Quality', 'Notifications', 'Help & About')):
            raise PreventUpdate
        dataset = store.active()
        block = next((b for b in dataset['blocks'] if b['icd10_block'] == code), None) if dataset else None
        show = lambda condition: {} if condition else {'display': 'none'}
        return (page_content(store, user, page, dataset, code, horizon or 12, notification_status, notification_type, history_window),
                show(page == 'Data & Quality' and user['role'] == 'admin'), show(page == 'Forecasting'),
                show(page == 'Reports' and dataset is not None), show(page == 'Notifications'),
                user['role'] != 'admin' or not block or not service.configured,
                show(page == 'Data & Quality'), coverage_panel(store, dataset) if page == 'Data & Quality' else None,
                'm-span-7' if user['role'] == 'admin' else 'm-span-12')

    @app.callback(Output('m-activate-button', 'disabled'), Output('m-cancel', 'disabled'), Output('m-reject-button', 'disabled'), Input('m-candidate', 'value'), Input('m-revision', 'data'))
    def pending_actions(candidate_id, _):
        disabled = current_user()['role'] != 'admin' or not candidate_id or not store.candidate(candidate_id)
        return bool(disabled), bool(disabled), bool(disabled)

    @app.callback(Output('m-preview', 'children'), Input('m-candidate', 'value'), Input('m-revision', 'data'), Input('m-page', 'value'))
    def preview(candidate_id, _, page):
        user = current_user()
        if page != 'Data & Quality':
            return None
        if user['role'] != 'admin' or not candidate_id:
            return message('Select a pending upload to review. Uploads never replace the active dataset automatically.')
        candidate = store.candidate(candidate_id)
        if not candidate:
            return message('This upload is no longer pending.')
        return [provenance(candidate), html.H3('Upload validation and coverage'),
            table(coverage_rows(candidate), ['icd10_block', 'top5_year_count', 'reported_month_count', 'observed_zero_count', 'upload_status']),
            html.Ul([html.Li(w) for w in candidate['warnings']]),
            html.H3('Normalized preview — confirm year, month, block, description and count'),
            table(candidate['observations'], ['year', 'month', 'icd10_block', 'icd10_description', 'consultation_count', 'observation_status']),
            message('Review this upload before pressing Confirm & Activate.')]

    @app.callback(Output('m-message', 'children'), Output('m-revision', 'data'), Output('m-download', 'data'),
                  Output('m-pending-choice', 'data'), Output('m-upload', 'contents'), Output('m-forecast-feedback', 'children'),
                  Input('m-upload', 'contents'), Input('m-activate', 'submit_n_clicks'), Input('m-cancel', 'n_clicks'),
                  Input('m-reject', 'submit_n_clicks'), Input('m-save-note', 'n_clicks'), Input('m-run', 'submit_n_clicks'),
                  Input('m-report-html', 'n_clicks'), Input('m-report-json', 'n_clicks'), Input('m-report-csv', 'n_clicks'), Input('m-read', 'submit_n_clicks'),
                  State('m-upload', 'filename'), State('m-candidate', 'value'), State('m-note', 'value'), State('m-block', 'value'),
                  State('m-horizon', 'value'), State('m-revision', 'data'), State('m-notification-status', 'value'), State('m-notification-type', 'value'), prevent_initial_call=True)
    def action(contents, activate, cancel, reject, note_click, run, report_html, report_json, report_csv, read,
               filename, candidate_id, note, code, horizon, revision, notification_status, notification_type):
        user = current_user()
        trigger = ctx.triggered_id
        download, candidate = no_update, no_update
        tone = 'success'
        try:
            if trigger == 'm-upload':
                require_admin(user)
                if not contents:
                    return (no_update,) * 6
                if len(contents) > 14 * 1024 * 1024:
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
                service.submit(user)
                tone = 'info'
                text = 'Forecast request accepted. Follow the saved batch status below; you may leave or refresh this page.'
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
                return (no_update,) * 6
        except PermissionError as exc:
            tone = 'error'
            text = 'Permission denied: ' + str(exc)
        except (ValueError, ModelFailure) as exc:
            tone = 'error'
            text = readable_text(str(exc))
        except Exception:
            tone = 'error'
            logging.getLogger(__name__).exception('Monthly action failed')
            store.notify('system', 'System processing failure', 'An operation failed. Check server logs.', 'Data & Quality', role='admin', severity='error')
            text = 'System failure. The operation could not be completed; check server logs.'
        # Release the base64 file after staging; later actions must not resend it.
        feedback = message(text, tone)
        return ('' if trigger == 'm-run' else feedback, (revision or 0) + 1, download, candidate,
                None if trigger == 'm-upload' else no_update, feedback if trigger == 'm-run' else no_update)

    return store, service
