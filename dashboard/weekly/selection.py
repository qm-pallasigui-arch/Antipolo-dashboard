"""Decision 90 selection primitives; all inputs retain calendar positions."""
from itertools import product
import warnings

import numpy as np
from scipy.stats import rankdata
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler
from statsmodels.tsa.statespace.sarimax import SARIMAX
from statsmodels.stats.diagnostic import acorr_ljungbox

from dashboard.modeling.metrics import compute_metrics
from dashboard.weekly.progress import report


def fit_sarima(values, steps, candidate, config):
    """Fit at a single cutoff; return raw forecasts and cutoff-specific residuals."""
    values = np.asarray(values, dtype=float)
    record = {**candidate, 'status': 'unavailable', 'training_positions': len(values),
              'missing_observations': int(np.isnan(values).sum()), 'aic': None}
    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            fitted = SARIMAX(values, order=candidate['order'], seasonal_order=candidate['seasonal_order'],
                             trend=candidate['trend'], loglikelihood_burn=config['residual_burn'],
                             enforce_stationarity=True, enforce_invertibility=True).fit(disp=False, maxiter=config['maxiter'])
        record['warnings'] = [str(w.message) for w in caught]
        record['converged'] = bool(fitted.mle_retvals.get('converged', False))
        if not record['converged'] or not np.isfinite(fitted.aic) or not np.isfinite(fitted.params).all():
            raise ValueError('SARIMA did not converge to finite parameters and AIC.')
        path = np.asarray(fitted.forecast(steps), dtype=float)
        if path.shape != (steps,) or not np.isfinite(path).all():
            raise ValueError('SARIMA forecast is invalid or nonfinite.')
        residuals = values - np.asarray(fitted.fittedvalues)
        if not np.isfinite(residuals[np.isfinite(values)]).all():
            raise ValueError('SARIMA residuals are nonfinite at observed positions.')
        residuals[:config['residual_burn']] = np.nan
        record.update(status='available', aic=float(fitted.aic),
                      fitted_parameters=dict(zip(fitted.param_names, map(float, fitted.params))))
        tail = residuals[config['residual_burn']:]
        if len(tail) > config['diagnostic_lag'] and np.isfinite(tail).all():
            try:
                pvalue = float(acorr_ljungbox(tail, lags=[config['diagnostic_lag']], return_df=True).lb_pvalue.iloc[0])
                record['ljung_box_pvalue'] = pvalue if np.isfinite(pvalue) else None
            except Exception as exc:
                record['diagnostic_notice'] = str(exc)
        else:
            record['diagnostic_notice'] = 'Ljung–Box unavailable with gaps or insufficient residuals.'
        return path, residuals, record
    except Exception as exc:
        record.update(status='unavailable', reason=str(exc))
        return None, None, record


def approved_configuration():
    """Fresh authoritative configuration; library settings retain existing values."""
    return {
        'version': 'weekly-decision-90-v1', 'label': 'Decision 90 weekly methodology',
        'approved': True, 'approval_reference': 'docs/FINAL_WEEKLY_IMPLEMENTATION_SPEC.md',
        'candidates': [dict(order=[p, d, q], seasonal_order=[P, D, Q, 52], trend='n')
                       for p, d, q, P, D, Q in product(range(3), range(2), range(3), range(2), range(2), range(2))],
        'validation_windows': 3, 'validation_weeks': 52, 'holdout_weeks': 52,
        'minimum_training_weeks': 156, 'minimum_residual_examples': 52,
        'lag_windows': [3, 6, 12, 26, 52], 'hidden_nodes_grid': [2, 3, 5, 8],
        'activation': 'logistic', 'output_activation': 'identity', 'repeats': 5,
        'seed': 42, 'maxiter': 300, 'nnar_maxiter': 2000, 'alpha': 1.0,
        'solver': 'lbfgs', 'residual_burn': 53, 'diagnostic_lag': 52,
        'missing_policy': 'state_space', 'week53_policy': 'preserve_sequence',
        'shortlist_policy': 'union_of_three_windows',
        'mape_policy': 'mean_over_applicable_windows_else_rank_rmse_mae',
        'aic_tiebreak': 'arithmetic mean of three cutoff-specific refit AICs',
        'metrics': ['rmse', 'mae', 'mape'], 'uncertainty_method': None,
        'simplicity_rule': 'NNAR parameter count, then lag window, then hidden nodes',
        'implementation_choices': 'StandardScaler on training lag inputs; no trend; residual burn 53; '
                                  'stationarity/invertibility enforced; seeds 42 through 46; '
                                  'average ranks for tied metric values; alpha is L2 regularization, not hybrid weighting.',
    }


