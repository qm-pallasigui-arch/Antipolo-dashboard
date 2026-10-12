"""Configurable weekly SARIMA–NNAR, with no implicit statistical protocol."""
import json
import time
import warnings
from copy import deepcopy

import numpy as np
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler
from statsmodels.stats.diagnostic import acorr_ljungbox
from statsmodels.tsa.statespace.sarimax import SARIMAX
from statsmodels.tsa.stattools import acf, adfuller, pacf

from dashboard.logging_config import get_logger
from dashboard.modeling.metrics import compute_metrics
from dashboard.weekly.data import digest, now
from dashboard.weekly.protocol import WEEK53_NOTICE
from dashboard.weekly import registry
from dashboard.weekly.preparedness import summarize

logger = get_logger(__name__)

VERSION = 'weekly-3-tvt'
HORIZON = 52
PENDING_CONFIG = {
    'version': 'pending', 'approved': False, 'approval_reference': None,
    'candidates': [], 'nnar_lags': [], 'hidden_nodes': None,
    'minimum_training_weeks': None, 'minimum_residual_examples': None,
    'residual_burn': None, 'diagnostic_lag': None, 'holdout_weeks': None,
    'missing_policy': 'state_space', 'week53_policy': 'pending',
    'maxiter': 300, 'nnar_maxiter': 2000, 'alpha': 1.0, 'seed': 42,
    'uncertainty_method': None,
}


def resolve_disease(config, disease):
    """Reduce an optional per-disease protocol to a single flat one.

    An offline residual search selects a different SARIMA specification and a
    different NNAR size per disease, because whether the residual network helps
    depends on the series. Both `candidates` and `nnar` may therefore be keyed
    by disease label. Anything not keyed stays exactly as supplied, so the
    existing single-protocol configuration format is unchanged.
    """
    if not isinstance(config, dict):
        return config
    resolved = dict(config)
    for field in ('candidates', 'nnar'):
        value = resolved.get(field)
        if field == 'nnar' and isinstance(value, dict) and 'lags' in value:
            continue
        if not isinstance(value, dict):
            continue
        if disease is None:
            raise ValueError(
                f'The protocol specifies {field} per disease, so the selected disease is '
                'required. Supply an explicit disease selection before forecasting.')
        if disease not in value:
            # An explicit `default` keeps untuned diseases working under the
            # general protocol instead of failing outright.
            if 'default' in value:
                resolved[field] = value['default']
                continue
            raise ValueError(
                f'No {field} specification is defined for {disease!r}. '
                f'Defined for: {", ".join(sorted(value))}.')
        resolved[field] = value[disease]
    nnar = resolved.get('nnar')
    if isinstance(nnar, dict) and nnar:
        # The NNAR stage consumes discrete lags and one hidden width.
        if 'lags' in nnar:
            resolved['nnar_lags'] = nnar['lags']
        if 'hidden_nodes' in nnar:
            resolved['hidden_nodes'] = nnar['hidden_nodes']
    return resolved


def validate_config(config, disease=None):
    c = {**PENDING_CONFIG, **resolve_disease(config, disease)}
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
    # Legacy protocol files may name the removed provisional interval. Ignore it.
    c['uncertainty_method'] = None
    c['holdout_weeks'] = HORIZON
    c['validation_weeks'] = HORIZON
    if c['approved'] and not c['approval_reference']:
        raise ValueError('Approved protocols need an approval reference.')
    return c


def advance(pair, lengths):
    year, week = pair
    last = lengths.get(str(year))
    if last is None:
        raise ValueError(f'Reporting calendar for {year} is required to label cross-year forecast weeks.')
    return (year + 1, 1) if week >= last else (year, week + 1)


