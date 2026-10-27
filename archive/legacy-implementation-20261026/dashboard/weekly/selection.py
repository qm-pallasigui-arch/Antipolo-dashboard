"""Offline-only training/validation selection. Final-test values are never inputs."""
from copy import deepcopy
from itertools import product
import json
from pathlib import Path
import uuid

import numpy as np

from dashboard.modeling.metrics import compute_metrics
from dashboard.weekly.data import digest, now
from dashboard.weekly.estimators import COMMON_BURN, SEEDS, VERSION, adf_diagnostic, fit_sarima, nnar


def candidates():
    return [{'order': [p, d, q], 'seasonal_order': [P, D, Q, 52], 'trend': 'n'}
            for p, d, q, P, D, Q in product(range(3), range(2), range(3), range(2), range(2), range(2))]


def base_config():
    return {'version': VERSION, 'model_version': VERSION, 'approved': False, 'approval_reference': None,
            'label': 'Validation-selected Hybrid SARIMA–NNAR', 'candidates': [],
            'nnar_lags': [1, 2], 'hidden_nodes': 2, 'alpha': .001, 'seed': SEEDS[0],
            'seed_policy': {'selection': list(SEEDS), 'production': SEEDS[0], 'aggregation': 'median'},
            'solver': 'lbfgs', 'activation': 'relu', 'minimum_training_weeks': 156,
            'minimum_residual_examples': 52, 'residual_burn': COMMON_BURN, 'diagnostic_lag': 52,
            'holdout_weeks': 52, 'validation_weeks': 52, 'missing_policy': 'state_space',
            'week53_policy': 'preserve_sequence', 'maxiter': 300, 'nnar_maxiter': 2000,
            'uncertainty_method': 'none', 'selection_status': 'pending',
            'estimator_policy': 'levels; approximate diffuse 1e6; common burn 108; constrained AR/MA; L-BFGS; no trend',
            'aic_shortlist_size': 10, 'rmse_tie_rtol': 1e-6, 'rmse_tie_atol': 1e-8}


def chronological_split(values, index):
    if len(values) != len(index) or len(values) < 260:
        raise ValueError('Model selection unavailable — insufficient historical data (156 + 52 + 52 positions required).')
    return (np.asarray(values[:-104], float), np.asarray(values[-104:-52], float),
            np.asarray(values[-52:], float),
            {'training': [list(index[0]), list(index[-105])],
             'validation': [list(index[-104]), list(index[-53])],
             'final_test': [list(index[-52]), list(index[-1])]})


def score_cases(actual, prediction):
    actual, prediction = np.asarray(actual, float), np.asarray(prediction, float)
    if actual.shape != prediction.shape or not np.isfinite(prediction).all():
        raise ValueError('Invalid forecast; candidates must score the identical finite-actual mask.')
    mask = np.isfinite(actual)
    if not mask.any():
        raise ValueError('No observed cases available for scoring.')
    metrics = compute_metrics(actual[mask], np.maximum(0, prediction)[mask])
    return {**metrics, 'test_positions_total': len(actual), 'observations_scored_rmse_mae': int(mask.sum()),
            'missing_actuals_excluded': int((~mask).sum()), 'mape_valid_observations': metrics['mape_n'],
            'zero_actuals_excluded_from_mape': int((actual[mask] == 0).sum())}


def selection_fingerprint(training, validation):
    return digest([[float(v) if np.isfinite(v) else None for v in values]
                   for values in (training, validation)])


def winner(rows, metric, c):
    best = min(r[metric]['rmse'] for r in rows)
    tied = [r for r in rows if np.isclose(r[metric]['rmse'], best, rtol=c['rmse_tie_rtol'], atol=c['rmse_tie_atol'])]
    return min(tied, key=lambda r: (r[metric]['mae'], r[metric]['mape'] if r[metric]['mape'] is not None else float('inf')))