def evaluation_splits(size):
    """Exactly three expanding 52-position windows and an untouched holdout."""
    first = size - 4 * 52
    if first < 156:
        raise ValueError('Formal forecasting evaluation unavailable — insufficient initial historical observations for the approved validation design.')
    return [(first + i * 52, first + (i + 1) * 52) for i in range(3)], (size - 52, size)


def validate_configuration(config):
    expected = approved_configuration()
    technical = {'maxiter', 'nnar_maxiter', 'diagnostic_lag'}
    for key, value in expected.items():
        if key not in technical and config.get(key) != value:
            raise ValueError(f'Decision 90 requires the fixed {key} setting; obsolete or modified methodology cannot run in production.')
    for key in technical:
        if type(config.get(key)) is not int or config[key] < 1:
            raise ValueError(f'{key} must be a positive integer.')
    if set(config) - set(expected):
        raise ValueError('Unrecognized Decision 90 configuration fields.')
    return dict(config)


def shortlist(records):
    valid = sorted((r for r in records if r.get('status') == 'available' and
                    r.get('aic') is not None and np.isfinite(r['aic'])),
                   key=lambda r: (r['aic'], tuple(r['order']), tuple(r['seasonal_order'])))
    if not valid:
        return []
    count = sum(r['aic'] - valid[0]['aic'] <= 4 for r in valid)
    return valid[:min(5, max(3, count))]


def score(actual, forecasts):
    """Shared actual mask; invalid model paths are unavailable, never rescored on fewer rows."""
    actual = np.asarray(actual, dtype=float)
    mask = np.isfinite(actual)
    coverage = {'total_weeks': len(actual), 'scored_weeks': int(mask.sum()),
                'excluded_missing_actuals': int((~mask).sum()),
                'mape_zero_excluded': int(np.sum(actual[mask] == 0)),
                'mape_n': int(np.sum(actual[mask] != 0))}
    metrics = {}
    for name, prediction in forecasts.items():
        if prediction is None:
            metrics[name] = None
            continue
        prediction = np.asarray(prediction, dtype=float)
        if prediction.shape != actual.shape or not np.isfinite(prediction).all():
            raise ValueError('A scoring path must have finite predictions at every calendar position.')
        metrics[name] = ({**compute_metrics(actual[mask], np.maximum(0, prediction[mask])),
                          'mape_zero_excluded': coverage['mape_zero_excluded']} if mask.any() else None)
    return {'metrics': metrics, **coverage}


