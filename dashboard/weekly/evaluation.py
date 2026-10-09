"""Locked Decision 90 selection, retrospective evaluation, and operational refit."""
from copy import deepcopy
import json
import logging

import numpy as np

from dashboard.weekly import selection as s
from dashboard.weekly.data import digest, now
from dashboard.weekly.progress import report

logger = logging.getLogger(__name__)


def candidate_key(candidate):
    return str((tuple(candidate['order']), tuple(candidate['seasonal_order'])))


def period(index, start, end):
    return {'start': list(index[start]), 'end': list(index[end - 1]), 'positions': end - start}


def select(values, config, windows):
    """Only pre-holdout values are accepted. Union screening precedes fresh refits."""
    audit = {'screening': [], 'union': [], 'sarima_candidates': [], 'hybrid_candidates': []}
    union = {}
    for window_number, (start, end) in enumerate(windows, 1):
        records = []
        for number, candidate in enumerate(config['candidates'], 1):
            report('SARIMA screening', (window_number - 1) * len(config['candidates']) + number - 1,
                   len(windows) * len(config['candidates']),
                   f'Validation window {window_number}/3; candidate {number}/{len(config["candidates"])}')
            _, _, evidence = s.fit_sarima(values[:start], end - start, candidate, config)
            records.append(evidence)
        chosen = s.shortlist(records)
        audit['screening'].append({'cutoff': start, 'candidates': records,
                                   'shortlist': [candidate_key(r) for r in chosen]})
        for record in chosen:
            key = candidate_key(record)
            union[key] = {k: record[k] for k in ('order', 'seasonal_order', 'trend')}
        logger.info('SARIMA screening cutoff=%s valid=%s shortlisted=%s', start,
                    sum(r['status'] == 'available' for r in records), len(chosen))
    audit['union'] = list(union)
    for candidate_number, (key, candidate) in enumerate(union.items(), 1):
        entry = {**candidate, 'candidate_id': key, 'windows': [], 'window_metrics': []}
        fitted = []
        for window_number, (start, end) in enumerate(windows, 1):
            report('Cross-window SARIMA refits', (candidate_number - 1) * 3 + window_number - 1,
                   len(union) * 3, f'Union candidate {candidate_number}/{len(union)}; window {window_number}/3')
            path, residuals, evidence = s.fit_sarima(values[:start], end - start, candidate, config)
            scoring = s.score(values[start:end], {'sarima': path})
            entry['windows'].append({'cutoff': start, 'fit': evidence, 'scoring': scoring})
            entry['window_metrics'].append(scoring['metrics']['sarima'])
            fitted.append((path, residuals))
        entry['aic'] = (float(np.mean([w['fit']['aic'] for w in entry['windows']]))
                        if all(w['fit']['status'] == 'available' for w in entry['windows']) else None)
        audit['sarima_candidates'].append(entry)
        if not s.rank_candidates([entry]):
            entry['exclusion_reason'] = 'Valid fits and RMSE/MAE metrics are required in all three windows.'
            continue
        for lag in config['lag_windows']:
            for nodes in config['hidden_nodes_grid']:
                hybrid = {**candidate, 'candidate_id': key, 'lag_window': lag, 'hidden_nodes': nodes,
                          'windows': [], 'window_metrics': []}
                for window_number, ((start, end), (path, residuals)) in enumerate(zip(windows, fitted), 1):
                    report('NNAR validation', candidate_number - 1, len(union),
                           f'Union candidate {candidate_number}/{len(union)}; window {window_number}/3; lag {lag}; hidden nodes {nodes}')
                    correction, evidence = s.fit_nnar(residuals, end - start, lag, nodes, config)
                    prediction = path + correction if correction is not None else None
                    if prediction is not None and not np.isfinite(prediction).all():
                        prediction = None
                        evidence['reason'] = 'Nonfinite combined Hybrid forecast.'
                    scoring = s.score(values[start:end], {'hybrid': prediction})
                    hybrid['windows'].append({'cutoff': start, 'nnar': evidence, 'scoring': scoring})
                    hybrid['window_metrics'].append(scoring['metrics']['hybrid'])
                if not s.rank_candidates([hybrid], hybrid=True):
                    hybrid['exclusion_reason'] = 'Valid hybrid forecasts and metrics are required in all three windows.'
                audit['hybrid_candidates'].append(hybrid)
    sarima_rank = s.rank_candidates(audit['sarima_candidates'])
    hybrid_rank = s.rank_candidates(audit['hybrid_candidates'], hybrid=True)
    # Keep complete diagnostics once, with compact ranking entries referencing candidate IDs.
    def compact(rows):
        return [{k: v for k, v in row.items() if k not in ('windows', 'window_metrics')} for row in rows]
    audit.update(sarima_ranking=compact(sarima_rank), hybrid_ranking=compact(hybrid_rank))
    locked = {'sarima': compact(sarima_rank[:1])[0] if sarima_rank else None,
              'hybrid': compact(hybrid_rank[:1])[0] if hybrid_rank else None}
    audit['locked_configuration'] = deepcopy(locked)
    audit['locked_at'] = now()
    return locked, audit


