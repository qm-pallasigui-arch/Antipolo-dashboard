"""Module views composed from the shared monthly component library."""
import json
from urllib.parse import quote

from dash import dcc, html

from .charts import trend_figure
from .components import (badge, disclosure, empty_state, message, metric_card,
                         metric_grid, section, table, timestamp)
from .domain import AVAILABLE_YEARS, LIMITATIONS, PROVENANCE, annual_history
from .forecast import METHOD_PENDING

DESCRIPTIONS = {
    'Dashboard': 'A clear view of monthly consultations, reporting coverage and forecast readiness.',
    'Disease Trends': 'Explore all historically reported ICD-10 blocks and their data availability.',
    'Forecasting': 'View monthly consultation estimates for eligible ICD-10 blocks.',
    'Model Performance & Insights': 'Review model selection, evaluation evidence and limitations.',
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
    return dcc.Graph(figure=trend_figure(dataset, code, forecast), config={'displaylogo': False, 'responsive': True})


def block_summary(block, latest=None):
    cards = [metric_card('Annual Top-5 recurrence', f'{block["top5_year_count"]} / 8', 'Available reporting years'),
             metric_card('Reported monthly observations', f'{block["reported_month_count"]} / 96', 'Reported zeros are included'),
             metric_card('Forecast eligibility', badge('Forecast eligible' if block['eligible'] else 'Not eligible for forecasting',
                                                      'success' if block['eligible'] else 'warning'), 'Based on reporting coverage')]
    if latest is not None:
        cards.append(metric_card('Latest observation', f'{latest["consultation_count"]:,}', f'{latest["month"]} {latest["year"]} consultations'))
    return metric_grid(cards)


def quality(dataset):
    return disclosure(f'Data-quality warnings ({len(dataset["warnings"])})',
                      [html.Ul([html.Li(w) for w in dataset['warnings']])])


def data_status(dataset, user, forecast=None):
    return section('Data status', [badge('Dataset active' if dataset else 'No dataset loaded', 'success' if dataset else 'neutral'),
        html.P('Reported zeros remain valid observations. Unavailable counts are never converted to zero.'),
        html.H4('Forecast availability'), html.P('Forecast available' if forecast else 'Not available yet'),
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
            ('Forecast eligibility', 'Requires a validated dataset'), ('Latest observation', 'Monthly consultation count')]]),
            html.Div([section('Monthly consultation trend', [state]), data_status(None, user)], className='m-overview-grid')]
    return [section('Get started with monthly data', [state]), provenance()]


