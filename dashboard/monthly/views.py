"""Module views composed from the shared monthly component library."""
import json
from datetime import datetime
from urllib.parse import quote

from dash import dcc, html

from .charts import trend_figure, has_intervals, evaluation_figure
from .components import (badge, disclosure, empty_state, message, metric_card,
                         metric_grid, section, table, timestamp, format_number,
                         forecast_outcome, readable_text, ranked_list, chart_controls, disease_label)
from .domain import AVAILABLE_YEARS, PROVENANCE, annual_history
from .forecast import METHOD_PENDING
from .forecasting.config import RANKING_SCOPE
from .navigation import PUBLIC_NOTICE
from .repositories.ranking_repository import RankingRepository

DESCRIPTIONS = {
    'Dashboard': 'A clear view of monthly consultations, reporting coverage and model outcomes.',
    'Disease Trends': 'Explore all historically reported ICD-10 blocks and their data availability.',
    'Forecasting': 'View monthly consultation estimates for all seven ICD-10 blocks.',
    'Model Performance & Insights': 'Review hybrid model evaluation evidence and limitations.',
    'Data & Quality': 'Review source data, reporting coverage and data quality before activation.',
    'Reports': 'Export historical trends, forecast availability and supporting evidence.',
    'Notifications': 'Keep track of dataset updates, reports and system activity.',
    'Help & About': 'Understand the study, its data and how to use the application.',
}


def provenance(dataset=None):
    return section('Data provenance', [html.Dl([
        html.Div([html.Dt(k.replace('_', ' ').capitalize()), html.Dd(', '.join(map(str, v)) if isinstance(v, list) else v)])
        for k, v in (dataset or {}).get('provenance', PROVENANCE).items()]),
        disclosure('Source file and dataset signature', [html.P((dataset or {}).get('source_file', 'Not uploaded')),
            html.Code((dataset or {}).get('dataset_signature', 'No active dataset'))])])


def trend_chart(dataset, code, forecast=None, focus_forecast=False):
    return dcc.Graph(figure=trend_figure(dataset, code, forecast, focus_forecast), responsive=True, config={'displaylogo': False, 'responsive': True})


def block_summary(block, latest=None):
    cards = [metric_card('Annual Top-5 recurrence', f'{block["top5_year_count"]} / 8', 'Available reporting years'),
             metric_card('Reported monthly observations', str(block['reported_month_count']), 'Coverage count; reported zeros included'),
             metric_card('Data quality', 'Coverage assessed', coverage_text(block))]
    cards.append(metric_card('Latest observation', f'{latest["consultation_count"]:,}' if latest else 'Not available', f'{latest["month"]} {latest["year"]} consultations' if latest else 'No reported observation'))
    return metric_grid(cards)


def coverage_text(block):
    return block['coverage_summary']


def coverage_rows(dataset):
    represented = {row['icd10_block'] for row in dataset['observations']}
    return [{**block, 'upload_status': 'In upload' if block['icd10_block'] in represented else badge('Not in upload'),
             **({key: '—' for key in ('top5_year_count', 'reported_month_count', 'observed_zero_count')}
                if block['icd10_block'] not in represented else {})}
            for block in dataset['blocks']]


def quality(dataset):
    return disclosure(f'Data-quality warnings ({len(dataset["warnings"])})',
                      [html.Ul([html.Li(w) for w in dataset['warnings']])])


def coverage_panel(store, dataset):
    """Active coverage beside persistent upload controls; pending previews stay separate."""
    if not dataset:
        return section('Coverage and data quality', [empty_state('No active coverage to review',
            'Coverage will appear after an administrator activates a verified monthly dataset.')])
    return section('Coverage and data quality', [table(coverage_rows(dataset),
        ['icd10_block', 'icd10_description', 'top5_year_count', 'reported_month_count', 'observed_zero_count', 'upload_status']),
        *[message(text, 'warning') for text in grouped_failures(store, dataset)], quality(dataset),
        disclosure('Missing periods by block', [table(dataset['blocks'], ['icd10_block', 'missing_years', 'missing_months'])])],
        'Active dataset coverage. All historically reported blocks remain available for descriptive analysis.')


