"""Shared, presentation-only components for every monthly module."""
from datetime import datetime, timedelta, timezone
from numbers import Real

from dash import dcc, html

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


def confirm_action(label, identity, explanation, variant='primary', disabled=False):
    return dcc.ConfirmDialogProvider(id=identity, message=explanation,
        children=button(label, identity + '-button', variant=variant, disabled=disabled))


def badge(label, tone='neutral', description=None):
    symbol = {'success': '✓', 'warning': '!', 'error': '!', 'info': 'i'}.get(tone, '○')
    return html.Span([html.Span(symbol, **{'aria-hidden': 'true'}), ' ' + label],
        className=f'm-badge m-badge--{tone}', title=description or label, tabIndex=0)


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
    if isinstance(value, Real):
        return format_number(value, key)
    return value


def format_number(value, key=''):
    if value is None:
        return 'Unavailable'
    if key in ('mae', 'rmse', 'mase', 'mae_improvement'):
        return f'{value:,.3f}' if abs(value) >= .001 or value == 0 else '<0.001' if value > 0 else '>-0.001'
    if key in ('projected_total', 'forecast_value'):
        return f'{value:,.1f}'
    if key == 'year':
        return str(int(value))
    return f'{value:,.0f}' if float(value).is_integer() else f'{value:,.1f}'


def table(rows, columns=None):
    if not rows:
        return empty_state('No records yet', 'Records will appear here when they are available.')
    columns = columns or list(rows[0])
    labels = {'icd10_block': 'ICD-10 block', 'icd10_description': 'Disease group', 'eligible': 'Forecast readiness',
              'top5_year_count': 'Years reported', 'required_top5_year_count': 'Available years', 'reason': 'Data availability',
              'projected_total': 'Consultations · next 12 months', 'consultation_count': 'Consultations',
              'mae': 'MAE', 'rmse': 'RMSE', 'mase': 'MASE', 'disease_group': 'Disease group',
              'forecast_value': 'Estimated consultations', 'rank': 'Rank'}
    numeric = [k for k in columns if any(isinstance(r.get(k), Real) and not isinstance(r.get(k), bool) for r in rows)]
    return html.Div(html.Table([
        html.Thead(html.Tr([html.Th(html.Button([
            labels.get(k, k.replace('_', ' ').capitalize()), html.Span(' ↕', **{'aria-hidden': 'true'})],
            type='button', className='m-sort-button', **{'data-column': str(index),
                'data-sort-kind': 'number' if k in numeric else 'text',
                'aria-label': 'Sort by ' + labels.get(k, k.replace('_', ' '))}),
            scope='col', **{'aria-sort': 'none'}) for index, k in enumerate(columns)])),
        html.Tbody([html.Tr([html.Td(display_value(row.get(k), k),
            className='m-numeric' if k in numeric else '',
            **{'data-sort-value': '' if row.get(k) is None else str(row.get(k))}) for k in columns]) for row in rows])
    ], className='m-data-table'), className='m-table', tabIndex=0, role='region', **{'aria-label': 'Scrollable data table'})
