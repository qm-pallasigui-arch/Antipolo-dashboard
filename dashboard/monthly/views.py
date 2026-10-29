"""Module views composed from the shared monthly component library."""
import json
from urllib.parse import quote

from dash import dcc, html

from .charts import trend_figure, has_intervals
from .components import (badge, disclosure, empty_state, message, metric_card,
                         metric_grid, section, table, timestamp, format_number)
from .domain import AVAILABLE_YEARS, LIMITATIONS, PROVENANCE, annual_history
from .forecast import METHOD_PENDING
from .forecasting.config import RANKING_SCOPE
from .navigation import PUBLIC_NOTICE
from .repositories.ranking_repository import RankingRepository

DESCRIPTIONS = {
    'Dashboard': 'A clear view of monthly consultations, reporting coverage and forecast readiness.',
    'Disease Trends': 'Explore all historically reported ICD-10 blocks and their data availability.',
    'Forecasting': 'View monthly consultation estimates for eligible ICD-10 blocks.',
    'Model Performance & Insights': 'Review hybrid model evaluation evidence and limitations.',
    'Data & Quality': 'Review source data, reporting coverage and eligibility before activation.',
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


def trend_chart(dataset, code, forecast=None):
    return dcc.Graph(figure=trend_figure(dataset, code, forecast), responsive=True, config={'displaylogo': False, 'responsive': True})


def block_summary(block, latest=None):
    cards = [metric_card('Annual Top-5 recurrence', f'{block["top5_year_count"]} / 8', 'Available reporting years'),
             metric_card('Reported monthly observations', str(block['reported_month_count']), 'Coverage count; reported zeros included'),
             metric_card('Forecast readiness', badge('Ready for research forecast' if block['eligible'] else 'Not ready',
                'success' if block['eligible'] else 'warning', readiness_text(block)), 'Provisional assessment')]
    if latest is not None:
        cards.append(metric_card('Latest observation', f'{latest["consultation_count"]:,}', f'{latest["month"]} {latest["year"]} consultations'))
    return metric_grid(cards)


def readiness_text(block):
    count = block['reported_month_count']
    if not count:
        return 'No reported observations are available for this disease group.'
    if block.get('is_prototype'):
        import re
        match = re.search(r'technical minimum (\d+)', block.get('reason', ''))
        minimum = f'Needs at least {match[1]} months of data to forecast. ' if match else ''
        return f'{minimum}This group has {count} reported months. Readiness is provisional.'
    return 'Research settings must be configured before forecasts can be generated.'


def quality(dataset):
    return disclosure(f'Data-quality warnings ({len(dataset["warnings"])})',
                      [html.Ul([html.Li(w) for w in dataset['warnings']])])


def data_status(dataset, user, forecast=None):
    return section('Data status', [badge('Dataset active' if dataset else 'No dataset loaded', 'success' if dataset else 'neutral'),
        html.P('Reported zeros remain valid observations. Unavailable counts are never converted to zero.'),
        html.H4('Forecast availability'), html.P(forecast.get('model_status', 'not_available').replace('_', ' ').capitalize() if forecast else 'Not available yet'),
        html.H4('Source freshness'), html.Dl([html.Div([html.Dt(label), html.Dd(timestamp(value))]) for label, value in [
            ('Document prepared', PROVENANCE['document_prepared_at']), ('Uploaded', (dataset or {}).get('uploaded_at'))]]),
        html.A('Go to data upload' if user['role'] == 'admin' else 'Review data quality', href='/?module=Data%20%26%20Quality', className='m-button m-button--primary')])


def no_data(page, user):
    action = html.A('Go to data upload', href='/?module=Data%20%26%20Quality', className='m-button m-button--primary') if user['role'] == 'admin' else None
    state = empty_state('No monthly dataset is active', 'Upload and activate a verified monthly dataset to view consultation trends.'
                        if user['role'] == 'admin' else 'An administrator needs to activate the monthly dataset before results can be viewed.', action)
    if page == 'Dashboard':
        return [metric_grid([metric_card(label, 'Not available', detail) for label, detail in [
            ('Annual Top-5 recurrence', 'Available reporting years'), ('Reported monthly observations', 'Reported zeros are included'),
            ('Forecast readiness', 'Requires a validated dataset'), ('Latest observation', 'Monthly consultation count')]]),
            html.Div([section('Monthly consultation trend', [state]), data_status(None, user)], className='m-overview-grid')]
    return [section('Get started with monthly data', [state]), provenance()]


def page_content(store, user, page, dataset, code, horizon=12, notification_status='all', notification_type='all'):
    if page == 'Help & About':
        return [section('About this study', [html.P('Monthly infectious-disease consultation trends among individuals aged 5–19 in Antipolo City, Rizal.'),
            html.P('Each grouped ICD-10 block is one analytical unit. Its counts cannot be split into individual diseases.'), message(LIMITATIONS)]),
            provenance(dataset), section('How reporting and eligibility work', [
                html.P('All seven ICD-10 blocks enter readiness assessment. Coverage is descriptive; approved readiness thresholds have not yet been configured. Explicit zeros are observations.'),
                html.P('Available years: ' + ', '.join(map(str, AVAILABLE_YEARS)) + '. City reports for 2020 and 2022 are unavailable and excluded from the denominator.'),
                html.P('All historically reported blocks remain available for descriptive analysis, even when they are not eligible for forecasting.')]),
            section('Using the application', [html.Ol([html.Li('Upload a canonical monthly CSV or XLSX in Data & Quality. Review the upload before Confirm & Activate.'),
                html.Li('Use the disease-group filter across pages. Overall rankings always cover all forecasted groups. Shaded chart bands identify months not reported.'),
                html.Li('Use Reports to download printable HTML, research data (JSON) or CSV values with availability labels.'),
                html.Li('Read Notifications for updates. Administrators manage authorized users through the Account menu.')])]),
            section('Forecasting methodology', [message(METHOD_PENDING, 'warning'),
                html.P('Prototype mode combines Prophet forecasts with XGBoost residual corrections over twelve future calendar months. Prototype outputs and evaluation are provisional; final thesis results remain blocked.'),
                disclosure('Research decisions awaiting approval', [html.Pre('Pending: readiness thresholds; chronological residual-training folds; features; tuning; evaluation metrics and splits; gap treatment; uncertainty intervals.')])])]
    if page == 'Notifications':
        notifications = filtered_notifications(store, user, notification_status, notification_type)
        if not notifications:
            return [section('Activity', [empty_state('No matching notifications', 'Try another filter, or check back after new activity.')])]
        groups = {}
        for item in notifications:
            groups.setdefault(timestamp(item['created_at']).split(',')[0], []).append(item)
        return [section(day, [html.Article([
            html.Div([html.H4(n['title']), badge('Unread' if not n['read_at'] else 'Read',
                'info' if not n['read_at'] else 'neutral')], className='m-activity-heading'),
            disclosure('View details', [html.P(notification_text(store, n))]) if len(n['message'] or '') > 200 else html.P(notification_text(store, n)),
            html.Div([html.Small(timestamp(n['created_at'])), html.A('Open ' + n['related_module'],
                href='/account' if n['related_module'] == 'Security' else '/?module=' + quote(n['related_module']))], className='m-section-footer')
        ], className='m-activity-item') for n in items]) for day, items in groups.items()]
    if not dataset:
        return no_data(page, user)
    block = next((b for b in dataset['blocks'] if b['icd10_block'] == code), dataset['blocks'][0])
    code = block['icd10_block']
    forecast = store.latest_forecast(dataset['dataset_signature'], code) if block['eligible'] and page in ('Dashboard', 'Forecasting', 'Model Performance & Insights') else None
    heading = [html.Div([html.Span('Selected disease group', className='m-eyebrow'),
        html.H3(code + ' · ' + block['icd10_description'])], className='m-block-heading')]
    summary = [html.P(readiness_text(block), className='m-muted')]
    if page == 'Dashboard':
        latest = next((r for r in reversed(dataset['observations']) if r['icd10_block'] == code and r['consultation_count'] is not None), None)
        return [ranking_view(store, dataset), *heading, block_summary(block, latest), html.Div([
            section('Monthly consultation trend', [trend_chart(dataset, code, forecast)], 'Observed consultations with reporting gaps preserved.'),
            data_status(dataset, user, forecast)], className='m-overview-grid'),
            html.P(readiness_text(block), className='m-muted'), quality(dataset),
            *([section(forecast['model_label'], [table(forecast['forecast_values'][:3]), *forecast_warnings(forecast)])] if forecast else []),
            html.P('Available reporting years: ' + ', '.join(map(str, AVAILABLE_YEARS)), className='m-muted')]
    if page == 'Disease Trends':
        return [*heading, section('Monthly consultation trend', [trend_chart(dataset, code),
            html.P('Grey: city reports unavailable. Amber: this group was outside the annual Top Five. Both mean unknown counts. An open diamond marks an explicitly reported zero.', className='m-muted')]),
            section('Annual Top-5 history', [table(annual_history(dataset, code))]),
            section('Monthly records', [table([r for r in dataset['observations'] if r['icd10_block'] == code],
                                             ['year', 'month', 'consultation_count', 'observation_status'])])]
    if page == 'Data & Quality':
        blocks = [{**b, 'reason': readiness_text(b)} for b in dataset['blocks']]
        return [section('Coverage and readiness', [table(blocks, ['icd10_block', 'icd10_description', 'top5_year_count',
            'reported_month_count', 'readiness_status', 'reason']), quality(dataset),
            disclosure('Missing periods by block', [table(dataset['blocks'], ['icd10_block', 'missing_years', 'missing_months'])])],
            'All historically reported blocks remain available for descriptive analysis.'), provenance(dataset),
            section('Researcher notes / source annotations', [table(store.notes(dataset['dataset_signature']))]),
            section('Normalized observations', [table(dataset['observations'], ['icd10_block', 'year', 'month', 'consultation_count', 'observation_status'])])]
    if page == 'Forecasting':
        if not block['eligible']:
            return [*heading, *summary, section('Forecast unavailable', [empty_state('Not ready for forecasting', readiness_text(block),
                html.A('Review Disease Trends', href='/?module=Disease%20Trends', className='m-button m-button--secondary'))])]
        if not forecast:
            return [*heading, *summary, section('Forecast availability', [empty_state('No forecast has been generated',
                'An administrator can generate research estimates for the active dataset.'), message(PUBLIC_NOTICE, 'warning')])]
        horizon = horizon if horizon in (3, 6, 12) else 12
        shown = {**forecast, 'forecast_values': forecast['forecast_values'][:horizon],
                 'baseline_forecast': forecast.get('baseline_forecast', [])[:horizon]}
        values = shown['forecast_values']
        return [*heading, section('Saved forecast · active dataset', [
            html.P(f'Last generated: {timestamp(forecast["forecast_created_at"])} · 12-month forecast · showing {horizon} months'),
            html.P('These saved estimates remain visible until a new forecast completes. Generating again refreshes all ready disease groups.'),
            *forecast_warnings(forecast), trend_chart(dataset, code, shown),
            html.P('Prediction intervals are not available for this model run. The line shows point estimates only.', className='m-muted')
                if not has_intervals(values) else html.P('The shaded band shows the prediction interval supplied with this run.')]),
            section(f'Estimated consultations · next {horizon} months', [table(values, ['month', 'consultation_count']),
                disclosure('Source and calculation details', [html.P('Last observed month: ' + forecast['training_cutoff']),
                    html.P('Forecast run: ' + forecast['forecast_run_id']), html.Code(forecast['dataset_signature'])])])]
    if page == 'Model Performance & Insights':
        details = ({k: forecast.get(k) for k in ('forecast_run_id', 'model_label', 'n_observations',
                    'horizon_months', 'model_metadata', 'evaluation', 'warnings')} if forecast else {'status': 'not_available'})
        if user['role'] != 'admin':
            details.pop('model_metadata', None)
        return [*heading, section('Forecast accuracy', [
            *performance_comparison(forecast),
            *forecast_warnings(forecast),
            disclosure('Chronological evaluation and run details', [html.Pre(json.dumps(details, indent=2))]),
            *([] if forecast else [message(METHOD_PENDING, 'warning')])])]
    return [*heading, section('What your report includes', [html.P('Historical trends, estimated consultations, overall rankings, data availability and source information.'),
        html.Div([section(title, [html.P(description)]) for title, description in [
            ('HTML report', 'A complete, self-contained report for reading, sharing or printing.'),
            ('Research data (JSON)', 'A structured download for further analysis.'),
            ('CSV values', 'Monthly values with explicit observation-state labels; unknown counts remain blank.')]], className='m-report-grid'), message(LIMITATIONS)])]


def forecast_warnings(forecast):
    if not forecast:
        return []
    return [message(PUBLIC_NOTICE, 'warning'), disclosure('Research methods and limitations',
        [html.Ul([html.Li(w) for w in forecast.get('warnings', [])])])]


def ranking_view(store, dataset):
    ranking = RankingRepository(store).latest(dataset['dataset_signature'])
    if not ranking:
        return section('Overall ranking · Projected Top Five', [html.P('Generate forecasts to compare the disease groups over the next twelve months.')], 'All forecasted disease groups; independent of the selected group below.')
    names = {b['icd10_block']: b['icd10_description'] for b in dataset['blocks']}
    enrich = lambda rows: [{**r, 'disease_group': r['icd10_block'] + ' · ' + names.get(r['icd10_block'], 'Description unavailable')} for r in rows]
    return section('Overall ranking · Projected Top Five' if ranking.get('top_five_status') == 'available' else 'Overall ranking · Projected Top Five unavailable', [
        html.P(f'Last generated: {timestamp(ranking["generated_at"])} · Next 12 months · All forecasted disease groups'),
        *([message(PUBLIC_NOTICE, 'warning')] if ranking.get('is_prototype') else []),
        table(enrich(ranking['top_five']), ['rank', 'disease_group', 'projected_total']) if ranking['top_five'] else html.P('At least five valid forecasts are needed to display the Top Five.'),
        *[message(w, 'warning') for w in ranking['warnings']],
        disclosure('All projected totals', [table(enrich(ranking['rankings']), ['rank', 'disease_group', 'projected_total']), html.P(ranking['tie_rule'])]),
        disclosure('Calculation details', [table(ranking['rankings'], ['icd10_block', 'forecast_run_id']), html.P('Displayed totals are rounded; rankings use unrounded values.')]),
        html.P(RANKING_SCOPE)])


def performance_comparison(forecast):
    evaluation = (forecast or {}).get('evaluation', {})
    if evaluation.get('status') != 'completed':
        return [html.P(evaluation.get('reason', 'No evaluation available.'))]
    import plotly.graph_objects as go
    figure = go.Figure()
    for label, key in [('Observed', 'actual'), ('Prophet baseline', 'prophet_predictions'), ('Hybrid prototype', 'hybrid_predictions')]:
        figure.add_trace(go.Scatter(x=evaluation['test_months'], y=evaluation[key], mode='lines+markers', name=label))
    figure.update_layout(template='plotly_white', xaxis_title='Held-out month', yaxis_title='Consultations', height=360)
    scores = evaluation['hybrid']
    return [metric_grid([metric_card(label, format_number(scores.get(key), key), detail) for label, key, detail in [
                ('Mean absolute error', 'mae', 'Consultations · lower is better'),
                ('Root mean squared error', 'rmse', 'Consultations · lower is better'),
                ('Scaled absolute error', 'mase', 'Unitless · unavailable when the scale is undefined')]]),
            table([dict(model='Prophet baseline', **evaluation['prophet']), dict(model='Hybrid research forecast', **scores)]),
            dcc.Graph(figure=figure, responsive=True, config={'displaylogo': False}),
            html.P(f'MAE improvement from correction: {format_number(evaluation["mae_improvement"], "mae_improvement")} consultations. Positive means lower error than the baseline.')]


def filtered_notifications(store, user, status='all', kind='all'):
    return [n for n in store.notifications(user)
            if (status == 'all' or status == 'unread' and not n['read_at'] or status == 'read' and n['read_at'])
            and (kind == 'all' or n['type'] == kind)]


def notification_text(store, item):
    text = item['message'] or ''
    if item['type'] == 'security' and item['title'] == 'Authorized account created' and ' ' not in text:
        return f'Account “{text}” was created.'
    if item['type'] == 'security' and text.startswith('Account ') and text[8:].isdigit():
        with store.connect() as db:
            row = db.execute('SELECT username FROM users WHERE id=?', (int(text[8:]),)).fetchone()
        return f'Permissions for account “{row[0]}” were updated.' if row else 'Account permissions were updated.'
    return text