def refit(values, locked, config):
    """Refit only selected orders. A failure never selects the next-best model."""
    result = {'hybrid': None, 'sarima': None, 'raw_hybrid': None, 'raw_sarima': None,
              'hybrid_status': 'Hybrid unavailable', 'sarima_status': 'SARIMA-only unavailable',
              'diagnostics': {}, 'failures': {}}
    fits = {}
    for name in ('sarima', 'hybrid'):
        candidate = locked.get(name)
        if candidate is None:
            result['failures'][name] = ('No SARIMA candidate produced valid forecasts and metrics in all three windows.'
                                        if name == 'sarima' else 'No NNAR/Hybrid configuration was valid in all three windows; inspect residual-window and fitting diagnostics.')
            continue
        key = candidate_key(candidate)
        if key not in fits:
            fits[key] = s.fit_sarima(values, 52, candidate, config)
        path, residuals, evidence = fits[key]
        result['diagnostics'][name] = {'sarima': evidence}
        if path is None:
            result['failures'][name] = evidence['reason']
            continue
        if name == 'hybrid':
            correction, nnar = s.fit_nnar(residuals, 52, candidate['lag_window'], candidate['hidden_nodes'], config)
            result['diagnostics'][name]['nnar'] = nnar
            if correction is None:
                result['failures'][name] = nnar['reason']
                continue
            result['raw_hybrid_base'] = path.tolist()
            result['raw_residual_forecast'] = correction.tolist()
            path = path + correction
        if not np.isfinite(path).all():
            result['failures'][name] = 'Nonfinite combined forecast.'
            continue
        result['raw_' + name] = path.tolist()
        result[name] = np.maximum(0, path).tolist()
        result[name + '_status'] = 'Available'
    return result


def execute(values, index, config):
    windows, (holdout_start, end) = s.evaluation_splits(len(values))
    # Defensive copy makes holdout data physically unavailable to the selector.
    locked, audit = select(values[:holdout_start].copy(), config, windows)
    audit.update(training_range=period(index, 0, windows[0][0]),
                 validation_ranges=[{'training': period(index, 0, start), 'validation': period(index, start, stop)}
                                    for start, stop in windows],
                 holdout_range=period(index, holdout_start, end),
                 pre_holdout_refit_range=period(index, 0, holdout_start),
                 operational_refit_range=period(index, 0, end),
                 missing_observations=int(np.isnan(values).sum()), zero_observations=int(np.sum(values == 0)),
                 configuration_signature=digest(config))
    report('Final holdout refit', detail='Selected configurations are locked; evaluating the final 52 weeks.')
    retrospective = refit(values[:holdout_start], locked, config)
    actual = values[holdout_start:]
    scoring = s.score(actual, {name: retrospective[name] for name in ('sarima', 'hybrid')})
    horizons = {}
    for horizon in (4, 13, 26, 52):
        summary = s.score(actual[:horizon], {name: retrospective[name][:horizon]
                                           if retrospective[name] is not None else None for name in ('sarima', 'hybrid')})
        summary['period'] = [list(p) for p, value in zip(index[holdout_start:holdout_start + horizon], actual[:horizon]) if np.isfinite(value)]
        horizons[str(horizon)] = summary
    evaluation = {'status': 'Retrospective evaluation', 'designation': 'Final untouched 52-week holdout',
                  'holdout_weeks': 52, **scoring,
                  'period': horizons['52']['period'], 'range': audit['holdout_range'],
                  'hybrid_status': retrospective['hybrid_status'], 'sarima_status': retrospective['sarima_status'],
                  'diagnostics': retrospective['diagnostics'], 'failures': retrospective['failures'],
                  'predictions': {k: v for k, v in retrospective.items() if k in ('hybrid', 'sarima') or k.startswith('raw_')},
                  'dm_test': {'status': 'Not applicable', 'role': 'Supplementary only; never used for selection',
                              'reason': 'This single fixed-origin path contains horizons 1–52, not repeated forecast errors at a common horizon. A DM protocol for these dependent, mixed-horizon errors has not been specified.'}}
    # The same lock is retained even if retrospective scores are poor or a refit fails.
    report('Operational refit', detail='Refitting locked configurations on full history for the future 52-week path.')
    operational = refit(values, locked, config)
    result = {**operational, 'evaluation': evaluation, 'metrics': scoring['metrics'], 'horizon_metrics': horizons,
              'selection': audit, 'locked_configuration': locked,
              'sarima_configuration': locked['sarima'], 'hybrid_configuration': locked['hybrid'],
              'operational': {'designation': 'Operational future forecast', 'horizon': 52,
                              'training_range': audit['operational_refit_range'], 'configuration_locked': True},
              'run_status': 'Complete' if operational['hybrid'] is not None else 'Hybrid unavailable'}
    if operational['failures']:
        result['failure_reason'] = '; '.join(f'{name}: {reason}' for name, reason in operational['failures'].items())
    result['protocol_warnings'] = ['Seasonal period 52 approximates annual weekly seasonality; documented week 53 remains a separate position.',
                                   'Recursive residual forecasts may accumulate error at longer horizons.']
    if any(r and r['mape_selection_unavailable'] for r in locked.values()):
        result['protocol_warnings'].append('MAPE was unavailable for model selection: all three validation windows had zero-only actuals. Ranking used RMSE and MAE.')
    logger.info('Completed weekly model selection configuration=%s', json.dumps(locked, allow_nan=False))
    return result
