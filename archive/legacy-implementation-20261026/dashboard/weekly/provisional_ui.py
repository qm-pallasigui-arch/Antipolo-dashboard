"""Inspectable provisional comparison charts and evidence, with no model work."""
import json

from dash import dcc, html
import plotly.graph_objects as go

from dashboard.weekly.presentation import disclosure, table
from dashboard.weekly.provisional import TITLE, NOTICE


def week_labels(index):
    return [f'{year} W{week:02d}' for year, week in index]


def comparison_figures(result):
    evaluation = result['evaluation']
    x = week_labels(evaluation['index'])
    test = go.Figure()
    test.add_scatter(x=x, y=evaluation['actual'], name='Actual Cases', connectgaps=False)
    for name, label in [('sarima', 'SARIMA-only Forecast'), ('hybrid', 'Hybrid SARIMA–NNAR Forecast')]:
        test.add_scatter(x=x, y=evaluation['predictions'][name], name=label)
    test.update_layout(title='Out-of-Sample Final Test — Actual vs Forecast', template='plotly_white',
                       yaxis_title='Cases', xaxis_title='Final Test reporting week', legend={'orientation': 'h'})
    historical = go.Figure()
    historical.add_scatter(x=week_labels(result.get('historical_evaluation_index', result['training_index'])[:-52]),
                           y=result.get('historical_evaluation_values', result['history'])[:-52],
                           name='Historical observed cases (before Final Test)', connectgaps=False)
    for trace in test.data:
        historical.add_trace(trace)
    historical.update_layout(title='Historical Seasonal Pattern vs Final-Test Forecast', template='plotly_white',
                             yaxis_title='Cases', xaxis_title='Reporting week', legend={'orientation': 'h'})
    for figure in (test, historical):
        figure.update_xaxes(type='category', nticks=12, tickangle=-35)
    return test, historical


def component_rows(result):
    rows = []
    for block, labels, component in [
        ('Final Test', week_labels(result['evaluation']['index']), result['evaluation']['components']),
        ('Future', [f'+{p["horizon_week"]}' for p in result['forecast_index']], result['components'])]:
        for i, label in enumerate(labels):
            rows.append({'block': block, 'week': label, 'raw_sarima': component['raw_sarima'][i],
                         'nnar_correction': component['nnar_correction'][i], 'hybrid': component['hybrid'][i]})
    return rows


