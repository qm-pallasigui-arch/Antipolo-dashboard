"""Configurable weekly SARIMA–NNAR, with no implicit statistical protocol."""
import json
import warnings

import numpy as np
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler
from statsmodels.stats.diagnostic import acorr_ljungbox
from statsmodels.tsa.statespace.sarimax import SARIMAX
from statsmodels.tsa.stattools import acf, adfuller, pacf

from dashboard.modeling.metrics import compute_metrics
from dashboard.weekly.data import digest, now
from dashboard.weekly.protocol import WEEK53_NOTICE

VERSION = 'weekly-3-decision90'
HORIZON = 52
PENDING_CONFIG = {
    'version': 'pending', 'approved': False, 'approval_reference': None,
    'candidates': [], 'nnar_lags': [], 'hidden_nodes': None,
    'minimum_training_weeks': None, 'minimum_residual_examples': None,
    'residual_burn': None, 'diagnostic_lag': None, 'holdout_weeks': None,
    'missing_policy': 'state_space', 'week53_policy': 'pending',
    'maxiter': 300, 'nnar_maxiter': 2000, 'alpha': 1.0, 'seed': 42,
    'uncertainty_method': 'training_residual_rmse',
}


def validate_config(config):
    if config.get('version') == 'weekly-decision-90-v1':
        from dashboard.weekly.selection import validate_configuration
        return validate_configuration(config)
    c = {**PENDING_CONFIG, **config}
    if not c['candidates']:
        raise ValueError('Weekly SARIMA candidate specification is pending. Supply an explicit protocol.')
    if not isinstance(c['candidates'], list) or len(c['candidates']) > 64:
        raise ValueError('Supply at most 64 explicitly permitted SARIMA candidates.')
    for candidate in c['candidates']:
        for key, length in [('order', 3), ('seasonal_order', 4)]:
            values = candidate.get(key, [])
            if len(values) != length or any(type(x) is not int or x < 0 for x in values):
                raise ValueError('Each candidate needs non-negative integer order[3] and seasonal_order[4].')
        seasonal = candidate['seasonal_order']
        if seasonal[-1] == 1 or (any(seasonal[:3]) and seasonal[-1] < 2):
            raise ValueError('Seasonal terms need an explicit period of at least two.')
    for key in ['hidden_nodes', 'minimum_training_weeks', 'minimum_residual_examples', 'diagnostic_lag', 'maxiter', 'nnar_maxiter']:
        if type(c[key]) is not int or c[key] < 1:
            raise ValueError(f'{key} must be explicitly supplied as a positive integer.')
    if type(c['residual_burn']) is not int or c['residual_burn'] < 0:
        raise ValueError('An explicit non-negative residual_burn is required.')
    if not isinstance(c['nnar_lags'], list) or not c['nnar_lags'] or any(type(x) is not int or x < 1 for x in c['nnar_lags']):
        raise ValueError('Explicit positive weekly NNAR lags are required.')
    if c['missing_policy'] not in ('state_space', 'reject'):
        raise ValueError('Missing policy must be state_space (no imputation) or reject.')
    if c['week53_policy'] not in ('pending', 'preserve_sequence'):
        raise ValueError('Week 53 may only be retained in sequence; no remapping is supported.')
    if c['holdout_weeks'] is not None and (type(c['holdout_weeks']) is not int or not 1 <= c['holdout_weeks'] <= HORIZON):
        raise ValueError('Optional retrospective holdout must be 1–52 weeks.')
    if c['uncertainty_method'] != 'training_residual_rmse':
        raise ValueError('Only provisional training_residual_rmse is implemented.')
    if c['approved'] and not c['approval_reference']:
        raise ValueError('Approved protocols need an approval reference.')
    return c


def advance(pair, lengths):
    year, week = pair
    last = lengths.get(str(year))
    if last is None:
        raise ValueError(f'Reporting calendar for {year} is required to label cross-year forecast weeks.')
    return (year + 1, 1) if week >= last else (year, week + 1)


