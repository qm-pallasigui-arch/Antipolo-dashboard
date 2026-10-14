"""Independent Reporting page and PDF download callbacks."""
import plotly.graph_objects as go
from dash import Input, Output, State, dcc, html, no_update, ctx

from dashboard.app_instance import app
from dashboard.weekly.reporting import build_report, report_pdf, weekly_cells
from dashboard.weekly.presentation import notice


def layout():
    return html.Section(id='w-reporting', style={'display': 'none'}, children=[
        dcc.Store(id='w-report-payload'), dcc.Download(id='w-report-download'),
        html.Div(className='report-controls dashboard-panel', children=[
            html.Div([html.Label('Report disease', htmlFor='w-report-disease'),
                      dcc.Dropdown(id='w-report-disease', clearable=False)]),
            html.Div([html.Label('Report outlook', htmlFor='w-report-horizon'),
                      dcc.RadioItems(id='w-report-horizon', options=[{'label': f'{n} weeks', 'value': n} for n in (4, 13, 26, 52)],
                                     value=4, inline=True, className='choice-row')]),
            html.Div([html.Button('Generate Report', id='w-report-generate', n_clicks=0),
                      html.Button('Export PDF', id='w-report-pdf', n_clicks=0, disabled=True, className='secondary')], className='actions'),
            html.P('Uses the existing Hybrid forecast for the selected disease. Suggested actions are for city health officer review.', className='muted'),
            html.Button('Open Forecast', className='secondary', **{'data-app-page': 'Forecast'}),
        ]),
        html.Div(id='w-report-export-status', role='status'),
        dcc.Loading(html.Div(id='w-report-body', children=notice('Choose a disease and generate a report.')), type='circle'),
    ])


def report_view(report):
    figure = go.Figure(go.Scatter(x=[r['week'] for r in report['rows']], y=[r['cases'] for r in report['rows']],
                                 mode='lines+markers', name='Projected cases', line={'color': '#185FA5'}))
    figure.add_hline(y=report['baseline'], line_dash='dash', line_color='#b45309', annotation_text='Latest complete week baseline')
    figure.update_layout(template='plotly_white', height=330, margin={'l': 45, 'r': 30, 't': 35, 'b': 80}, yaxis_title='Cases', xaxis_title='Reporting week')
    head = ['Week', 'Projected cases', 'Case change', '% change', 'Comparison']
    return html.Article(className='report-briefing', children=[
        html.Div(className='dashboard-panel', children=[html.P('CITY HEALTH OFFICER BRIEFING', className='card-label'),
            html.H2(f"{report['disease']} — {report['horizon']}-week outlook"),
            html.P(f"{report['location']} | Population: {report['population']} | {report['classification']} cases"),
            html.P(f"Prepared {report['generated_at']} | {report['context']}"),
            html.P(f"Source: {report['source_file']} | Source date: {report['source_date']}"),
            html.P(f"Forecast issued: {report['issued_at']} | Model protocol: {report['configuration']}"),
            html.H3('Executive summary'), html.P(report['summary']),
            html.P('Above-baseline projections are not outbreak declarations.', className='muted')]),
        html.Div(className='dashboard-panel', children=[html.H3('Weekly outlook'),
            html.P(f"Fixed comparison: {report['baseline_week']} — {report['baseline']:g} observed cases. Values rounded for display."),
            dcc.Graph(id='w-report-chart', figure=figure, style={'height': '330px'}, config={'displaylogo': False}),
            html.Div(html.Table([html.Thead(html.Tr([html.Th(x, scope='col') for x in head])),
                html.Tbody([html.Tr([html.Td(x) for x in cells], className='report-increase' if row['change'] > 0 else '')
                            for row, cells in zip(report['rows'], weekly_cells(report))])]), className='report-table'),
            html.H3('Interpretation by period'), *[html.P(x) for x in report['blocks']]]),
        html.Div(className='dashboard-panel', children=[html.H3('Recommendations and suggested intervention plan'),
            *[html.Section(className='report-action', children=[html.H4(f'Action {i}'), html.P(action['finding']), html.P(action['activity']),
                html.Dl([html.Div([html.Dt(label), html.Dd(action[key])]) for key, label in
                         [('owner', 'Proposed team'), ('timing', 'Timing'), ('indicator', 'Follow-up indicator'), ('reference', 'Basis')]])])
              for i, action in enumerate(report['actions'], 1)]]),
        html.Div(className='dashboard-panel', children=[html.H3('Evidence and limitations'),
            html.Ul([html.Li(x) for x in report['limitations']]), html.H3('References'),
            *[html.P([f'[{i}] ', html.A(s['title'], href=s['url'], target='_blank', rel='noopener noreferrer')])
              for i, s in enumerate(report['sources'], 1)],
            *([] if report['sources'] else [html.P('No verified disease-specific reference configured.')])]),
    ])


@app.callback(Output('w-reporting', 'style'), Input('w-page', 'value'))
def visibility(page):
    return {} if page == 'Reporting' else {'display': 'none'}


@app.callback(Output('w-report-disease', 'options'), Output('w-report-disease', 'value'),
              Input('w-active', 'data'), State('w-report-disease', 'value'), State('w-disease', 'value'))
def diseases(active, selected, current):
    names = (active or {}).get('quality', {}).get('diseases', [])
    return names, selected if selected in names else current if current in names else next(iter(names), None)


@app.callback(Output('w-report-body', 'children'), Output('w-report-payload', 'data'), Output('w-report-pdf', 'disabled'),
              Input('w-report-generate', 'n_clicks'), Input('w-active', 'data'), Input('w-result', 'data'),
              Input('w-report-disease', 'value'), Input('w-report-horizon', 'value'))
def generate(clicks, active, results, disease, horizon):
    if ctx.triggered_id != 'w-report-generate':
        return notice('Choose Generate Report to prepare or refresh the briefing for the current data, disease and outlook.'), None, True
    try:
        report = build_report(active, (results or {}).get(disease), disease, horizon)
    except ValueError as exc:
        return notice(str(exc)), None, True
    return report_view(report), report, False


@app.callback(Output('w-report-download', 'data'), Output('w-report-export-status', 'children'),
              Input('w-report-pdf', 'n_clicks'), State('w-report-payload', 'data'), State('w-active', 'data'),
              State('w-result', 'data'), State('w-report-disease', 'value'), State('w-report-horizon', 'value'),
              prevent_initial_call=True)
def download(clicks, report, active, results, disease, horizon):
    try:
        current = build_report(active, (results or {}).get(disease), disease, horizon)
        if not report or any(report.get(k) != current.get(k) for k in current if k != 'generated_at'):
            raise ValueError('This report is outdated. Generate Report again before exporting.')
        payload = report_pdf(report)
    except ValueError as exc:
        return no_update, notice(str(exc))
    return dcc.send_bytes(payload, f"disease-outlook-{horizon}-weeks.pdf"), 'PDF prepared.'