def panel(result):
    test, history = comparison_figures(result)
    c = result['configuration']
    selected = c['candidates'][0]
    metric_rows = []
    coverage_rows = []
    for period, models in [('Validation', result['validation_metrics']), ('Final Test', result['metrics'])]:
        for name, metrics in models.items():
            # Validation median metrics share the coverage of every successful seed.
            coverage = (result['validation_seed_metrics'][0]['metrics']
                        if name == 'hybrid_seed_median' else metrics)
            label = {'sarima': 'SARIMA-only', 'hybrid': 'Hybrid', 'hybrid_seed_median': 'Hybrid (seed median)'}[name]
            metric_rows.append({'period': period, 'model': label,
                **{k: round(metrics[k], 3) if metrics[k] is not None else 'Unavailable' for k in ('rmse', 'mae', 'mape')}})
            coverage_rows.append({'period': period, 'model': label, 'scored': coverage.get('observations_scored_rmse_mae'),
                'missing': coverage.get('missing_actuals_excluded'), 'zero_exclusions': coverage.get('zero_actuals_excluded_from_mape'),
                'mape_count': coverage.get('mape_valid_observations')})
    components = component_rows(result)
    component_charts = []
    for block in ('Final Test', 'Future'):
        rows = [r for r in components if r['block'] == block]
        fig = go.Figure()
        for field, label in [('raw_sarima', 'Raw SARIMA'), ('nnar_correction', 'NNAR residual correction'), ('hybrid', 'Final Hybrid')]:
            fig.add_scatter(x=[r['week'] for r in rows], y=[r[field] for r in rows], name=label)
        fig.update_layout(title=block + ' forecast components', template='plotly_white', yaxis_title='Cases', legend={'orientation': 'h'})
        fig.update_xaxes(type='category', nticks=12, tickangle=-35)
        component_charts.append(dcc.Graph(figure=fig))
    actual_peak = result['shape_diagnostics']['actual_peak']
    peaks = [{'model': 'Actual', 'week': week_labels([actual_peak['week']])[0],
              'count': actual_peak['count'], 'timing_error': '—', 'magnitude_error': '—'}]
    directions = []
    for name, row in result['shape_diagnostics']['models'].items():
        peaks.append({'model': name, 'week': week_labels([row['peak_week']])[0], 'count': round(row['peak_count'], 3),
                       'timing_error': row['peak_timing_error_positions'], 'magnitude_error': round(row['peak_magnitude_error_cases'], 3)})
        agreement, ratio = row['directional_agreement_rate'], row['difference_sd_ratio']
        directions.append({'model': name, 'agreement': f'{agreement:.1%}' if agreement is not None else 'Unavailable',
                           'scored_pairs': row['direction_pairs_scored'],
                           'change_sd_ratio': round(ratio, 3) if ratio is not None else 'Unavailable'})
    return html.Section([
        html.H3(TITLE), html.Strong(NOTICE),
        html.P('Full chronological model selection; the final test was excluded from fitting and selection until after the configuration was locked.'),
        html.P(f"Selected SARIMA {selected['order']} {selected['seasonal_order']}; NNAR lag {max(c['nnar_lags'])}, hidden nodes {c['hidden_nodes']}, alpha {c['alpha']}, production seed {c['seed']}."),
        table([result['data_status']]),
        html.Ul([html.Li(w) for w in c.get('data_assumptions', [])]),
        html.H4('Validation and untouched Final Test metrics'), table(metric_rows,
            columns={'period': 'Period', 'model': 'Model', 'rmse': 'RMSE (cases)', 'mae': 'MAE (cases)', 'mape': 'MAPE (%)'}),
        disclosure('Scored observations and exclusions', table(coverage_rows,
            columns={'period': 'Period', 'model': 'Model', 'scored': 'Scored weeks', 'missing': 'Missing exclusions',
                     'zero_exclusions': 'Zero exclusions (MAPE)', 'mape_count': 'MAPE valid weeks'})),
        html.P('Hybrid Validation metrics are medians across seeds 42, 137 and 2026. Final Test and future refits use the preselected production seed 42. MAPE is a percentage; RMSE and MAE are cases.'),
        dcc.Graph(figure=test), dcc.Graph(figure=history),
        html.H4('Provisional Validation Interpretation'), html.Ul([html.Li(s) for s in result['interpretation']]),
        html.H4('Peak timing and direction diagnostics'), table(peaks,
            columns={'model': 'Model', 'week': 'Peak week', 'count': 'Peak cases', 'timing_error': 'Timing error (weeks)', 'magnitude_error': 'Magnitude error (cases)'}),
        table(directions, columns={'model': 'Model', 'agreement': 'Direction agreement', 'scored_pairs': 'Consecutive pairs', 'change_sd_ratio': 'Change SD ratio'}),
        html.P(result['shape_diagnostics']['limitations']),
        disclosure('Diagnostic heuristic thresholds', html.Pre(json.dumps(result['shape_diagnostics']['thresholds'], indent=2))),
        disclosure('Forecast Components', [html.P('Final Hybrid = max(0, raw SARIMA + NNAR residual correction). The nonnegative clipping step is included in both scoring and display.'),
                                            *component_charts, table(components, page_size=13)]),
        disclosure('ADF and adjusted Ljung–Box diagnostics', [
            html.P('ADF is unavailable when the observed series has gaps or is constant. Ljung–Box uses model_df = p + q + P + Q; unsupported residual windows are explicitly unavailable.'),
            html.Pre(json.dumps({'training_adf': c['selection_diagnostics']['adf'],
                'training_ljung_box': c['selection_diagnostics']['sarima']['ljung_box'],
                'final_test_refit': result['evaluation']['diagnostics'],
                'all_history_refit': result['diagnostics']}, indent=2), className='technical-readout')]),
        disclosure('Search summary and split boundaries', [table([result['search_summary']]),
            html.Pre(json.dumps(c['periods'], indent=2)), html.P('Dataset fingerprint: ' + result['dataset_fingerprint'])]),
    ], className='provisional-validation-panel')