def data_status(dataset, user, forecast=None):
    return section('Data status', [
        html.P('Reported zeros remain valid observations. Unavailable counts are never converted to zero.'),
        html.H4('Model status'), html.P(forecast_outcome(forecast)),
        html.H4('Source freshness'), html.Dl([html.Div([html.Dt(label), html.Dd(timestamp(value))]) for label, value in [
            ('Document prepared', PROVENANCE['document_prepared_at']), ('Uploaded', (dataset or {}).get('uploaded_at'))]]),
        html.A('Go to data upload' if user['role'] == 'admin' else 'Review data quality', href='/?module=Data%20%26%20Quality')])


def no_data(page, user):
    action = html.A('Go to data upload', href='/?module=Data%20%26%20Quality', className='m-button m-button--primary') if user['role'] == 'admin' else None
    state = empty_state('No monthly dataset is active', 'Upload and activate a verified monthly dataset to view consultation trends.'
                        if user['role'] == 'admin' else 'An administrator needs to activate the monthly dataset before results can be viewed.', action)
    if page == 'Dashboard':
        return [html.Div([
            section('Projected Top Five', [state], variant='featured', className='m-panel m-span-8 m-ranking-card'),
            html.Div(data_status(None, user), className='m-span-4'),
            section('Selected group at a glance', [metric_grid([metric_card(label, 'Not available', detail) for label, detail in [
            ('Annual Top-5 recurrence', 'Available reporting years'), ('Reported monthly observations', 'Reported zeros are included'),
            ('Model status', 'No model run yet'), ('Latest observation', 'Monthly consultation count')]])], className='m-panel m-span-12 m-kpi-strip'),
            section('Monthly consultation trend', [empty_state('No observations available', 'Activate a dataset to view the monthly trend.')], className='m-panel m-span-12')], className='m-layout-grid')]
    return [section('Get started with monthly data', [state]), provenance()]


def page_content(store, user, page, dataset, code, horizon=12, notification_status='all', notification_type='all', history_window='recent'):
    notice = [message(PUBLIC_NOTICE, 'warning')] if dataset and store.is_prototype and page in (
        'Dashboard', 'Forecasting', 'Model Performance & Insights', 'Reports') else []
    content = _page_content(store, user, page, dataset, code, horizon, notification_status, notification_type, history_window)
    if page != 'Forecasting' or not dataset:
        content.append(html.Div(chart_controls(horizon, history_window, disabled=True), hidden=True))
    return [html.Div(notice + content, **{'data-page': page})]


