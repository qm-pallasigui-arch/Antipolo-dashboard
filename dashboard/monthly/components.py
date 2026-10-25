"""Shared, presentation-only components for every monthly module."""
from datetime import datetime, timedelta, timezone
from numbers import Real

from dash import dash_table, dcc, html

FONT = 'Segoe UI, system-ui, -apple-system, sans-serif'
STATUS_LABELS = {
    'observed': 'Observed count', 'observed_zero': 'Reported zero',
    'city_report_unavailable': 'Reporting unavailable', 'outside_annual_top5': 'Outside annual Top 5',
    'forecast': 'Forecasted consultations', 'reported': 'Reported',
}


def button(label, identity=None, variant='primary', **props):
    if identity:
        props['id'] = identity
    return html.Button(label, className=f'm-button m-button--{variant}', **props)


def confirm_action(label, identity, explanation, variant='primary'):
    return dcc.ConfirmDialogProvider(id=identity, message=explanation, children=button(label, variant=variant))


def badge(label, tone='neutral'):
    return html.Span(label, className=f'm-badge m-badge--{tone}')


def message(text, tone='info', title=None):
    symbols = {'info': 'i', 'success': '✓', 'warning': '!', 'error': '!'}
    return html.Div([html.Span(symbols.get(tone, 'i'), className='m-notice-icon', **{'aria-hidden': 'true'}),
        html.Div(([html.Strong(title)] if title else []) + [html.Div(text)])],
        className=f'm-notice m-notice--{tone}', role='alert' if tone == 'error' else 'status')


def section(title, children, description=None, **props):
    return html.Section([html.Div([html.H3(title), *([html.P(description)] if description else [])],
                                 className='m-section-heading'), *children], className='m-panel', **props)


def metric_card(label, value, detail=None):
    return html.Div([html.Span(label, className='m-metric-label'), html.Strong(value, className='m-metric-value'),
                     *([html.Small(detail)] if detail else [])], className='m-metric')


def metric_grid(cards):
    return html.Div(cards, className='m-metric-grid')


def empty_state(title, description, action=None):
    return html.Div([html.Span('○', className='m-empty-icon', **{'aria-hidden': 'true'}), html.H3(title),
                     html.P(description), *([action] if action else [])], className='m-empty')


def page_heading(title, description):
    return html.Div([html.H2(title), html.P(description)], className='m-page-heading')


def disclosure(title, children):
    return html.Details([html.Summary(title), html.Div(children, className='m-disclosure-body')], className='m-disclosure')


def timestamp(value):
    if not value:
        return 'Not available'
    try:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo:
            return parsed.astimezone(timezone(timedelta(hours=8))).strftime('%d %b %Y, %I:%M %p PHT')
        return parsed.strftime('%d %b %Y')
    except (ValueError, TypeError):
        return str(value)


def display_value(value, key=''):
    if value is None:
        return 'Unknown / unavailable'
    if isinstance(value, bool):
        if key == 'eligible':
            return 'Forecast eligible' if value else 'Not eligible for forecasting'
        return 'Yes' if value else 'No'
    if isinstance(value, list):
        return ', '.join(map(str, value)) or 'None'
    if key in ('observation_status', 'status'):
        return STATUS_LABELS.get(value, value)
    return value


def table(rows, columns=None):
    if not rows:
        return empty_state('No records yet', 'Records will appear here when they are available.')
    columns = columns or list(rows[0])
    labels = {'icd10_block': 'ICD-10 block', 'icd10_description': 'Description', 'eligible': 'Forecast eligibility',
              'top5_year_count': 'Top-5 years', 'required_top5_year_count': 'Available years', 'reason': 'Eligibility reason'}
    numeric = [k for k in columns if any(isinstance(r.get(k), Real) and not isinstance(r.get(k), bool) for r in rows)]
    return html.Div(dash_table.DataTable(
        data=[{k: display_value(r.get(k), k) for k in columns} for r in rows],
        columns=[{'name': labels.get(k, k.replace('_', ' ').capitalize()), 'id': k} for k in columns],
        page_size=12, sort_action='native', style_table={'overflowX': 'auto'},
        style_cell={'textAlign': 'left', 'whiteSpace': 'normal', 'height': 'auto', 'minWidth': '100px',
                    'maxWidth': '400px', 'padding': '12px 14px', 'fontFamily': FONT, 'fontSize': '14px',
                    'color': '#17324d', 'border': '1px solid #e3eaf0'},
        style_cell_conditional=[{'if': {'column_id': k}, 'textAlign': 'right', 'fontVariantNumeric': 'tabular-nums'} for k in numeric],
        style_header={'backgroundColor': '#f1f6f8', 'fontWeight': '600', 'fontSize': '12px'},
        style_data_conditional=[{'if': {'filter_query': '{observation_status} = "' + label + '"'},
                                 'backgroundColor': color} for label, color in [('Reporting unavailable', '#f0f3f7'),
                                                                             ('Outside annual Top 5', '#fff8eb')]],
    ), className='m-table')