def select_configuration(training, validation, disease, periods, checkpoint=None, progress=None):
    """Only training and validation arrays cross this API boundary."""
    c = base_config()
    emit = progress or (lambda stage, message: None)
    if np.isfinite(training).sum() < c['minimum_training_weeks']:
        raise ValueError('Model selection unavailable: at least 156 observed training weeks are required.')
    audit = {'run_id': uuid.uuid4().hex, 'started_at': now(), 'disease': disease,
             'periods': periods, 'sarima_candidates': [], 'nnar_candidates': [],
             'adf': adf_diagnostic(training), 'policy': deepcopy(c)}
    fitted = {}
    def save():
        if checkpoint:
            checkpoint(audit)
    for number, candidate in enumerate(candidates(), 1):
        emit('sarima_search', f'Fitting SARIMA candidate {number}/144: {candidate["order"]} {candidate["seasonal_order"]}.')
        record = {**candidate, 'fit_status': 'failed', 'converged': False, 'aic': None,
                  'log_likelihood': None, 'parameter_count': None, 'likelihood_burn': COMMON_BURN,
                  'effective_observation_count': int(np.isfinite(training[COMMON_BURN:]).sum())}
        try:
            prediction, residuals, record = fit_sarima(training, 52, candidate, c)
            if record['likelihood_burn'] != COMMON_BURN:
                raise ValueError('Incomparable likelihood burn.')
            fitted[len(audit['sarima_candidates'])] = (prediction, residuals)
        except Exception as exc:
            record.update(fit_status='failed', failure_reason=str(exc))
        audit['sarima_candidates'].append(record)
        save()
    valid = [(i, r) for i, r in enumerate(audit['sarima_candidates']) if r['fit_status'] == 'available']
    if not valid:
        raise ValueError('SARIMA fitting failed — no valid candidate configuration was identified.')
    # Common data mask and common burn must both match before AIC ranking.
    if len({(r['likelihood_burn'], r['effective_observation_count']) for _, r in valid}) != 1:
        raise ValueError('SARIMA likelihood windows are not comparable.')
    shortlist = sorted(valid, key=lambda item: item[1]['aic'])[:c['aic_shortlist_size']]
    emit('sarima_validation', f'Evaluating {len(shortlist)} lowest-AIC candidates on Validation.')
    for i, record in shortlist:
        record['validation'] = score_cases(validation, fitted[i][0])
        record['shortlisted'] = True
    selected = winner([r for _, r in shortlist], 'validation', c)
    chosen_index = next(i for i, r in shortlist if r is selected)
    baseline, residuals = fitted[chosen_index]
    emit('sarima_selected', f'Selected SARIMA {selected["order"]} {selected["seasonal_order"]} by Validation error.')
    emit('residuals', 'Preparing training-only post-burn residuals for NNAR selection.')
    for lag, hidden, alpha in product((2, 4, 6, 8, 13, 26), (2, 4, 8, 12), (.001, .01, .1, 1.0)):
        emit('nnar_search', f'Evaluating NNAR configuration {len(audit["nnar_candidates"]) + 1}/96 across three seeds: lag {lag}, hidden {hidden}, alpha {alpha}.')
        row = {'lag': lag, 'hidden_nodes': hidden, 'alpha': alpha, 'seeds': [], 'status': 'failed'}
        for seed in SEEDS:
            config = {**c, 'nnar_lags': list(range(1, lag + 1)), 'hidden_nodes': hidden, 'alpha': alpha, 'seed': seed}
            item = {'seed': seed, 'status': 'failed'}
            try:
                correction, notes = nnar(residuals, 52, config)
                item.update(status='available', metrics=score_cases(validation, baseline + correction), warnings=notes)
            except Exception as exc:
                item['failure_reason'] = str(exc)
            row['seeds'].append(item)
        if all(s['status'] == 'available' for s in row['seeds']):
            row['median_validation'] = {key: float(np.median([s['metrics'][key] for s in row['seeds']]))
                                        if row['seeds'][0]['metrics'][key] is not None else None
                                        for key in ('rmse', 'mae', 'mape')}
            row['status'] = 'available'
        audit['nnar_candidates'].append(row)
        save()
    available = [r for r in audit['nnar_candidates'] if r['status'] == 'available']
    if not available:
        raise ValueError('Hybrid unavailable — no NNAR configuration converged for all three fixed seeds.')
    neural = winner(available, 'median_validation', c)
    emit('hybrid_validation', 'Selected NNAR by median recursive Hybrid Validation case-count error across three seeds.')
    c.update(candidates=[{k: selected[k] for k in ('order', 'seasonal_order', 'trend')}],
             nnar_lags=list(range(1, neural['lag'] + 1)), hidden_nodes=neural['hidden_nodes'], alpha=neural['alpha'],
             disease=disease, selection_status='locked', selection_run_id=audit['run_id'], selection_timestamp=now(),
             periods=periods, training_start=periods['training'][0], training_end=periods['training'][1],
             validation_start=periods['validation'][0], validation_end=periods['validation'][1],
             selection_diagnostics={'adf': audit['adf'], 'sarima': selected, 'nnar': neural},
             nnar_helps_baseline=neural['median_validation']['rmse'] < selected['validation']['rmse'])
    c['selection_data_fingerprint'] = selection_fingerprint(training, validation)
    c['locked_configuration_id'] = digest(c)
    audit.update(configuration=c, completed_at=now(), status='locked')
    save()
    return c, audit


def verify_lock(c):
    body = {k: v for k, v in c.items() if k != 'locked_configuration_id'}
    if c.get('selection_status') != 'locked' or c.get('locked_configuration_id') != digest(body):
        raise ValueError('No validated locked model configuration is currently available.')
    if len(c['candidates']) != 1 or c['residual_burn'] != COMMON_BURN or c['holdout_weeks'] != 52:
        raise ValueError('Locked model protocol is inconsistent.')


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False), encoding='utf-8')
    temporary.replace(path)