def page_content(store, user, page, dataset, code, horizon=12):
    if page == 'Help & About':
        return [section('About this study', [html.P('Monthly infectious-disease consultation trends among individuals aged 5–19 in Antipolo City, Rizal.'),
            html.P('Each grouped ICD-10 block is one analytical unit. Its counts cannot be split into individual diseases.'), message(LIMITATIONS)]),
            provenance(dataset), section('How reporting and eligibility work', [
                html.P('A block must appear in all eight available annual Top-5 reports and contain 96 reported monthly observations to qualify for primary forecasting. Explicit zeros count.'),
                html.P('Available years: ' + ', '.join(map(str, AVAILABLE_YEARS)) + '. City reports for 2020 and 2022 are unavailable and excluded from the denominator.'),
                html.P('All historically reported blocks remain available for descriptive analysis, even when they are not eligible for forecasting.')]),
            section('Using the application', [html.Ol([html.Li('Upload a canonical monthly CSV or XLSX in Data & Quality. Review the candidate before Confirm & Activate.'),
                html.Li('Select an ICD-10 block in Dashboard or Disease Trends. Shaded gaps distinguish unavailable reports from outside-Top-5 coverage.'),
                html.Li('Use Reports to download printable HTML, JSON evidence or CSV values with availability labels.'),
                html.Li('Read Notifications for updates. Administrators manage authorized users through the Account menu.')])]),
            section('Forecasting methodology', [message(METHOD_PENDING, 'warning'),
                html.P('No forecasting engine is installed. Once approved, forecasts will estimate monthly consultations 1–12 months ahead.'),
                disclosure('Research decisions awaiting approval', [html.Pre('TODO THESIS-METHOD: models; ensemble design; selection rule; metrics; chronological validation; treatment of 2020/2022 in fitting; uncertainty intervals.')])])]
    if page == 'Notifications':
        notifications = store.notifications(user)
        if not notifications:
            return [section('Activity', [empty_state('You’re all caught up', 'Dataset updates and report notifications will appear here.')])]
        return [section(n['title'], [badge('Unread' if not n['read_at'] else 'Read', 'info' if not n['read_at'] else 'neutral'),
            message(n['message'], n['severity'] if n['severity'] in ('warning', 'error', 'success') else 'info'),
            html.Div([html.Small(timestamp(n['created_at'])), html.A('Open ' + n['related_module'],
                href='/account' if n['related_module'] == 'Security' else '/?module=' + quote(n['related_module']))], className='m-section-footer')]) for n in notifications]
    if not dataset:
        return no_data(page, user)
    block = next((b for b in dataset['blocks'] if b['icd10_block'] == code), dataset['blocks'][0])
    code = block['icd10_block']
    forecast = store.latest_forecast(dataset['dataset_signature'], code)
    heading = [html.Div([html.Span(code, className='m-block-code'), html.H3(block['icd10_description'])], className='m-block-heading')]
    summary = [block_summary(block), message(block['reason'], 'info' if block['eligible'] else 'warning')]
    if page == 'Dashboard':
        latest = next(r for r in reversed(dataset['observations']) if r['icd10_block'] == code and r['consultation_count'] is not None)
        return [*heading, block_summary(block, latest), html.Div([
            section('Monthly consultation trend', [trend_chart(dataset, code, forecast)], 'Observed consultations with reporting gaps preserved.'),
            data_status(dataset, user, forecast)], className='m-overview-grid'),
            message(block['reason'], 'info' if block['eligible'] else 'warning'), quality(dataset),
            *([section('Latest forecast', [table(forecast['forecast_values'][:3])])] if forecast else []),
            html.P('Available reporting years: ' + ', '.join(map(str, AVAILABLE_YEARS)), className='m-muted')]
    if page == 'Disease Trends':
        return [*heading, *summary, section('Monthly consultation trend', [trend_chart(dataset, code),
            html.P('Reported zero uses an open diamond. Shaded periods represent unknown counts; gaps are never connected.', className='m-muted')]),
            section('Annual Top-5 history', [table(annual_history(dataset, code))]),
            section('Monthly records', [table([r for r in dataset['observations'] if r['icd10_block'] == code],
                                             ['year', 'month', 'consultation_count', 'observation_status'])])]
    if page == 'Data & Quality':
        return [section('Coverage and eligibility', [table(dataset['blocks'], ['icd10_block', 'icd10_description', 'top5_year_count',
            'required_top5_year_count', 'reported_month_count', 'eligible', 'reason']), quality(dataset),
            disclosure('Missing periods by block', [table(dataset['blocks'], ['icd10_block', 'missing_years', 'missing_months'])])],
            'All historically reported blocks remain available for descriptive analysis.'), provenance(dataset),
            section('Researcher notes / source annotations', [table(store.notes(dataset['dataset_signature']))]),
            section('Normalized observations', [table(dataset['observations'], ['icd10_block', 'year', 'month', 'consultation_count', 'observation_status'])])]
    if page == 'Forecasting':
        if not block['eligible']:
            return [*heading, *summary, section('Primary forecast unavailable', [empty_state('Not eligible for forecasting', block['reason'],
                html.A('Review Disease Trends', href='/?module=Disease%20Trends', className='m-button m-button--secondary'))])]
        if not forecast:
            return [*heading, *summary, section('Forecast availability', [empty_state('Awaiting approved methodology',
                'Monthly forecasts will appear here when an approved model is available.'), message(METHOD_PENDING, 'warning'),
                html.P('The service supports 1–12 monthly forecasts. No values are fabricated while methodology remains open.')])]
        shown = {**forecast, 'forecast_values': forecast['forecast_values'][:horizon]}
        return [*heading, *summary, section('Historical and forecasted consultations', [trend_chart(dataset, code, shown)]),
            section('Forecast values', [table(shown['forecast_values']), html.P(f'Model: {forecast["selected_model"]} · Generated: {timestamp(forecast["forecast_created_at"])}'),
                disclosure('Run provenance', [html.P('Training cutoff: ' + forecast['training_cutoff']), html.Code(forecast['dataset_signature'])])]), message(LIMITATIONS)]
    if page == 'Model Performance & Insights':
        return [*heading, *summary, section('Chronological evaluation', [metric_grid([
            metric_card(f'{h}-month horizon', 'Available' if forecast else 'Not available', 'Evaluation evidence' if forecast else 'Methodology pending') for h in (1, 3, 6, 12)]),
            message('Performance on historical evaluation periods does not guarantee future accuracy.'),
            disclosure('Model and evaluation details', [html.Pre(json.dumps({k: forecast.get(k) for k in ('forecast_run_id', 'candidate_models',
                'selected_model', 'model_selection_reason', 'evaluation_period', 'evaluation_method', 'metric_results', 'warnings')}
                if forecast else {'status': METHOD_PENDING, 'candidate_models': '[TO FINALIZE: candidate model list]',
                                 'metrics': '[TO FINALIZE: final evaluation metrics]'}, indent=2))])])]
    return [*heading, *summary, section('What your report includes', [html.P('Source provenance, historical monthly trend, annual Top-5 recurrence, reporting coverage, data quality, eligibility, forecast availability and limitations.'),
        html.Div([section(title, [html.P(description)]) for title, description in [
            ('HTML report', 'A complete, self-contained report for reading, sharing or printing.'),
            ('JSON evidence', 'A structured snapshot of source observations and available forecast evidence.'),
            ('CSV values', 'Monthly values with explicit observation-state labels; unknown counts remain blank.')]], className='m-report-grid'), message(LIMITATIONS)])]