def _page_content(store, user, page, dataset, code, horizon=12, notification_status='all', notification_type='all', history_window='recent'):
    if page == 'Help & About':
        panels = [section('About this study', [html.P('Monthly infectious-disease consultation trends among individuals aged 5–19 in Antipolo City, Rizal.'),
            html.P('Each grouped ICD-10 block is one analytical unit. Its counts cannot be split into individual diseases.')]), section('How reporting and data quality work', [
                html.P('All seven historically represented ICD-10 blocks undergo data-quality assessment and Prophet + XGBoost modeling using available monthly observations. Explicit zeros are observations.'),
                html.P('Available years: ' + ', '.join(map(str, AVAILABLE_YEARS)) + '. City reports for 2020 and 2022 are unavailable and excluded from the denominator.'),
                html.P('Technical model outcomes are recorded for every candidate; coverage does not exclude a block from modeling.')]),
            section('Using the application', [html.Ol([html.Li('Upload a canonical monthly CSV or XLSX in Data & Quality. Review the upload before Confirm & Activate.'),
                html.Li('Use the disease-group filter across pages. Overall rankings always cover all forecasted groups. Shaded chart bands identify months not reported.'),
                html.Li('Use Reports to download printable HTML, research data (JSON) or CSV values with availability labels.'),
                html.Li('Read Notifications for updates. Administrators manage authorized users through the Account menu.')])]),
            section('Glossary', [html.Dl([html.Div([html.Dt(term), html.Dd(text)]) for term, text in [
                ('ICD-10 block', 'A group of related diagnosis codes; the study analyzes each block as one unit.'),
                ('Observed zero', 'A report explicitly recorded zero consultations; this is different from missing data.'),
                ('MAE', 'Mean absolute error: the average size of prediction errors, in consultations.'),
                ('RMSE', 'Root mean squared error: an error measure in consultations that gives more weight to large misses.'),
                ('MASE', 'Mean absolute scaled error: error relative to a training-data reference; unavailable when that reference scale is undefined.')]])]),
            section('Forecasting methodology', [message('Final research results require approved methodology. Research forecasts remain provisional.', 'warning'),
                html.P('Prototype mode combines Prophet forecasts with XGBoost residual corrections over twelve future calendar months. Prototype outputs and evaluation are provisional; final thesis results remain blocked.'),
                disclosure('Research decisions awaiting approval', [html.Pre('Pending: chronological residual-training folds; features; tuning; evaluation metrics and splits; gap treatment; uncertainty intervals.')])])]
        return [html.Div([html.Div([*panels[:3], panels[4]], className='m-span-8 m-panel-stack'),
                              html.Div([panels[3], section('Source provenance', [
                                  html.A('View source provenance in Data & Quality', href='/?module=Data%20%26%20Quality')])],
                                  className='m-span-4 m-panel-stack')], className='m-layout-grid m-help-grid')]
    if page == 'Notifications':
        notifications = filtered_notifications(store, user, notification_status, notification_type)
        if not notifications:
            return [section('Activity', [empty_state('No matching notifications', 'Try another filter, or check back after new activity.')])]
        notifications = notification_events(store, user, notifications)
        groups = {}
        for item in notifications:
            groups.setdefault(timestamp(item['created_at']).split(',')[0], []).append(item)
        return [section(day, [html.Article([
            html.Div([html.H4(n['title']), *([html.Span('Unread', className='m-badge')] if not n['read_at'] else [])], className='m-activity-heading'),
            disclosure('View details', [html.P(n['message'])]) if len(n['message'] or '') > 200 else html.P(n['message']),
            html.Div([html.Small(timestamp(n['created_at'])), html.A('Open ' + n['related_module'],
                href='/account' if n['related_module'] == 'Security' else '/?module=' + quote(n['related_module']))], className='m-section-footer')
        ], className='m-activity-item') for n in items]) for day, items in groups.items()]
    if not dataset:
        return no_data(page, user)
    block = next((b for b in dataset['blocks'] if b['icd10_block'] == code), dataset['blocks'][0])
    code = block['icd10_block']
    model_run = store.latest_model_run(dataset['dataset_signature'], code) if page in ('Dashboard', 'Forecasting', 'Model Performance & Insights') else None
    forecast = model_run if model_run and model_run['forecast_status'] == 'hybrid_completed' else None
    summary = [html.P(coverage_text(block), className='m-muted')]
    outcome = message(forecast_outcome(model_run), 'warning' if model_run and not forecast else 'info')
    if page == 'Dashboard':
        latest = next((r for r in reversed(dataset['observations']) if r['icd10_block'] == code and r['consultation_count'] is not None), None)
        estimates = [html.P(f'Showing 3 of {len(forecast["forecast_values"])} months; {max(0, len(forecast["forecast_values"]) - 3)} more are available in Forecasting.'),
            table(forecast['forecast_values'][:3], ['month', 'consultation_count']),
            html.A('View all forecast months', href='/?module=Forecasting'), *forecast_warnings(forecast)] if forecast else [
                empty_state('No completed forecast for the latest model run', 'Open Forecasting to review the latest attempt and available actions.')]
        return [html.Div([
            html.Div(ranking_view(store, dataset), className='m-span-8'),
            html.Div(data_status(dataset, user, model_run), className='m-span-4'),
            section('Selected group at a glance', [block_summary(block, latest)], className='m-panel m-span-12 m-kpi-strip'),
            section('Monthly consultation trend', [trend_chart(dataset, code, forecast),
                disclosure('View observed values', [table([r for r in dataset['observations'] if r['icd10_block'] == code], ['year', 'month', 'consultation_count', 'observation_status'])])],
                'Observed consultations with reporting gaps preserved.', className='m-panel m-span-12'),
            section('Monthly consultation estimates', estimates, className='m-panel m-span-8'),
            section('Data-quality warnings', [quality(dataset), html.P('Available reporting years: ' + ', '.join(map(str, AVAILABLE_YEARS)))], className='m-panel m-span-4')], className='m-layout-grid')]
    if page == 'Disease Trends':
        return [html.Div([section('Monthly consultation trend', [trend_chart(dataset, code),
            html.P('Grey: city reports unavailable. Amber: this group was outside the annual Top Five. Both mean unknown counts. An open diamond marks an explicitly reported zero.', className='m-muted')],
            className='m-panel m-span-12', id='m-trends-chart'),
            section('Annual Top-5 history', [table([
                {**row, 'top5_present': 'Unknown' if row['status'] == 'city_report_unavailable' else row['top5_present']}
                for row in annual_history(dataset, code)])], className='m-panel m-span-5', id='m-annual-history'),
            section('Monthly records', [table([r for r in dataset['observations'] if r['icd10_block'] == code],
                ['year', 'month', 'consultation_count', 'observation_status'])],
                'Recorded values for the selected group. Unavailable counts remain unknown.',
                className='m-panel m-span-7', id='m-monthly-records')], className='m-layout-grid')]
    if page == 'Data & Quality':
        return [provenance(dataset),
            section('Normalized observations', [table(dataset['observations'], ['icd10_block', 'year', 'month', 'consultation_count', 'observation_status'])])]
    if page == 'Forecasting':
        if not forecast:
            return [section('Forecast availability', [*summary, outcome,
                empty_state('No completed forecast for the latest model run',
                'An administrator can generate research estimates for the active dataset.')],
                right=chart_controls(horizon, history_window, disabled=True))]
        horizon = horizon if horizon in (3, 6, 12) else 12
        shown = {**forecast, 'forecast_values': forecast['forecast_values'][:horizon],
                 'baseline_forecast': forecast.get('baseline_forecast', [])[:horizon]}
        values = shown['forecast_values']
        return [html.Div([section('Saved forecast · active dataset', [
            html.P(f'Last generated: {timestamp(forecast["forecast_created_at"])} · Forecast period: {forecast["forecast_values"][0]["month"]} to {forecast["forecast_values"][-1]["month"]} · showing {horizon} months'),
            html.P('Last observed month: ' + str(forecast.get('training_cutoff') or 'Unavailable')),
            html.P('The displayed estimates belong to the latest completed attempt. Generating again refreshes all seven disease groups.'),
            *forecast_warnings(forecast), trend_chart(dataset, code, shown, focus_forecast=history_window != 'full'),
            html.P('Prediction intervals are not available for this model run. The line shows point estimates only.', className='m-muted')
                if not has_intervals(values) else html.P('The shaded band shows the prediction interval supplied with this run.')],
                right=chart_controls(horizon, history_window), className='m-panel m-span-8', id='m-saved-forecast'),
            section(f'Estimated consultations · first {horizon} forecast months', [table(values, ['month', 'consultation_count']),
                disclosure('Source and calculation details', [html.P('Last observed month: ' + forecast['training_cutoff']),
                    html.P('Forecast run: ' + forecast['forecast_run_id']), html.Code(forecast['dataset_signature'])])],
                className='m-panel m-span-4', id='m-forecast-estimates')], className='m-layout-grid m-forecast-grid')]
    if page == 'Model Performance & Insights':
        details = ({k: forecast.get(k) for k in ('forecast_run_id', 'model_label', 'n_observations',
                    'horizon_months', 'model_metadata', 'evaluation', 'warnings')} if forecast else {'status': 'not_available'})
        if user['role'] != 'admin':
            details.pop('model_metadata', None)
        return [outcome, *performance_comparison(forecast), section('Research details', [
            *forecast_warnings(forecast),
            disclosure('Chronological evaluation and run details', [html.Pre(json.dumps(details, indent=2))]),
            *([] if forecast else [message(readable_text(METHOD_PENDING), 'warning')])])]
    return [section('Report scope', [html.P('Selected group: ' + code + ' · ' + disease_label(block['icd10_description'])),
        html.P('HTML and JSON include this group’s history, latest model attempt and evaluation, plus overall rankings across all compatible forecasted groups. CSV contains only the selected group’s historical and available forecast values.'),
        html.P('Exports use the active dataset and saved results; the chart window does not limit exported months.')])]


