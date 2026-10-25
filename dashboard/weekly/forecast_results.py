"""Shared result presentation for guided and legacy forecasts; never fits models."""
import json

from dash import dcc, html
import plotly.graph_objects as go

from dashboard.weekly.presentation import disclosure, table
from dashboard.weekly.provisional_ui import comparison_figures, component_rows


def performance_panel(result):
    result = result or {}
    metrics = result.get('metrics') or {}
    c = result.get('configuration') or {}
    evaluation = result.get('evaluation') or {}
    rows, coverage = [], []
    for period, models in [('Validation', result.get('validation_metrics', {})), ('Final Test', metrics)]:
        for name, values in models.items():
            if not values:
                continue
            label = {'sarima': 'SARIMA-only', 'hybrid': 'Hybrid', 'hybrid_seed_median': 'Hybrid (seed median)'}.get(name, name)
            rows.append({'period': period, 'model': label,
                **{k: round(values[k], 3) if values.get(k) is not None else 'Unavailable' for k in ('rmse', 'mae', 'mape')}})
            seeds = result.get('validation_seed_metrics') or []
            counts = seeds[0]['metrics'] if name == 'hybrid_seed_median' and seeds else values
            coverage.append({'period': period, 'model': label, 'scored': counts.get('n'),
                'missing': counts.get('missing_actuals_excluded'), 'mape_valid': counts.get('mape_n'),
                'zero_exclusions': counts.get('zero_actuals_excluded_from_mape')})
    children = [html.H3('Model Performance')]
    if rows:
        children += [table(rows, columns={'period': 'Period', 'model': 'Model', 'rmse': 'RMSE (cases)', 'mae': 'MAE (cases)', 'mape': 'MAPE (%)'}),
                     disclosure('Scored observations and exclusions', table(coverage)),
                     html.P('Validation Hybrid metrics use the median across selection seeds. Final Test metrics use the locked production seed. Lower error is better; Hybrid is not required to outperform SARIMA.')]
    else:
        children.append(html.P('Quick Preview is an unvalidated demonstration and does not calculate historical performance.' if result.get('sample_forecast') else 'Historical performance appears here after a successful guided run.'))
    periods = c.get('periods') or evaluation.get('periods') or {}
    if periods:
        children.append(table([{'period': key.replace('_', ' ').title(), 'from': f'{start[0]} W{start[1]:02d}',
                                'to': f'{end[0]} W{end[1]:02d}'} for key, (start, end) in periods.items()]))
    if c.get('candidates') and isinstance(c['candidates'], list):
        selected = c['candidates'][0]
        children.append(html.P(f"SARIMA {selected['order']} {selected['seasonal_order']}; NNAR lags {c.get('nnar_lags')}, hidden nodes {c.get('hidden_nodes')}, alpha {c.get('alpha')}."))
    diagnostics = []
    if evaluation.get('index') and evaluation.get('predictions'):
        # Legacy results may lack stored history. Final Test remains independently inspectable.
        if result.get('history') is not None:
            test, historical = comparison_figures(result)
            diagnostics.append(dcc.Graph(figure=historical))
        else:
            test = go.Figure()
            labels = [f'{y} W{w:02d}' for y, w in evaluation['index']]
            test.add_scatter(x=labels, y=evaluation['actual'], name='Actual cases', connectgaps=False)
            for name, values in evaluation['predictions'].items():
                test.add_scatter(x=labels, y=values, name=name)
            test.update_layout(title='Final Test — Actual vs Forecast', template='plotly_white')
        children.append(dcc.Graph(figure=test))
    children += [html.Ul([html.Li(s) for s in result.get('interpretation', [])]),
                 html.Button('Download Methodology Report', id='w-provisional-export', n_clicks=0,
                             disabled=not bool(metrics), className='secondary')]
    if result.get('performance_reused'):
        children.append(html.P('Compatible historical performance reused. The original evaluation dates are unchanged.'))
    if result.get('performance_provenance', {}).get('test_outcomes_revised'):
        children.append(html.P('Final Test outcomes were revised; metrics were recomputed on the original window without retuning.'))
    if result.get('components') and evaluation.get('components'):
        component_data = component_rows(result)
        figures = []
        for block in ('Final Test', 'Future'):
            subset = [r for r in component_data if r['block'] == block]
            figure = go.Figure()
            for key, label in [('raw_sarima', 'Raw SARIMA'), ('nnar_correction', 'NNAR correction'), ('hybrid', 'Clipped Hybrid')]:
                figure.add_scatter(x=[r['week'] for r in subset], y=[r[key] for r in subset], name=label)
            figure.update_layout(title=block + ' forecast components', template='plotly_white')
            figure.update_xaxes(nticks=12)
            figures.append(dcc.Graph(figure=figure))
        diagnostics.append(disclosure('Forecast Components', [html.P('Hybrid = max(0, raw SARIMA + NNAR correction).'),
            *figures, table(component_data, page_size=13)]))
    diagnostics += [html.Pre(json.dumps({
        'configuration': c, 'dataset_fingerprint': result.get('dataset_fingerprint'),
        'model_version': result.get('model_version'), 'methodology_version': result.get('methodology_version'),
        'peak_and_direction': result.get('shape_diagnostics'), 'fit_diagnostics': result.get('diagnostics'),
        'historical_diagnostics': evaluation.get('diagnostics'), 'run_metadata': result.get('run_metadata')},
        indent=2, ensure_ascii=False), className='technical-readout'),
        html.Ul([html.Li(w) for w in result.get('warnings', [])])]
    children.append(disclosure('Diagnostics', diagnostics))
    return html.Section(children, className='model-performance-panel')
