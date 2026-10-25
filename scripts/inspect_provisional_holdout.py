"""Inspect SARIMA-only holdout evidence when strict Hybrid initialization is blocked.

This does not complete Hybrid validation, retune settings, or generate a future path.
"""
import argparse
import json
from pathlib import Path
import sys

import numpy as np
from threadpoolctl import threadpool_limits

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dashboard.weekly.data import digest, now
from dashboard.weekly.estimators import fit_sarima
from dashboard.weekly.model import training_series
from dashboard.weekly.provisional import shape_diagnostics
from dashboard.weekly.sample import prepare_uploaded
from dashboard.weekly.selection import score_cases, verify_lock, write_json, chronological_split, selection_fingerprint


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run_directory', type=Path)
    args = parser.parse_args()
    root = args.run_directory
    c = json.loads((root / 'locked.json').read_text(encoding='utf-8'))
    verify_lock(c)
    if c.get('validation_scope') != 'provisional':
        raise ValueError('This inspection accepts provisional locks only.')
    dataset = json.loads((root / 'input.json').read_text(encoding='utf-8'))['dataset']
    fingerprint = digest({'records': dataset['records'], 'metadata': dataset['metadata'], 'disease': c['disease']})
    if fingerprint != c['dataset_fingerprint']:
        raise ValueError('Dataset differs from the locked provisional source.')
    prepared, assumptions = prepare_uploaded(dataset, 'Provisional')
    values, index = training_series(prepared, c['disease'])
    train, validation, actual, periods = chronological_split(values, index)
    if periods != c['periods'] or selection_fingerprint(train, validation) != c['selection_data_fingerprint']:
        raise ValueError('Selection boundaries or observations changed.')
    with threadpool_limits(limits=1):
        prediction, residuals, diagnostics = fit_sarima(values[:-52], 52, c['candidates'][0], c)
    missing = [list(p) for p, value in zip(index[:-52][-max(c['nnar_lags']):], residuals[-max(c['nnar_lags']):]) if not np.isfinite(value)]
    if not missing:
        raise ValueError('No missing terminal residual was found; this inspection is only for that failure.')
    predicted = np.maximum(0, prediction)
    metric = score_cases(actual, predicted)
    shape = shape_diagnostics(actual, {'sarima': predicted}, [list(p) for p in index[-52:]])
    payload = {'title': 'Supplemental SARIMA-only Final Test — Not Thesis-Validated',
        'status': 'Hybrid Final Test blocked', 'research_validated': False, 'completed_at': now(),
        'dataset_fingerprint': fingerprint, 'configuration': c, 'missing_terminal_residual_weeks': missing,
        'metrics': {'sarima': metric, 'hybrid': None}, 'shape_diagnostics': shape,
        'actual': [float(v) if np.isfinite(v) else None for v in actual],
        'sarima_prediction': predicted.tolist(), 'raw_sarima_prediction': prediction.tolist(),
        'final_test_index': [list(p) for p in index[-52:]], 'diagnostics': diagnostics,
        'future_forecast': None, 'limitations': 'Supplemental baseline only. No Hybrid final-test metrics or provisional future path were generated. Missing counts/residuals were not filled.'}
    write_json(root / 'sarima-only-holdout.json', payload)
    import plotly.graph_objects as go
    labels = [f'{year} W{week:02d}' for year, week in index[-52:]]
    figure = go.Figure()
    figure.add_scatter(x=labels, y=payload['actual'], name='Actual cases', connectgaps=False)
    figure.add_scatter(x=labels, y=payload['sarima_prediction'], name='SARIMA-only Final Test')
    figure.update_layout(title='Dengue: supplemental Final Test — Not Thesis-Validated', template='plotly_white',
        yaxis_title='Cases', xaxis_title='Reporting week',
        annotations=[{'text': 'Hybrid unavailable: missing initial residual. No provisional future forecast generated.',
                      'xref': 'paper', 'yref': 'paper', 'x': 0, 'y': 1.12, 'showarrow': False}],
        margin={'t': 120}, legend={'orientation': 'h'})
    figure.update_xaxes(type='category', nticks=12, tickangle=-35)
    figure.write_html(root / 'sarima-only-holdout.html', include_plotlyjs=True)
    sarima, neural = c['selection_diagnostics']['sarima'], c['selection_diagnostics']['nnar']
    audit = json.loads((root / 'search.json').read_text(encoding='utf-8'))
    peak = shape['models']['sarima']
    lines = ['# Dengue provisional assessment — Not Thesis-Validated', '',
        'Source: repository Antipolo_Disease_Surveillance_2016-2025.xlsx, unchanged as requested.', '',
        'The full parameter search completed, but the strict Hybrid Final Test could not start because its NNAR lag window includes a missing residual at ' + str(missing) + '.', '',
        f"Dataset fingerprint: `{fingerprint}`", '',
        f"Search: {len(audit['sarima_candidates'])} SARIMA candidates and {len(audit['nnar_candidates'])} NNAR configurations, with three seeds each. "
        f"NNAR configurations successful for all seeds: {sum(r['status'] == 'available' for r in audit['nnar_candidates'])}.", '',
        f"Selected SARIMA: {sarima['order']} {sarima['seasonal_order']}.",
        f"Selected NNAR: lag {neural['lag']}, hidden nodes {neural['hidden_nodes']}, alpha {neural['alpha']}, production seed {c['seed']}.", '',
        *[f'- {name}: {start} through {end}' for name, (start, end) in periods.items()], '',
        '| Period / model | RMSE | MAE | MAPE (%) |', '|---|---:|---:|---:|']
    for label, metrics in [('Validation SARIMA', sarima['validation']), ('Validation Hybrid (seed median)', neural['median_validation']), ('Final Test SARIMA (supplemental)', metric)]:
        lines.append('| ' + label + ' | ' + ' | '.join('Unavailable' if metrics[k] is None else f'{metrics[k]:.6f}' for k in ('rmse', 'mae', 'mape')) + ' |')
    lines += ['| Final Test Hybrid | Unavailable | Unavailable | Unavailable |', '',
        f"Final Test SARIMA coverage: {metric['n']} scored observations, {metric['missing_actuals_excluded']} missing exclusions, {metric['zero_actuals_excluded_from_mape']} zero exclusions from MAPE, {metric['mape_n']} MAPE-valid observations.", '',
        '## Answers about shape and future forecasts', '',
        '- Hybrid versus SARIMA on Final Test: cannot be determined because Hybrid initialization was blocked.',
        f"- Actual test peak: {shape['actual_peak']['week']}, {shape['actual_peak']['count']:g} cases.",
        f"- SARIMA test peak: {peak['peak_week']}, {peak['peak_count']:.6f} cases; timing error {peak['peak_timing_error_positions']:+d} chronological weeks; magnitude error {peak['peak_magnitude_error_cases']:+.6f} cases.",
        f"- SARIMA direction agreement: {peak['directional_agreement_rate']:.2%} on {peak['direction_pairs_scored']} adjacent observed pairs. This is supplementary, not proof of seasonal accuracy.",
        '- Hybrid reproduction of major rises/falls and peak timing: unavailable.',
        '- Component causing a future decline: unavailable; no provisional future path was generated after the blocked Hybrid test.',
        '- Support for a smooth future Hybrid decline: not established by this run. Earlier fixed-preset sample forecasts are not evidence for the selected provisional configuration.',
        '- Resulting provisional 52-week Hybrid path: intentionally not generated. Final Test must complete first.', '',
        '## Source assumptions', '', *['- ' + s for s in assumptions], '',
        '## Next step', '',
        'Establish from the data provider whether the blank Week 53 is a missing report or a nonexistent source-calendar week. Do not replace it with zero without evidence. Recursive residual warm-up would extend the method and requires an explicit decision; it was not enabled.', '',
        'The signed provisional lock remains separate from the research registry. No parameter was retuned using these test outcomes. Full precision and baseline diagnostic arrays are in sarima-only-holdout.json; candidate failures are in search.json.']
    (root / 'assessment.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(json.dumps({'selected_sarima': c['candidates'], 'selected_nnar': {k: c[k] for k in ('nnar_lags', 'hidden_nodes', 'alpha', 'seed')},
                     'validation': {'sarima': sarima['validation'], 'hybrid_seed_median': neural['median_validation']},
                     'sarima_final_test': metric, 'shape': shape}, indent=2))


if __name__ == '__main__':
    main()