def require_research_data(dataset, disease):
    if disease not in ('Dengue', 'Leptospirosis', 'Measles'):
        raise ValueError('Research disease must be Dengue, Leptospirosis or Measles; combined categories cannot be relabeled.')
    meta = dataset['metadata']
    if (str(meta.get('population', '')).replace('–', '-') != '5-19'
            or meta.get('case_classification') != 'confirmed' or meta.get('dataset_type') != 'real'
            or meta.get('frequency') != 'weekly' or not dataset.get('eligible')):
        raise ValueError('Research dataset eligibility unresolved: confirmed cases, ages 5–19 and validated source metadata required.')
    # Do not trust an edited JSON eligibility flag or stale validation errors.
    import pandas as pd
    from dashboard.weekly.data import validate
    checked = validate(pd.DataFrame(dataset['records']), meta)
    if not checked['eligible']:
        raise ValueError('Research dataset eligibility unresolved: active records failed revalidation.')


def select_dataset(dataset, disease, output):
    from dashboard.weekly.model import training_series, retrospective_evaluation
    require_research_data(dataset, disease)
    values, index = training_series(dataset, disease)
    train, val, _, periods = chronological_split(values, index)
    root = Path(output)
    c, audit = select_configuration(train, val, disease, periods,
                                   lambda a: write_json(root / 'search.json', a))
    # Persist lock BEFORE any final-test computation. Test results never mutate c.
    write_json(root / 'locked.json', c)
    result = {'metrics': {}, 'warnings': [], 'configuration': deepcopy(c)}
    retrospective_evaluation(result, values, index, c, disease)
    verify_lock(c)
    write_json(root / 'evaluation.json', result)
    write_reconciliation(root / 'methodology.md', c, result)
    return c, audit, result


def write_reconciliation(path, c, result):
    sarima = c['selection_diagnostics']['sarima']
    neural = c['selection_diagnostics']['nnar']
    metrics = result['metrics']
    comparisons = [np.sign(metrics['hybrid'][key] - metrics['sarima'][key]) for key in ('rmse', 'mae')]
    comparison = ('Similar' if all(v == 0 for v in comparisons) else
                  'Hybrid better' if all(v <= 0 for v in comparisons) else
                  'SARIMA better' if all(v >= 0 for v in comparisons) else 'Mixed')
    lines = [f"# {c['disease']} — corrected methodology results", '',
             f"Locked configuration: `{c['locked_configuration_id']}`", '',
             *[f"- {name}: {start} through {end}" for name, (start, end) in c['periods'].items()], '',
             f"SARIMA {sarima['order']}{sarima['seasonal_order']}; training AIC {sarima['aic']:.6g}.",
             f"NNAR: lag {neural['lag']}; hidden nodes {neural['hidden_nodes']}; alpha {neural['alpha']}; ReLU; L-BFGS.",
             f"Selection seeds {list(SEEDS)}; median validation metrics; production seed {SEEDS[0]}.", '',
             '| Period / model | RMSE | MAE | MAPE (%) |', '|---|---:|---:|---:|']
    for label, m in [('Validation SARIMA', sarima['validation']), ('Validation Hybrid (seed median)', neural['median_validation']),
                     ('Final Test SARIMA', metrics['sarima']), ('Final Test Hybrid', metrics['hybrid'])]:
        lines.append('| ' + label + ' | ' + ' | '.join('Unavailable' if m[k] is None else f'{m[k]:.6g}' for k in ('rmse', 'mae', 'mape')) + ' |')
    lines += ['', f"MAPE coverage: {metrics['hybrid']['mape_n']}/{metrics['hybrid']['n']} observed final-test positions.",
              f'Final comparison (RMSE / MAE): {comparison}. MAPE is supporting evidence.', '',
              'ADF is a stationarity diagnostic; AIC screens training fit and complexity. Validation selects orders.',
              'Ljung–Box tests residual serial autocorrelation with p+q+P+Q fitted AR/MA degrees of freedom.',
              'Neither a residual diagnostic nor a percentage-error threshold determines the winner.', '',
              'ADF: ' + json.dumps(c['selection_diagnostics']['adf']), '',
              'Ljung–Box: ' + json.dumps(sarima['ljung_box']), '',
              'All data retain genuine zeros, gaps and Week 53. No imputation or pre-metric rounding.',
              'Final-test observations were excluded from selection. Both models use the same finite-actual mask.',
              'Operational forecasting refits this lock on all eligible history and slices one 52-week path.',
              'Progress reports executed stages and does not change model fitting. Uncertainty bands are disabled.',
              'Limitations: one validation block; fixed top-10 AIC shortlist; three NNAR seeds; no prospective validation.',
              'Algorithmic exclusion does not erase any prior human exposure to the historical test period.']
    Path(path).write_text('\n'.join(lines) + '\n', encoding='utf-8')