def training_series(dataset, disease, include_trailing=False):
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
    end = max((r['year'], r['morbidity_week']) for r in (rows if include_trailing else observed))
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
    started = time.monotonic()
    observed = int(np.isfinite(values).sum())
    logger.info('fitting %d SARIMA candidates on %d weeks (%d observed, %d missing), horizon=%d',
                len(c['candidates']), values.size, observed, int(np.isnan(values).sum()), steps)
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
    for position, candidate in enumerate(c['candidates'], start=1):
        label = f"{tuple(candidate['order'])}x{tuple(candidate['seasonal_order'])}"
        candidate_started = time.monotonic()
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
            logger.info('candidate %d/%d %s converged, AIC=%.2f, %.1fs',
                        position, len(c['candidates']), label, float(fit.aic), time.monotonic() - candidate_started)
        except Exception as exc:
            record['reason'] = str(exc)
            logger.warning('candidate %d/%d %s failed after %.1fs: %s',
                           position, len(c['candidates']), label, time.monotonic() - candidate_started, exc)
    result = {'hybrid': None, 'sarima': None, 'hybrid_status': 'Hybrid unavailable',
              'sarima_status': 'SARIMA-only unavailable', 'diagnostics': report, 'range': None}
    if not valid:
        logger.warning('no permitted SARIMA candidate produced a valid forecast (%.1fs total)', time.monotonic() - started)
        result['failure_reason'] = 'No permitted SARIMA candidate produced a valid forecast.'
        return result
    valid.sort(key=lambda v: v[0])
    result.update(sarima=np.maximum(0, valid[0][1]).tolist(), sarima_status='Available', sarima_configuration=valid[0][3])
    for _, prediction, residuals, record in valid:
        try:
            correction, notes = nnar(residuals, steps, c)
            hybrid = np.maximum(0, prediction + correction)
            result.update(hybrid=hybrid.tolist(), hybrid_status='Available', hybrid_configuration=record,
                          nnar_warnings=notes)
            logger.info('hybrid ready from SARIMA%sx%s in %.1fs total', tuple(record['order']), tuple(record['seasonal_order']), time.monotonic() - started)
            return result
        except Exception as exc:
            record['hybrid_failure'] = str(exc)
            logger.warning('NNAR stage failed for SARIMA%sx%s: %s', tuple(record['order']), tuple(record['seasonal_order']), exc)
    failures = [record.get('hybrid_failure', '') for _, _, _, record in valid]
    logger.warning('NNAR failed for every valid candidate (%.1fs total)', time.monotonic() - started)
    result['failure_reason'] = ('Hybrid unavailable — insufficient complete residual lag windows.'
                               if failures and all('residual lag window' in reason for reason in failures)
                               else 'NNAR failed for every permitted SARIMA candidate. See candidate diagnostics.')
    return result


def selection_key(dataset, disease, config):
    return registry.scope(dataset, disease, validate_config(config, disease), VERSION)


def cache_key(dataset, disease, config):
    key = selection_key(dataset, disease, config)
    saved = registry.operational_selection(dataset, disease, validate_config(config, disease), VERSION)
    return digest({'dataset': dataset['id'], 'scope': key,
                   'selection_run': saved.get('selection_run') if saved else None})


def boundaries(index):
    return {'start': list(index[0]), 'end': list(index[-1]), 'positions': len(index)} if index else None


def split_history(values, index, c):
    if len(values) <= 104 or np.isfinite(values[:-104]).sum() < c['minimum_training_weeks']:
        raise ValueError('Model selection unavailable — insufficient historical data. '
                         'Provide training history plus 52 validation and 52 final test positions.')
    return {'training': boundaries(index[:-104]), 'validation': boundaries(index[-104:-52]),
            'final_test': boundaries(index[-52:])}


def configuration_options(c):
    networks = c.get('nnar_candidates') or [{'lags': c['nnar_lags'], 'hidden_nodes': c['hidden_nodes']}]
    if not isinstance(networks, list) or len(c['candidates']) * len(networks) > 64:
        raise ValueError('Supply at most 64 explicit SARIMA/NNAR configuration combinations.')
    for candidate in c['candidates']:
        for network in networks:
            option = {**c, 'candidates': [candidate], 'nnar_lags': network['lags'],
                      'hidden_nodes': network['hidden_nodes']}
            # Per-disease nnar mapping has already been resolved; do not let it
            # override an explicitly enumerated network.
            option.pop('nnar', None)
            option.pop('nnar_candidates', None)
            yield validate_config(option)