def forecast_warnings(forecast):
    if not forecast:
        return []
    return [disclosure('Research methods and limitations',
        [html.Ul([html.Li(w) for w in forecast.get('warnings', [])])])]


def ranking_view(store, dataset):
    ranking = RankingRepository(store).latest(dataset['dataset_signature'])
    title = 'Projected Top Five' if ranking and ranking.get('top_five_status') == 'available' else 'Projected ranking'
    months = ranking.get('forecast_months', []) if ranking else []
    period = 'Forecast period unavailable'
    if months:
        start, end = (datetime.fromisoformat(month[:7] + '-01') for month in (months[0], months[-1]))
        years = str(start.year) if start.year == end.year else f'{start.year}–{end.year}'
        title += ' · ' + years
        period = (start.strftime('%b') if start.year == end.year else start.strftime('%b %Y')) + ' to ' + end.strftime('%b %Y')
    header = title
    props = dict(className='m-panel m-ranking-card', variant='featured', right=badge('Provisional', 'warning') if store.is_prototype else None)
    subtitle = RANKING_SCOPE + ' Overall ranking; independent of the selected disease group.'
    if ranking:
        subtitle += f' Last generated: {timestamp(ranking["generated_at"])}'
    if not ranking:
        return section(header, [empty_state('No projected ranking yet',
            'Generate forecasts to compare the disease groups over twelve months after the dataset endpoint.')], subtitle, **props)
    names = {b['icd10_block']: b['icd10_description'] for b in dataset['blocks']}
    rows = ranking['top_five'] or ranking['rankings']
    count = len(ranking['rankings'])
    return section(header, [
        html.P('Estimated consultations, ' + period, className='m-ranking-units'),
        *([] if ranking['top_five'] else [message(
            f'Incomplete ranking: {count} valid forecasts; at least five are needed for a Projected Top Five.', 'warning'),
            html.P('Review the failed groups in Forecasting before generating again.')]),
        ranked_list(rows, names) if rows else empty_state('No valid projected totals', 'Review the failed groups in Forecasting before generating again.'),
        *[message(w, 'warning') for w in ranking['warnings'] if not w.startswith('Projected Top Five unavailable:')
          and (ranking['top_five'] or w != 'Some block forecasts failed; this ranking is incomplete.')],
        *([disclosure(f'All projected totals ({count} groups)', [ranked_list(ranking['rankings'], names)])] if ranking['top_five'] else []),
        disclosure(f'Calculation details ({count} groups)', [html.P('Ranking batch: ' + ranking['forecast_run_group_id']),
            table(ranking['rankings'], ['icd10_block', 'forecast_run_id']), html.P(ranking['tie_rule']),
            html.P('Displayed totals are rounded; rankings use unrounded values.')])], subtitle, **props)


