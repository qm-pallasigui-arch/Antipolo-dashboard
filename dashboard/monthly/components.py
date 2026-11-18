"""Shared, presentation-only components for every monthly module."""
from datetime import datetime, timedelta, timezone
from numbers import Real
import re

from dash import dash_table, dcc, html
from dash.dash_table.Format import Format, Group, Scheme

FONT = 'Segoe UI, system-ui, -apple-system, sans-serif'
STATUS_LABELS = {
    'not_run': 'Not run', 'running': 'Forecast in progress',
    'hybrid_completed': 'Forecast completed',
    'xgboost_insufficient_history': 'Insufficient usable history for the forecast workflow',
    'xgboost_failed': 'Residual correction failed', 'prophet_failed': 'Base forecast failed',
    'forecast_failed': 'Forecast failed', 'prophet_only_fallback': 'Base forecast only',
    'observed': 'Observed count', 'observed_zero': 'Reported zero',
    'city_report_unavailable': 'Reporting unavailable', 'outside_annual_top5': 'Outside annual Top 5',
    'forecast': 'Forecasted consultations', 'reported': 'Reported',
}


def readable_text(text):
    """Translate display text only; stored diagnostics retain their original codes."""
    for code, label in STATUS_LABELS.items():
        text = re.sub(r'\b' + re.escape(code) + r'\b', label, text)
    return text.replace('PROTOTYPE_MODE=true', 'research forecasting is enabled')


def forecast_outcome(run):
    if not run:
        return STATUS_LABELS['not_run']
    error = run.get('error')
    if error:
        # The stored detail is more specific than the component status code.
        prefix = run.get('forecast_status', '') + ': '
        return readable_text(error.removeprefix(prefix))
    return STATUS_LABELS.get(run.get('forecast_status'), 'Forecast status unavailable')


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


def section(title, children, description=None, variant='standard', right=None, **props):
    class_name = props.pop('className', 'm-panel')
    return html.Section([html.Div([
        html.Div([html.H3(title), *([html.P(description)] if description else [])], className='m-panel-heading-text'),
        *([html.Div(right, className='m-panel-heading-slot')] if right is not None else [])],
        className='m-section-heading') , *children], className=class_name + ' m-panel--' + variant, **props)


def panel_header_markup(title, level='h2'):
    """Flask adapter for the same standard header classes used by section()."""
    from html import escape
    from markupsafe import Markup
    if level not in ('h1', 'h2', 'h3'):
        raise ValueError('Unsupported heading level')
    return Markup(f'<div class="m-section-heading"><div class="m-panel-heading-text"><{level}>{escape(title)}</{level}></div></div>')


def disease_label(value):
    """Known source-casing alias, used only for live UI presentation."""
    return 'Intestinal infectious diseases' if str(value).casefold() == 'intestinal infectious diseases' else value


def chart_controls(horizon=12, history='recent', disabled=False):
    return html.Div([
        html.Div([html.Fieldset([html.Legend('Months to display'),
            dcc.RadioItems(id='m-horizon', options=[{'label': f'{n} months', 'value': n, 'disabled': disabled} for n in (3, 6, 12)],
                           value=horizon, className='m-segmented')], disabled=disabled),
            html.Fieldset([html.Legend('History shown'),
            dcc.RadioItems(id='m-history-window', options=[{'label': label, 'value': value, 'disabled': disabled} for label, value in
                [('Recent history + forecast', 'recent'), ('Full history', 'full')]], value=history, className='m-segmented')], disabled=disabled)], className='m-chart-groups'),
        html.P('Available when a completed forecast can be displayed.' if disabled else
               'Changes the chart and table below; saved forecasts and rankings remain unchanged.', className='m-muted')], id='m-chart-controls')


def ranked_list(rows, names):
    """Fixed-order presentation; meter values follow the printed, rounded totals."""
    totals = [None if row.get('projected_total') is None else round(row['projected_total']) for row in rows]
    maximum = max((value for value in totals if value is not None), default=0) or 1
    items = []
    for row, total in zip(rows, totals):
        name = disease_label(names.get(row['icd10_block'], 'Description unavailable'))
        printed = format_number(row.get('projected_total'), 'projected_total')
        items.append(html.Li([
            html.Span(str(row['rank']), className='m-ranking-rank', **{'aria-hidden': 'true'}),
            html.Div([html.Span(name, className='m-ranking-name'), ' ',
                      html.Span(row['icd10_block'], className='m-ranking-code')], className='m-ranking-disease'),
            html.Strong(printed, className='m-ranking-value'),
            *([html.Meter(value=total, min=0, max=maximum, className='m-ranking-bar',
                         **{'aria-hidden': 'true'})] if total is not None else [])],
            className='m-ranking-row',
            **{'aria-label': f'Rank {row["rank"]} of {len(rows)}, {name}, {printed} estimated consultations.'}))
    return html.Ol(items, className='m-ranking-list', **{'aria-label': 'Projected disease-group ranking'})