def training_series(dataset, disease):
    rows = [r for r in dataset['records'] if r['disease'] == disease]
    if not rows:
        raise ValueError('Selected disease has no observations.')
    metadata = dataset['metadata']
    if metadata.get('frequency') != 'weekly':
        raise ValueError('The operational model requires weekly observations.')
    if dataset['quality']['errors']:
        raise ValueError('Unresolved data validation errors.')
    complete = [r for r in rows if str(r.get('reporting_status') or metadata.get('reporting_status', '')).lower() == 'complete']
    observed = [r for r in complete if r['case_count'] is not None]
    if not observed:
        raise ValueError('No complete, reported weeks available for training.')
    start = min((r['year'], r['morbidity_week']) for r in rows)
    end = max((r['year'], r['morbidity_week']) for r in complete)
    lookup = {(r['year'], r['morbidity_week']): r['case_count'] for r in complete}
    index, values, point = [], [], start
    lengths = metadata.get('year_lengths', {})
    while point <= end:
        index.append(point)
        value = lookup.get(point)
        values.append(float(value) if value is not None else np.nan)
        if point == end:
            break
        if point[0] == end[0]:
            point = (point[0], point[1] + 1)
        else:
            point = advance(point, lengths)
    return np.asarray(values), index


def nnar(residuals, steps, c):
    """Use only actual contiguous lag positions; never compress across gaps."""
    lags = c['nnar_lags']
    X, y = [], []
    for i in range(max(lags), len(residuals)):
        window = [residuals[i - lag] for lag in lags]
        if np.isfinite(window).all() and np.isfinite(residuals[i]):
            X.append(window)
            y.append(residuals[i])
    if len(y) < c['minimum_residual_examples']:
        raise ValueError('Insufficient complete residual lag windows; no imputation was performed.')
    if not np.isfinite(residuals[-max(lags):]).all():
        raise ValueError('Terminal residual lag window contains missing observations.')
    scaler = StandardScaler().fit(X)
    network = MLPRegressor(hidden_layer_sizes=(c['hidden_nodes'],), solver='lbfgs',
                           max_iter=c['nnar_maxiter'], alpha=c['alpha'], random_state=c['seed'])
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        network.fit(scaler.transform(X), y)
    notes = [str(w.message) for w in caught]
    if any('converg' in str(w.message).lower() for w in caught):
        raise ValueError('NNAR optimizer did not converge: ' + '; '.join(notes))
    history, predicted = list(residuals), []
    for _ in range(steps):
        value = float(network.predict(scaler.transform([[history[-lag] for lag in lags]]))[0])
        if not np.isfinite(value):
            raise ValueError('NNAR generated a nonfinite value.')
        predicted.append(value)
        history.append(value)
    return np.array(predicted), notes