def performance_comparison(forecast):
    evaluation = (forecast or {}).get('evaluation', {})
    if evaluation.get('status') != 'completed':
        return [section('Evaluation summary', [empty_state('No evaluation available',
            evaluation.get('reason', 'Generate a completed forecast before reviewing evaluation results.'))])]
    figure = evaluation_figure(evaluation)
    scores = evaluation['hybrid']
    improvement = evaluation['mae_improvement']
    result = 'Residual correction reduced average absolute error.' if improvement > 0 else 'Residual correction increased average absolute error.' if improvement < 0 else 'Residual correction left average absolute error unchanged.'
    return [section('Evaluation summary', [message(result + f' MAE improvement from correction: {format_number(improvement, "mae_improvement")} consultations.'),
            metric_grid([metric_card(label, format_number(scores.get(key), key), detail) for label, key, detail in [
                ('Mean absolute error', 'mae', 'MAE: average absolute error in consultations; lower is better.'),
                ('Root mean squared error', 'rmse', 'RMSE: error in consultations, with greater weight on large misses.'),
                ('Scaled absolute error', 'mase', 'MASE: error relative to a training-data reference scale.')]
                if scores.get(key) is not None]),
            *([html.P('MASE is unavailable because the training-data reference scale is undefined.', className='m-muted')] if scores.get('mase') is None else [])],
            className='m-panel m-kpi-strip m-performance-summary'),
            html.Div([section('Observed consultations and held-out predictions', [dcc.Graph(figure=figure, responsive=True, config={'displaylogo': False})],
                className='m-panel m-span-8', id='m-performance-chart'),
            section('Model comparison', [table([dict(model='Prophet baseline', **evaluation['prophet']), dict(model='Hybrid research forecast', **scores)]),
            disclosure('View comparison values', [table([
                dict(month=month, observed=actual, prophet_baseline=base, hybrid_forecast=hybrid)
                for month, actual, base, hybrid in zip(evaluation['test_months'], evaluation['actual'],
                                                      evaluation['prophet_predictions'], evaluation['hybrid_predictions'])])])],
                className='m-panel m-span-4', id='m-performance-comparison')], className='m-layout-grid m-performance-grid')]