def metric_card(label, value, detail=None):
    return html.Div([html.Span(label, className='m-metric-label'), html.Strong(value, className='m-metric-value'),
                     *([html.Small(detail)] if detail else [])], className='m-metric')


def metric_grid(cards):
    return html.Div(cards, className='m-metric-grid')


def empty_state(title, description, action=None):
    return html.Div([html.Span('○', className='m-empty-icon', **{'aria-hidden': 'true'}), html.H3(title),
                     html.P(description), *([action] if action else [])], className='m-empty')


def page_heading(title, description):
    return html.Div([html.H1(title, tabIndex=-1), html.P(description)], className='m-page-heading')


def application_shell(content, user=None, dataset=None, unread=0, current='Dashboard'):
    """One semantic shell tree for Dash and authenticated Flask pages."""
    from urllib.parse import quote
    from .navigation import NAV_LABELS, ROLE_LABELS
    from .domain import LIMITATIONS
    groups = [('Analyze', ['Dashboard', 'Disease Trends', 'Forecasting', 'Model Performance & Insights']),
              ('Data', ['Data & Quality', 'Reports']), ('Support', ['Help & About'])]
    sidebar = html.Aside([
        html.Div([html.Div([html.Span(), html.Span(), html.Span()], className='m-brand-mark', **{'aria-hidden': 'true'}),
                  html.Div(html.Strong('Antipolo Disease Forecasting'))], className='m-brand'),
        button('Close menu', 'm-menu-close', 'secondary'),
        html.Nav([html.Div([html.P(label, className='m-nav-group-label'), *[
            html.A(NAV_LABELS.get(page, page), href='/?module=' + quote(page), className='m-sidebar-link',
                   **({'aria-current': 'page'} if page == current else {})) for page in pages]], className='m-nav-group')
            for label, pages in groups], **{'aria-label': 'Main navigation'})], id='m-sidebar', className='m-sidebar')
    topbar = html.Header([
        button('Menu', 'm-menu-toggle', 'secondary', **{'aria-expanded': 'false', 'aria-controls': 'm-sidebar'}),
        html.Div([html.Strong('Dataset active' if dataset else 'No dataset loaded', id='m-dataset'),
                  html.Span(dataset['source_file'] if dataset else 'No active dataset', id='m-source-context')], className='m-dataset-context'),
        html.Div([html.A(['Notifications ', html.Span(str(unread), className='m-count')], id='m-notifications-link',
                        href='/?module=Notifications', className='m-header-control',
                        **({'aria-current': 'page'} if current == 'Notifications' else {})),
            html.Details([html.Summary('Account'), html.Div([
                html.Span(f'{user["username"]} · {ROLE_LABELS[user["role"]]}' if user else '', id='m-user'),
                html.A('Security / Accounts', href='/account', id='m-account',
                       **({'aria-current': 'page'} if current == '/account' else {}),
                       style={} if not user or user['role'] == 'admin' else {'display': 'none'}),
                html.A('Sign out', href='/logout', **({'aria-current': 'page'} if current == '/logout' else {}))], className='m-account-menu')], className='m-account')], className='m-header-tools')], className='m-topbar')
    return html.Div([html.A('Skip to content', href='#m-main', className='m-skip-link'), sidebar,
                     html.Div([topbar, html.Main(content, id='m-main', tabIndex=-1), html.Footer(LIMITATIONS, className='m-app-footer')], className='m-workspace')],
                    className='monthly-app m-shell')


