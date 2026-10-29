"""Configurable weekly SARIMA–NNAR, with no implicit statistical protocol."""
import json
import time

import numpy as np
from dashboard.weekly.estimators import VERSION, adf_diagnostic, fit_sarima, nnar
from dashboard.weekly.selection import chronological_split, score_cases, verify_lock, require_research_data, selection_fingerprint

from dashboard.logging_config import get_logger
from dashboard.modeling.metrics import compute_metrics
from dashboard.weekly.data import digest, now
from dashboard.weekly.protocol import WEEK53_NOTICE

logger = get_logger(__name__)

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
    c = dict(config) if config.get('version') == VERSION else {**PENDING_CONFIG, **resolve_disease(config, disease)}
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
    if c['uncertainty_method'] not in ('none', 'training_residual_rmse'):
        raise ValueError('Unsupported uncertainty method.')
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


def fit_models(values, steps, c, progress=None):
    """Fit exactly one locked specification; never select or substitute at runtime."""
    emit = progress or (lambda stage, message: None)
    result = {'hybrid': None, 'sarima': None, 'hybrid_status': 'Hybrid unavailable',
              'sarima_status': 'SARIMA-only unavailable', 'range': None,
              'diagnostics': {'candidates': [], 'stationarity': adf_diagnostic(values)}}
    if len(c['candidates']) != 1:
        raise ValueError('A single locked SARIMA configuration is required; run offline selection first.')
    if c.get('version') == VERSION:
        verify_lock(c)
    try:
        emit('sarima', 'Fitting SARIMA on the prepared historical observations.')
        prediction, residuals, record = fit_sarima(values, steps, c['candidates'][0], c)
        result['diagnostics']['candidates'].append(record)
        result.update(sarima=np.maximum(0, prediction).tolist(), sarima_status='Available', sarima_configuration=record)
        emit('residuals', 'SARIMA fit completed. Post-initialization residuals prepared; missing positions preserved.')
        emit('nnar', 'Fitting the NNAR residual model.')
        correction, notes = nnar(residuals, steps, c, progress=progress) if progress else nnar(residuals, steps, c)
        emit('combine', 'Combining SARIMA forecasts and NNAR residual corrections.')
        hybrid = np.maximum(0, prediction + correction)
        result.update(hybrid=hybrid.tolist(), hybrid_status='Available', hybrid_configuration=record, nnar_warnings=notes)
        result['components'] = {'raw_sarima': prediction.tolist(), 'nnar_correction': correction.tolist(),
                                'hybrid': hybrid.tolist(), 'formula': 'max(0, raw_sarima + nnar_correction)'}
    except Exception as exc:
        logger.exception('Weekly model fitting failed')
        # Only known model-domain errors are suitable for the user-facing log.
        result['failure_reason'] = str(exc) if isinstance(exc, ValueError) else 'Model fitting failed. See the server log for technical details.'
    return result


def cache_key(dataset, disease, config):
    return digest({'dataset': dataset['id'], 'records': dataset['records'], 'metadata': dataset['metadata'],
                   'disease': disease, 'model_version': VERSION, 'config': config})