def fit_locked(values, steps, selected):
    """Fit only locked configurations; never search or substitute on failure."""
    fits = {}
    output = {'hybrid': None, 'sarima': None, 'hybrid_status': 'Hybrid unavailable',
              'sarima_status': 'SARIMA-only unavailable', 'diagnostics': {}, 'range': None}
    failures = []
    for name in ('sarima', 'hybrid'):
        configuration = selected.get(name)
        if configuration is None:
            failures.append(f'{name}: no valid configuration selected on validation.')
            continue
        key = digest(configuration)
        try:
            if key not in fits:
                fits[key] = fit_models(values, steps, configuration)
            fitted = fits[key]
            output[name] = fitted.get(name)
            output[name + '_status'] = fitted.get(name + '_status', 'Unavailable')
            output[name + '_configuration'] = fitted.get(name + '_configuration')
            output['diagnostics'][name] = fitted.get('diagnostics', {})
            if not output[name]:
                failures.append(f"{name}: " + fitted.get('failure_reason', 'Selected configuration could not be refitted.'))
        except Exception as exc:
            failures.append(f'{name}: selected configuration could not be refitted: {exc}')
    if failures:
        output['failure_reason'] = '; '.join(failures)
    return output


def select_configuration(values, index, c, disease):
    periods = split_history(values, index, c)
    actual = values[-104:-52]
    mask = np.isfinite(actual)
    if not mask.any():
        raise ValueError('Model selection unavailable — no reported validation observations.')
    winners, scores, diagnostics = {}, {}, []
    for ordinal, option in enumerate(configuration_options(c)):
        record = {'candidate': ordinal, 'configuration': option, 'metrics': {}}
        try:
            fitted = fit_models(values[:-104], 52, option)
            record['hybrid_status'] = fitted['hybrid_status']
            record['sarima_status'] = fitted['sarima_status']
            record['failure_reason'] = fitted.get('failure_reason')
            for name in ('hybrid', 'sarima'):
                if fitted.get(name) is None:
                    continue
                metrics = compute_metrics(actual[mask], np.asarray(fitted[name])[mask])
                record['metrics'][name] = metrics
                score = (metrics['rmse'], metrics['mae'], ordinal)
                if name not in scores or score < scores[name]:
                    scores[name], winners[name] = score, option
        except Exception as exc:
            record['failure_reason'] = str(exc)
        diagnostics.append(record)
    if not winners:
        raise ValueError('Model selection unavailable — no candidate produced a valid validation forecast.')
    return {'status': 'Locked', 'disease': disease, 'model_version': VERSION,
            'selection_date': now(), 'selection_run': digest({'at': now(), 'disease': disease, 'winners': winners}),
            'periods': periods, 'selected': winners, 'validation_candidates': diagnostics,
            'selection_rule': 'Lowest validation RMSE; ties use MAE, then configured candidate order. Models selected independently.',
            'validation_scored_weeks': int(mask.sum()), 'validation_missing_actuals': int((~mask).sum()),
            'model_status': {name: 'Locked' if name in winners else 'Unavailable: no valid validation candidate'
                             for name in ('hybrid', 'sarima')},
            'performance': None}