def application_shell_markup(content, **context):
    """Serialize the shared HTML-only shell; Flask body is already rendered/escaped."""
    from html import escape
    from markupsafe import Markup
    def render(node):
        if node is None:
            return ''
        if isinstance(node, (str, int, float)):
            return escape(str(node))
        if isinstance(node, (list, tuple)):
            return ''.join(render(child) for child in node)
        item = node.to_plotly_json()
        props = dict(item['props'])
        children = props.pop('children', None)
        attrs = []
        for key, value in props.items():
            key = {'className': 'class', 'tabIndex': 'tabindex'}.get(key, key)
            if key == 'style':
                value = ';'.join(f'{k}:{v}' for k, v in value.items())
            if value is not None:
                attrs.append(f'{key}="{escape(str(value), quote=True)}"')
        tag = item['type'].lower()
        return f'<{tag} {" ".join(attrs)}>{render(children)}</{tag}>'
    return Markup(render(application_shell('__MONTHLY_BODY__', **context)).replace('__MONTHLY_BODY__', str(content)))


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
        return 'Yes' if value else 'No'
    if isinstance(value, list):
        return ', '.join(map(str, value)) or 'None'
    if key in ('observation_status', 'status', 'forecast_status', 'model_status'):
        return STATUS_LABELS.get(value, value)
    if isinstance(value, Real):
        return format_number(value, key)
    return value


def format_number(value, key=''):
    if value is None:
        return 'Unavailable'
    if key in ('mae', 'rmse', 'mase', 'mae_improvement'):
        return f'{value:,.3f}' if abs(value) >= .001 or value == 0 else '<0.001' if value > 0 else '>-0.001'
    if key == 'year':
        return str(int(value))
    return f'{value:,.0f}'


def table(rows, columns=None):
    rows = [{**row, 'icd10_description': disease_label(row['icd10_description'])} if 'icd10_description' in row else row for row in rows]
    if not rows:
        return empty_state('No records yet', 'Records will appear here when they are available.')
    columns = columns or list(rows[0])
    labels = {'icd10_block': 'ICD-10 block', 'icd10_description': 'Disease group', 'coverage_summary': 'Reporting coverage',
              'top5_year_count': 'Years reported', 'required_top5_year_count': 'Available years', 'reason': 'Data availability',
              'projected_total': 'Consultations · forecast period', 'consultation_count': 'Consultations',
              'mae': 'MAE', 'rmse': 'RMSE', 'mase': 'MASE', 'disease_group': 'Disease group',
              'forecast_value': 'Estimated consultations', 'rank': 'Rank'}
    numeric = [k for k in columns if any(isinstance(r.get(k), Real) and not isinstance(r.get(k), bool) for r in rows)]
    if len(rows) > 50:
        # Send compact records, not thousands of individual React components.
        # Native paging/sorting operates over all records but mounts only 25 rows.
        return html.Div([
            html.P(f'{len(rows):,} records · 25 per page. Sort using a column heading.', className='m-muted'),
            dash_table.DataTable(
                data=[{k: row.get(k) if k in numeric else display_value(row.get(k), k) for k in columns} for row in rows],
                columns=[dict(name=labels.get(k, k.replace('_', ' ').capitalize()), id=k,
                    **({'type': 'numeric', 'format': Format(precision=3 if k in ('mae', 'rmse', 'mase', 'mae_improvement') else 0,
                        scheme=Scheme.fixed, group=Group.no if k == 'year' else Group.yes, nully='Unknown / unavailable')}
                       if k in numeric else {'type': 'text'})) for k in columns],
                page_action='native', page_size=25, sort_action='native', sort_mode='single',
                cell_selectable=False,
                # Alignment follows inferred column types; static styling lives in CSS.
                style_cell_conditional=[{'if': {'column_id': k}, 'textAlign': 'right'} for k in numeric])
        ], className='m-paged-table')
    return html.Div(html.Table([
        html.Thead(html.Tr([html.Th(html.Button([
            labels.get(k, k.replace('_', ' ').capitalize()), html.Span(' ↕', **{'aria-hidden': 'true'})],
            type='button', className='m-sort-button', **{'data-column': str(index),
                'data-sort-kind': 'number' if k in numeric else 'text',
                'aria-label': 'Sort by ' + labels.get(k, k.replace('_', ' '))}),
            scope='col', className='m-numeric' if k in numeric else '', **{'aria-sort': 'none'}) for index, k in enumerate(columns)])),
        html.Tbody([html.Tr([html.Td(display_value(row.get(k), k),
            className='m-numeric' if k in numeric else '',
            **{'data-sort-value': '' if row.get(k) is None else str(row.get(k))}) for k in columns]) for row in rows])
    ], className='m-data-table'), className='m-table', tabIndex=0, role='region', **{'aria-label': 'Scrollable data table'})