def filtered_notifications(store, user, status='all', kind='all'):
    return [n for n in store.notifications(user)
            if (status == 'all' or status == 'unread' and not n['read_at'] or status == 'read' and n['read_at'])
            and (kind == 'all' or n['type'] == kind)]


def notification_events(store, user, visible):
    """Group only explicit run links or coverage emitted after an activation."""
    coverage = {}
    activation = None
    for item in reversed(store.notifications(user)):
        if item['type'] == 'dataset' and item['title'] == 'Dataset activated':
            activation = item['id']
        if item['type'] == 'data_quality' and 'Reporting coverage' in item['title'] and activation:
            coverage[item['id']] = ('coverage', activation)
    events = {}
    with store.connect() as db:
        for item in visible:
            key = coverage.get(item['id'], ('single', item['id']))
            text = notification_text(store, item)
            title = item['title']
            if key[0] == 'coverage':
                title = 'Dataset reporting coverage'
                text = item['title'] + ': ' + text
            if item['type'] == 'forecast' and item.get('related_record_id'):
                ref = item['related_record_id']
                row = db.execute('SELECT payload FROM forecasts WHERE id=?', (ref,)).fetchone()
                ranking = False
                if not row:
                    row = db.execute('SELECT payload FROM rankings WHERE id=?', (ref,)).fetchone()
                    ranking = True
                if row:
                    result = json.loads(row[0])
                    key = ('forecast', result['forecast_run_group_id'])
                    title = 'Forecast run'
                    if ranking:
                        title += f': {len(result["rankings"])} completed, {len(result.get("failed_blocks", []))} failed'
                        text = 'Completed blocks: ' + ', '.join(r['icd10_block'] for r in result['rankings']) + '. Failed blocks: ' + (', '.join(result.get('failed_blocks', [])) or 'None') + '.'
                    else:
                        text = result['icd10_block'] + ': ' + forecast_outcome(result)
            if key not in events:
                events[key] = {**item, 'title': title, 'message': text}
            else:
                event = events[key]
                event['message'] += '\n' + text
                event['read_at'] = event['read_at'] if item['read_at'] else None
    return list(events.values())


def notification_text(store, item):
    text = item['message'] or ''
    if item['type'] == 'security' and item['title'] == 'Authorized account created' and ' ' not in text:
        return f'Account “{text}” was created.'
    if item['type'] == 'security' and text.startswith('Account ') and text[8:].isdigit():
        with store.connect() as db:
            row = db.execute('SELECT username FROM users WHERE id=?', (int(text[8:]),)).fetchone()
        return f'Permissions for account “{row[0]}” were updated.' if row else 'Account permissions were updated.'
    if item['type'] == 'forecast':
        for status in ('xgboost_insufficient_history', 'xgboost_failed', 'prophet_failed', 'forecast_failed'):
            text = text.removeprefix(status + ': ')
    return readable_text(text)


def grouped_failures(store, dataset, batch=None):
    """Group identical saved causes without inferring a cause from coverage."""
    groups = {}
    for block in dataset['blocks']:
        code = block['icd10_block']
        run = store.latest_model_run(dataset['dataset_signature'], code)
        if not run or run.get('forecast_status') in ('running', 'hybrid_completed'):
            continue
        if batch and run.get('forecast_run_group_id') != batch['id']:
            continue
        groups.setdefault(forecast_outcome(run), []).append(code)
    return [', '.join(codes) + ': ' + cause for cause, codes in groups.items()]