def score_test(values, index, selected):
    fitted = fit_locked(values[:-52], 52, selected['selected'])
    actual, mask = values[-52:], np.isfinite(values[-52:])
    metrics = {name: compute_metrics(actual[mask], np.asarray(fitted[name])[mask])
               if mask.any() and fitted.get(name) is not None else None for name in ('hybrid', 'sarima')}
    available = any(metrics.values())
    evaluation = {'status': 'Retrospective evaluation' if available else 'Model performance unavailable',
                  'designation': 'Retrospective final test', 'periods': selected['periods'],
                  'period': [list(p) for p, usable in zip(index[-52:], mask) if usable],
                  'holdout_weeks': 52, 'validation_weeks': 52, 'scored_weeks': int(mask.sum()) if available else 0,
                  'excluded_missing_actuals': int((~mask).sum()),
                  'mape_valid_observations': int((mask & (actual != 0)).sum()),
                  'zero_actuals_excluded_from_mape': int((mask & (actual == 0)).sum()),
                  'hybrid_status': fitted['hybrid_status'], 'sarima_status': fitted['sarima_status'],
                  'failure_reason': fitted.get('failure_reason') if mask.any() else 'No reported final test observations.',
                  'diagnostics': fitted['diagnostics']}
    horizons = {}
    for horizon in (4, 13, 26, 52):
        scored = mask[:horizon]
        horizons[str(horizon)] = {
            'scored_weeks': int(scored.sum()), 'excluded_missing_actuals': int((~scored).sum()),
            'period': [list(p) for p, usable in zip(index[-52:][:horizon], scored) if usable],
            'metrics': {name: compute_metrics(actual[:horizon][scored], np.asarray(fitted[name])[:horizon][scored])
                        if scored.any() and fitted.get(name) is not None else None for name in ('hybrid', 'sarima')}}
    return {'evaluation': evaluation, 'metrics': metrics, 'horizon_metrics': horizons}


def deferred_evaluation(dataset, result):
    """Selection sees Training/Validation only; Test is scored after locking."""
    result = deepcopy(result)
    disease = result['disease']
    if result.get('dataset_id') != dataset['id']:
        raise ValueError('The performance request does not match the active dataset.')
    c = validate_config(result['configuration'], disease)
    values, index = training_series(dataset, disease, include_trailing=True)
    if any(w == 53 for _, w in index) and c['week53_policy'] == 'pending':
        raise ValueError('Week 53 treatment must be configured before model selection.')
    key = registry.scope(dataset, disease, c, VERSION)
    selected = registry.load(key)
    if not selected:
        selected = select_configuration(values, index, c, disease)
        selected['dataset_id'] = dataset['id']
        selected['scope'] = key
        selected['compatibility'] = registry.compatibility(dataset, disease, c, VERSION)
        # Commit the selection BEFORE any access to final-test outcomes.
        registry.save(key, selected)
    if not selected.get('performance') or selected['performance']['evaluation']['status'] != 'Retrospective evaluation':
        selected['performance'] = score_test(values, index, selected)
        registry.save(key, selected)
    result.update(deepcopy(selected['performance']))
    result['selection'] = {k: v for k, v in selected.items() if k not in ('performance', 'compatibility')}
    result['model_version'] = VERSION
    result['cache_key'] = cache_key(dataset, disease, c) if result.get('operational_selection_run') == selected['selection_run'] else None
    result['forecast_refresh_required'] = bool((result.get('hybrid') or result.get('sarima'))
                                               and result.get('operational_selection_run') != selected['selection_run'])
    if not result.get('hybrid') and not result.get('sarima'):
        result['failure_reason'] = 'Configuration locked. Choose Generate Forecast to fit all eligible history.'
    note = mape_scale_risk(result['metrics'])
    if note and note not in result['warnings']:
        result['warnings'].append(note)
    return result


def empty_result(dataset, disease, config):
    return {'model_version': VERSION, 'issued_at': None, 'dataset_id': dataset['id'],
            'disease': disease, 'metadata': dataset['metadata'],
            'context': 'Synthetic / Demo Data' if dataset['context'] == 'Synthetic / Demo Data' else 'Technical / Retrospective Evaluation',
            'designation': 'Operational future forecast',
            'eligible': dataset['eligible'], 'eligibility_reasons': dataset['eligibility_reasons'],
            'warnings': list(dataset['quality']['warnings']), 'configuration': config,
            'configuration_label': config.get('label', config.get('version', 'Unspecified protocol')),
            'hybrid': None, 'sarima': None, 'hybrid_status': 'Hybrid unavailable',
            'sarima_status': 'SARIMA-only unavailable', 'metrics': {}, 'horizon_metrics': {}, 'forecast_index': [],
            'evaluation': {'status': 'Pending', 'detail': 'Choose Compute Model Performance to select and evaluate configurations.'}}