def rank_candidates(records, hybrid=False):
    """Equal-window averages; MAPE uses only windows with nonzero actuals."""
    eligible = []
    for record in records:
        windows = record.get('window_metrics', [])
        if len(windows) != 3 or any(m is None or any(m.get(k) is None or not np.isfinite(m[k])
                                                  for k in ('rmse', 'mae')) for m in windows):
            continue
        mape = [m['mape'] for m in windows if m.get('mape') is not None]
        if not all(np.isfinite(mape)):
            continue
        mean = {k: float(np.mean([m[k] for m in windows])) for k in ('rmse', 'mae')}
        mean['mape'] = float(np.mean(mape)) if mape else None
        eligible.append({**record, 'mean_metrics': mean,
                         'mape_window_count': len(mape),
                         'mape_observation_count': sum(m.get('mape_n', 0) for m in windows),
                         'mape_zero_excluded': sum(m.get('mape_zero_excluded', 0) for m in windows),
                         'mape_selection_unavailable': not mape})
    if not eligible:
        return []
    # Shared actual positions imply identical MAPE applicability for every candidate.
    if len({r['mape_window_count'] for r in eligible}) != 1:
        raise ValueError('Candidates must share MAPE scoring coverage across validation windows.')
    measures = ['rmse', 'mae'] + (['mape'] if eligible[0]['mape_window_count'] else [])
    ranks = np.array([rankdata([r['mean_metrics'][k] for r in eligible], method='average')
                      for k in measures]).T
    for record, rank in zip(eligible, ranks):
        record['metric_ranks'] = dict(zip(measures, map(float, rank)))
        record['ranking_metrics'] = measures
        record['average_rank'] = float(np.mean(rank))
    def key(r):
        base = (r['average_rank'], *(r['mean_metrics'][k] for k in measures))
        if hybrid:
            lag, nodes = r['lag_window'], r['hidden_nodes']
            return (*base, nodes * (lag + 2) + 1, lag, nodes, str(r.get('candidate_id', '')))
        return (*base, r['aic'], sum(r['order'][::2]) + sum(r['seasonal_order'][:3:2]),
                tuple(r['order']), tuple(r['seasonal_order']))
    return sorted(eligible, key=key)


def residual_windows(residuals, lag):
    residuals = np.asarray(residuals, dtype=float)
    positions = [i for i in range(lag, len(residuals)) if np.isfinite(residuals[i-lag:i+1]).all()]
    X = np.asarray([residuals[i-lag:i][::-1] for i in positions], dtype=float).reshape(-1, lag)
    y = residuals[positions]
    return X, y, {'candidate_windows': max(0, len(residuals) - lag), 'complete_windows': len(y),
                  'excluded_incomplete_windows': max(0, len(residuals) - lag) - len(y)}


def fit_nnar(residuals, steps, lag, nodes, config):
    X, y, audit = residual_windows(residuals, lag)
    audit.update(lag_window=lag, hidden_nodes=nodes, activation='logistic', output_activation='identity',
                 seed=config['seed'], repeats=[], selected_seed=None)
    if len(y) < 52:
        return None, {**audit, 'reason': 'Hybrid unavailable — insufficient complete NNAR residual windows.'}
    if not np.isfinite(residuals[-lag:]).all():
        return None, {**audit, 'reason': 'Terminal residual lag window contains missing observations.'}
    scaler = StandardScaler().fit(X)
    scaled = scaler.transform(X)
    valid = []
    for repeat in range(5):
        report('NNAR initialization', repeat, 5, f'Lag {lag}; hidden nodes {nodes}; initialization {repeat + 1}/5')
        seed = config['seed'] + repeat
        evidence = {'seed': seed, 'status': 'unavailable'}
        audit['repeats'].append(evidence)
        try:
            network = MLPRegressor(hidden_layer_sizes=(nodes,), activation='logistic', solver=config['solver'],
                                   max_iter=config['nnar_maxiter'], alpha=config['alpha'], random_state=seed)
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter('always')
                network.fit(scaled, y)
            evidence['warnings'] = [str(w.message) for w in caught]
            if any('converg' in str(w.message).lower() for w in caught) or not np.isfinite(network.loss_):
                raise ValueError('NNAR fit did not converge to finite training loss.')
            evidence.update(status='available', training_loss=float(network.loss_))
            valid.append((float(network.loss_), seed, network))
        except Exception as exc:
            evidence['reason'] = str(exc)
    if not valid:
        return None, {**audit, 'reason': 'All five deterministic NNAR fits failed.'}
    loss, seed, network = min(valid, key=lambda r: (r[0], r[1]))
    audit.update(selected_seed=seed, training_loss=loss)
    history, path = list(residuals), []
    for _ in range(steps):
        try:
            value = float(network.predict(scaler.transform([history[-lag:][::-1]]))[0])
        except Exception as exc:
            return None, {**audit, 'reason': 'NNAR recursive prediction failed: ' + str(exc)}
        if not np.isfinite(value):
            return None, {**audit, 'reason': 'NNAR generated a nonfinite recursive forecast.'}
        path.append(value)
        history.append(value)
    return np.asarray(path), audit