def retrospective_evaluation(result, values, index, c, disease, progress=None):
    """Refit the lock on training + validation, then score the final 52 positions.

    This explicit workflow is deferred by the operational UI. It cannot select
    parameters, change the lock, or redefine the original historical boundaries.
    """
    emit = progress or (lambda stage, message: None)
    emit('configuration', 'Loading locked configuration for historical evaluation.')
    verify_lock(c)
    before = digest(c)
    train, validation, test, periods = chronological_split(values, index)
    if periods != c['periods']:
        raise ValueError('Historical evaluation requires the original selection periods.')
    if selection_fingerprint(train, validation) != c['selection_data_fingerprint']:
        raise ValueError('Training or validation data changed since configuration selection.')
    emit('split', 'Training, validation and final-test boundaries prepared.')
    holdout = 52
    emit('refit', 'Refitting locked models on training plus validation.')
    evaluation = fit_models(values[:-holdout], holdout, c, progress=progress)
    if evaluation['hybrid'] is None:
        raise ValueError(evaluation.get('failure_reason', 'Locked configuration could not be refitted.'))
    emit('test', 'Final-test forecasts generated without using final-test observations.')
    actual = values[-holdout:]
    mask = np.isfinite(actual)
    period = [list(p) for p, usable in zip(index[-holdout:], mask) if usable]
    result['evaluation'] = {'status': 'Retrospective evaluation', 'period': period,
                            'holdout_weeks': holdout, 'scored_weeks': int(mask.sum()),
                            'excluded_missing_actuals': int((~mask).sum()),
                            'hybrid_status': evaluation['hybrid_status'], 'sarima_status': evaluation['sarima_status'],
                            'diagnostics': evaluation['diagnostics'], 'periods': periods,
                            'configuration_hash_before': before, 'configuration_hash_after': digest(c)}
    for model in ['hybrid', 'sarima']:
        emit('metrics_' + model, 'Computing ' + model + ' final-test metrics.')
        result['metrics'][model] = score_cases(actual, evaluation[model])
    coverage = result['metrics']['hybrid']
    if coverage['zero_actuals_excluded_from_mape']:
        result['warnings'].append(f"MAPE excludes {coverage['zero_actuals_excluded_from_mape']} zero-actual weeks.")
    result['evaluation']['actual'] = [float(v) if np.isfinite(v) else None for v in actual]
    result['evaluation']['predictions'] = {name: evaluation[name] for name in ('hybrid', 'sarima')}
    result['evaluation']['index'] = [list(p) for p in index[-holdout:]]
    result['evaluation']['components'] = evaluation.get('components', {})
    if before != digest(c):
        raise ValueError('Final test modified the locked configuration.')
    note = mape_scale_risk(result['metrics'])
    if note:
        result['warnings'].append(note)
        logger.info('MAPE scale risk for %r: %s', disease, note)
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
    return result


def deferred_evaluation(dataset, result, progress=None):
    """Score a forecast whose retrospective evaluation was deferred at run time.

    Rebuilds the training series from the dataset rather than storing it twice;
    reconstructing is cheap because no fitting happens, and a stored series
    could disagree with the one run() actually used.
    """
    disease = result['disease']
    if result['configuration'].get('validation_scope') == 'provisional':
        raise ValueError('Provisional performance is included in Run Provisional Model Validation; it is not research-validated.')
    require_research_data(dataset, disease)
    values, index = training_series(dataset, disease)
    return retrospective_evaluation(result, values, index, result['configuration'], disease, progress=progress)