def run(dataset, disease, config, defer_evaluation=True):
    """Operational forecasting never selects models. Explicit evaluation is separate."""
    result = empty_result(dataset, disease, config)
    try:
        c = validate_config(config, disease)
        result['configuration'] = c
        values, index = training_series(dataset, disease)
        if not defer_evaluation:
            result = deferred_evaluation(dataset, result)
        selected = registry.operational_selection(dataset, disease, c, VERSION)
        if not selected:
            raise ValueError('No compatible locked configuration. Choose Compute Model Performance first.')
        if any(week == 53 for _, week in index) and c['week53_policy'] == 'pending':
            raise ValueError('Week 53 treatment must be configured before modeling.')
        result['training_index'] = [list(p) for p in index]
        result['training_observed_count'] = int(np.isfinite(values).sum())
        result['operational_training_period'] = boundaries(index)
        point = index[-1]
        for offset in range(1, HORIZON + 1):
            try:
                point = advance(point, dataset['metadata'].get('year_lengths', {})) if point else None
            except ValueError:
                point = None
            result['forecast_index'].append({'horizon_week': offset, 'year': point[0] if point else None,
                                             'morbidity_week': point[1] if point else None})
        if any(p['year'] is None for p in result['forecast_index']):
            result['warnings'].append('Future reporting calendar unresolved: affected predictions use horizon offsets.')
        result.pop('failure_reason', None)
        result.update(fit_locked(values, HORIZON, selected['selected']))
        result['issued_at'] = now()
        result['selection'] = {k: v for k, v in selected.items() if k not in ('performance', 'compatibility')}
        result['operational_selection_run'] = selected['selection_run']
        result['operational_configurations'] = deepcopy(selected['selected'])
        if selected.get('performance'):
            result.update(deepcopy(selected['performance']))
        if selected['scope'] != registry.scope(dataset, disease, c, VERSION):
            result['warnings'].append('Using a locked configuration from unchanged earlier history. '
                                      'Historical performance describes the saved test period; '
                                      'Compute Model Performance develops and evaluates the current dataset separately.')
        result['cache_key'] = cache_key(dataset, disease, c)
        result['preparedness'] = summarize(result, values)
        if not c['approved']:
            result['warnings'].append('Model protocol is exploratory; outputs are not final thesis evidence.')
        if c['version'] == 'exploratory-weekly-v0.1':
            result['warnings'].append(WEEK53_NOTICE)
    except Exception as exc:
        result['failure_reason'] = str(exc)
        result['warnings'].append(str(exc))
        logger.warning('forecast unavailable for %r: %s', disease, exc)
    return json.loads(json.dumps(result, allow_nan=False))


MAPE_SCALE_FLOOR = 10
MAPE_SCALE_SHARE = 0.25


def mape_scale_risk(metrics, floor=MAPE_SCALE_FLOOR, share=MAPE_SCALE_SHARE):
    """Warn when MAPE's denominators are small enough to distort the percentage.

    This is a risk note, not a verdict: MAPE degrades as the model's absolute
    error becomes comparable to the denominator, so a low-count series can post a
    large percentage even for a close forecast. Both the typical nonzero count
    and the seasonal low are reported, because a healthy median can still hide a
    thin off-season. MAE and RMSE stay in cases and are unaffected.
    """
    scored = [m for m in (metrics or {}).values() if m]
    if not scored or any(m.get('mape') is None for m in scored):
        return None
    median = max(m['mape_median_actual'] for m in scored)
    p10 = max(m['mape_p10_actual'] for m in scored)
    if median >= floor and p10 >= MAPE_SCALE_FLOOR / 2:
        return None
    if p10 < MAPE_SCALE_FLOOR / 2:
        basis = (f'the 10th-percentile nonzero weekly count is {p10:g} and the median is {median:g}')
    else:
        basis = f'the median nonzero weekly count is {median:g}'
    return (f'MAPE is at risk for this disease: {basis}, so the percentage can be dominated '
            f"by single-case differences. Interpret MAE and RMSE alongside it; they stay in cases.")


def interpretation(result, horizon):
    summary = (result or {}).get('preparedness') or {}
    return summary.get('text', 'Preparedness interpretation unavailable until a valid future forecast is generated.')