def fit_models(values, steps, c):
    report = {'candidates': [], 'stationarity': None, 'correlations': None}
    if np.isfinite(values).sum() < c['minimum_training_weeks']:
        raise ValueError('Insufficient complete observations under configured protocol.')
    if np.isnan(values).any() and c['missing_policy'] == 'reject':
        raise ValueError('Configured missing-value policy rejects gaps; no imputation performed.')
    if np.isfinite(values).all() and np.ptp(values) > 0:
        try:
            report['stationarity'] = {'adf_pvalue': float(adfuller(values, autolag='AIC')[1])}
            lag = min(c['diagnostic_lag'], len(values) // 2 - 1)
            report['correlations'] = {'acf': acf(values, nlags=lag).tolist(), 'pacf': pacf(values, nlags=lag).tolist()}
        except ValueError as exc:
            report['assessment_reason'] = str(exc)
    else:
        report['assessment_reason'] = 'ADF/ACF/PACF unavailable for gapped or constant series; no gaps compressed.'
    valid = []
    for candidate in c['candidates']:
        record = {**candidate, 'status': 'unavailable', 'converged': None, 'aic': None,
                  'residual_diagnostic_notice': 'Unavailable: candidate not yet fitted.'}
        report['candidates'].append(record)
        try:
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter('always')
                fit = SARIMAX(values, order=candidate['order'], seasonal_order=candidate['seasonal_order'],
                              trend=candidate.get('trend', 'n'), loglikelihood_burn=c['residual_burn'],
                              enforce_stationarity=True, enforce_invertibility=True).fit(disp=False, maxiter=c['maxiter'])
            record['warnings'] = [str(w.message) for w in caught]
            record['converged'] = bool(fit.mle_retvals.get('converged', False))
            record['aic'] = float(fit.aic) if np.isfinite(fit.aic) else None
            if not fit.mle_retvals.get('converged', False) or not np.isfinite(fit.aic):
                raise ValueError('SARIMA did not converge to a finite AIC.')
            prediction = np.asarray(fit.forecast(steps))
            if not np.isfinite(prediction).all():
                raise ValueError('Nonfinite SARIMA forecast.')
            residuals = values - np.asarray(fit.fittedvalues)
            residuals[:c['residual_burn']] = np.nan
            valid_residuals = residuals[c['residual_burn']:]
            if np.isfinite(valid_residuals).all() and len(valid_residuals) > c['diagnostic_lag']:
                lb = acorr_ljungbox(valid_residuals, lags=[c['diagnostic_lag']], return_df=True)
                probability = float(lb.lb_pvalue.iloc[0])
                record['ljung_box_pvalue'] = probability if np.isfinite(probability) else None
                record.pop('residual_diagnostic_notice', None)
            else:
                record['residual_diagnostic_notice'] = 'Ljung–Box unavailable with gaps or insufficient residuals.'
            record.update(status='available', aic=float(fit.aic), fitted_parameters=dict(zip(fit.param_names, map(float, fit.params))))
            valid.append((float(fit.aic), prediction, residuals, record))
        except Exception as exc:
            record['reason'] = str(exc)
    result = {'hybrid': None, 'sarima': None, 'hybrid_status': 'Hybrid unavailable',
              'sarima_status': 'SARIMA-only unavailable', 'diagnostics': report, 'range': None}
    if not valid:
        result['failure_reason'] = 'No permitted SARIMA candidate produced a valid forecast.'
        return result
    valid.sort(key=lambda v: v[0])
    result.update(sarima=np.maximum(0, valid[0][1]).tolist(), sarima_status='Available', sarima_configuration=valid[0][3])
    for _, prediction, residuals, record in valid:
        try:
            correction, notes = nnar(residuals, steps, c)
            hybrid = np.maximum(0, prediction + correction)
            # Deliberately provisional scale, not a calibrated coverage interval.
            scale = float(np.sqrt(np.nanmean(residuals ** 2)))
            result.update(hybrid=hybrid.tolist(), hybrid_status='Available', hybrid_configuration=record,
                          nnar_warnings=notes, range={'lower': np.maximum(0, hybrid - scale).tolist(),
                          'upper': (hybrid + scale).tolist(), 'method': 'Hybrid ± training SARIMA residual RMSE, lower clipped at zero; provisional, uncalibrated.'})
            return result
        except Exception as exc:
            record['hybrid_failure'] = str(exc)
    failures = [record.get('hybrid_failure', '') for _, _, _, record in valid]
    result['failure_reason'] = ('Hybrid unavailable — insufficient complete residual lag windows.'
                               if failures and all('residual lag window' in reason for reason in failures)
                               else 'NNAR failed for every permitted SARIMA candidate. See candidate diagnostics.')
    return result


def cache_key(dataset, disease, config):
    return digest({'dataset': dataset['id'], 'records': dataset['records'], 'metadata': dataset['metadata'],
                   'disease': disease, 'model_version': VERSION, 'config': config})


def run(dataset, disease, config):
    if not dataset or not dataset.get('records'):
        return {'hybrid': None, 'sarima': None, 'hybrid_status': 'Hybrid unavailable',
                'sarima_status': 'SARIMA-only unavailable', 'metrics': {},
                'failure_reason': 'Forecast unavailable — no validated Active Dataset is currently selected.'}
    result = {'model_version': VERSION, 'issued_at': now(), 'dataset_id': dataset['id'],
              'disease': disease, 'metadata': dataset['metadata'],
              'context': 'Synthetic / Demo Data' if dataset['context'] == 'Synthetic / Demo Data' else 'Technical / Retrospective Evaluation',
              'eligible': dataset['eligible'], 'eligibility_reasons': dataset['eligibility_reasons'],
              'warnings': list(dataset['quality']['warnings']), 'configuration': config,
              'configuration_label': config.get('label', config.get('version', 'Unspecified protocol')),
              'hybrid': None, 'sarima': None, 'hybrid_status': 'Hybrid unavailable',
              'sarima_status': 'SARIMA-only unavailable', 'metrics': {}, 'forecast_index': [],
              'evaluation': {'status': 'Not performed; weekly evaluation protocol pending.'}}
    result['cache_key'] = cache_key(dataset, disease, config)
    try:
        c = validate_config(config)
        result['configuration'] = c
        if c['approved'] and dataset['eligible']:
            result['context'] = 'Final Thesis Evaluation'
        if not c['approved']:
            result['warnings'].append('Model protocol is exploratory and pending adviser approval; outputs are not final thesis evidence.')
            result['context'] = 'Synthetic / Demo Data' if dataset['context'] == 'Synthetic / Demo Data' else 'Technical / Retrospective Evaluation'
        if c['version'] == 'exploratory-weekly-v0.1':
            result['warnings'].append(WEEK53_NOTICE)
        values, index = training_series(dataset, disease)
        if any(week == 53 for _, week in index) and c['week53_policy'] == 'pending':
            raise ValueError('Week 53 retained in source; configure its approved/exploratory sequential treatment before modeling.')
        result['training_index'] = [list(p) for p in index]
        result['training_observed_count'] = int(np.isfinite(values).sum())
        point = index[-1]
        for offset in range(1, HORIZON + 1):
            try:
                point = advance(point, dataset['metadata'].get('year_lengths', {})) if point else None
            except ValueError:
                point = None
            result['forecast_index'].append({'horizon_week': offset, 'year': point[0] if point else None,
                                             'morbidity_week': point[1] if point else None})
        if any(p['year'] is None for p in result['forecast_index']):
            result['warnings'].append('Future reporting calendar unresolved: affected predictions use horizon offsets, without invented year/week labels.')
        if c['version'] == 'weekly-decision-90-v1':
            from dashboard.weekly.evaluation import execute
            result.update(execute(values, index, c))
            result['warnings'].extend(result.pop('protocol_warnings', []))
            return json.loads(json.dumps(result, allow_nan=False))
        result.update(fit_models(values, HORIZON, c))
        holdout = c['holdout_weeks']
        result['evaluation'] = {'status': 'Not performed: no retrospective holdout configured.'}
        if holdout:
            if len(values) <= holdout:
                raise ValueError('Not enough weekly history for the configured holdout.')
            evaluation = fit_models(values[:-holdout], holdout, c)
            actual = values[-holdout:]
            mask = np.isfinite(actual)
            period = [list(p) for p, usable in zip(index[-holdout:], mask) if usable]
            result['evaluation'] = {'status': 'Retrospective evaluation', 'period': period,
                                    'holdout_weeks': holdout, 'scored_weeks': int(mask.sum()),
                                    'excluded_missing_actuals': int((~mask).sum()),
                                    'hybrid_status': evaluation['hybrid_status'], 'sarima_status': evaluation['sarima_status'],
                                    'diagnostics': evaluation['diagnostics']}
            for model in ['hybrid', 'sarima']:
                result['metrics'][model] = compute_metrics(actual[mask], np.asarray(evaluation[model])[mask]) if mask.any() and evaluation[model] is not None else None
            result['horizon_metrics'] = {}
            for horizon in (4, 13, 26, 52):
                if holdout < horizon:
                    continue
                scored = mask[:horizon]
                result['horizon_metrics'][str(horizon)] = {
                    'scored_weeks': int(scored.sum()), 'excluded_missing_actuals': int((~scored).sum()),
                    'period': [list(p) for p, usable in zip(index[-holdout:][:horizon], scored) if usable],
                    'metrics': {name: compute_metrics(actual[:horizon][scored], np.asarray(evaluation[name])[:horizon][scored])
                                if scored.any() and evaluation[name] is not None else None for name in ['hybrid', 'sarima']}}
    except Exception as exc:
        result['failure_reason'] = str(exc)
        if result['evaluation']['status'] != 'Retrospective evaluation':
            result['evaluation'] = {'status': 'Not performed: ' + str(exc)}
        result['warnings'].append(str(exc))
    # Enforce strict JSON, so nonfinite diagnostic values cannot leak into stores/exports.
    return json.loads(json.dumps(result, allow_nan=False))


def interpretation(result, horizon):
    values = (result.get('hybrid') or [])[:horizon]
    if not values:
        return 'Hybrid unavailable. A projection could not be generated with the current data and protocol.'
    peak = int(np.argmax(values)) + 1
    point = result['forecast_index'][peak - 1]
    label = f"{point['year']} morbidity week {point['morbidity_week']}" if point['year'] else f'forecast week +{peak}'
    prefix = 'Demo projection. ' if result['context'] == 'Synthetic / Demo Data' else ''
    return prefix + f'The highest projected count in this view is around {label}. This is a model-based projection and should be interpreted together with current surveillance data.'