def run(dataset, disease, config, defer_evaluation=False, progress=None, sample=False):
    emit = progress or (lambda stage, message: None)
    started = time.monotonic()
    logger.info('forecast requested: disease=%r dataset=%s records=%d protocol=%r',
                disease, str(dataset['id'])[:12], len(dataset['records']), config.get('version'))
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
        emit('validation' if sample else 'configuration',
             'Checking sample data quality.' if sample else 'Checking for a validated disease model configuration.')
        modeling_dataset = dataset
        if sample:
            from dashboard.weekly.sample import sample_configuration, prepare_sample
            if config != sample_configuration():
                raise ValueError('Sample mode requires the explicit demonstration preset.')
            modeling_dataset, sample_notes = prepare_sample(dataset)
            result.update(context='Quick Preview — Fixed Settings — Unvalidated demonstration forecast', eligible=False,
                          model_version=config['version'], sample_forecast=True, sample_assumptions=sample_notes)
            result['warnings'].extend(sample_notes)
        if 'configurations' in config:
            config = config['configurations'].get(disease)
            if not config:
                raise ValueError('No validated locked model configuration is currently available for this disease.')
        if not sample:
            if config.get('validation_scope') == 'provisional':
                raise ValueError('A provisional configuration cannot be used as a research-validated configuration.')
            verify_lock(config)
            emit('validation', 'Checking dataset eligibility.')
            require_research_data(dataset, disease)
        emit('configuration', 'Loading disease model configuration.')
        c = validate_config(config, disease)
        result['configuration'] = c
        logger.info('protocol resolved for %r: %d candidate(s), nnar_lags=%s, hidden_nodes=%s',
                    disease, len(c['candidates']), c['nnar_lags'], c['hidden_nodes'])
        if c['approved'] and dataset['eligible']:
            result['context'] = 'Final Thesis Evaluation'
        if not c['approved'] and not sample:
            result['warnings'].append('Model protocol is exploratory and pending adviser approval; outputs are not final thesis evidence.')
            result['context'] = 'Synthetic / Demo Data' if dataset['context'] == 'Synthetic / Demo Data' else 'Technical / Retrospective Evaluation'
        if c['version'] == 'exploratory-weekly-v0.1':
            result['warnings'].append(WEEK53_NOTICE)
        emit('history', 'Preparing chronological weekly history.')
        values, index = training_series(modeling_dataset, disease)
        if np.isnan(values).any():
            result['warnings'].append(f'{int(np.isnan(values).sum())} historical observations are missing and preserved as missing.')
        if any(week == 53 for _, week in index) and c['week53_policy'] == 'pending':
            raise ValueError('Week 53 retained in source; configure its approved/exploratory sequential treatment before modeling.')
        result['training_index'] = [list(p) for p in index]
        result['training_observed_count'] = int(np.isfinite(values).sum())
        point = index[-1]
        for offset in range(1, HORIZON + 1):
            try:
                point = advance(point, modeling_dataset['metadata'].get('year_lengths', {})) if point else None
            except ValueError:
                point = None
            result['forecast_index'].append({'horizon_week': offset, 'year': point[0] if point else None,
                                             'morbidity_week': point[1] if point else None})
        if any(p['year'] is None for p in result['forecast_index']):
            result['warnings'].append('Future reporting calendar unresolved: affected predictions use horizon offsets, without invented year/week labels.')
        result.update(fit_models(values, HORIZON, c, progress=progress) if progress else fit_models(values, HORIZON, c))
        for record in result.get('diagnostics', {}).get('candidates', []):
            for diagnostic in record.get('ljung_box', []):
                if diagnostic['status'] == 'unavailable':
                    result['warnings'].append(f"Ljung–Box diagnostic at lag {diagnostic['lag']} unavailable: {diagnostic['reason']}")
        if result['hybrid'] is None:
            raise ValueError(result.get('failure_reason', 'Hybrid forecast unavailable.'))
        if sample:
            result['evaluation'] = {'status': 'Not performed: sample preset is not research validated.',
                                    'detail': 'Sample mode demonstrates forecasting; it does not report benchmark accuracy.'}
            result['horizon_metrics'] = {}
        elif defer_evaluation:
            result['evaluation'] = {'status': 'Pending', 'holdout_weeks': c['holdout_weeks'],
                                    'detail': 'Retrospective performance has not been computed for this forecast.'}
            result['horizon_metrics'] = {}
        else:
            retrospective_evaluation(result, values, index, c, disease, progress=progress)
    except Exception as exc:
        result['failure_reason'] = str(exc)
        if result['evaluation']['status'] != 'Retrospective evaluation':
            result['evaluation'] = {'status': 'Not performed: ' + str(exc)}
        logger.warning('forecast failed for %r after %.1fs: %s', disease, time.monotonic() - started, exc)
    else:
        logger.info('forecast complete for %r in %.1fs: hybrid=%s sarima=%s',
                    disease, time.monotonic() - started,
                    result.get('hybrid_status'), result.get('sarima_status'))
    # Enforce strict JSON, so nonfinite diagnostic values cannot leak into stores/exports.
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
    values = (result.get('hybrid') or [])[:horizon]
    if not values:
        return 'Hybrid unavailable. A projection could not be generated with the current data and protocol.'
    peak = int(np.argmax(values)) + 1
    point = result['forecast_index'][peak - 1]
    label = f"{point['year']} morbidity week {point['morbidity_week']}" if point['year'] else f'forecast week +{peak}'
    prefix = 'Demo projection. ' if result['context'] == 'Synthetic / Demo Data' else ''
    return prefix + f'The highest projected count in this view is around {label} ({values[peak - 1]:,.1f} projected cases). This is a model-based projection and should be interpreted together with current surveillance data.'
