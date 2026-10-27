"""Full selection on uploaded data; isolated from the research model registry."""
from copy import deepcopy
from pathlib import Path
import uuid

import numpy as np
from threadpoolctl import threadpool_limits

from dashboard.weekly.data import digest, now
from dashboard.weekly.estimators import VERSION
from dashboard.weekly import model, selection
from dashboard.weekly.sample import prepare_uploaded

TITLE = 'Provisional Model Validation — Uploaded Dataset'
NOTICE = 'Not Thesis-Validated'
ROOT = Path(__file__).resolve().parents[2] / '.weekly-models' / 'provisional'


def shape_diagnostics(actual, predictions, index):
    """Peak comparison uses the common observed mask; directions never bridge gaps.

    Descriptive heuristics, not significance tests: a surge is max >= 2*median
    and max-median >= 10 cases. Missing it badly means >4 positions timing
    error or >50% magnitude error. Smooth means <50% observed difference SD.
    Tied peaks use the earliest observed position; timing is chronological.
    """
    actual = np.asarray(actual, float)
    mask = np.isfinite(actual)
    if not mask.any():
        raise ValueError('No observed cases available for shape diagnostics.')
    positions = np.flatnonzero(mask)
    peak = int(positions[np.argmax(actual[mask])])
    pairs = mask[1:] & mask[:-1]
    changes = np.diff(actual)[pairs]
    median = float(np.median(actual[mask]))
    result = {'actual_peak': {'week': index[peak], 'position': peak + 1, 'count': float(actual[peak])},
              'clear_surge_heuristic': bool(actual[peak] >= 2 * median and actual[peak] - median >= 10),
              'models': {}, 'thresholds': {'surge_peak_to_median': 2, 'surge_excess_cases': 10,
                'miss_timing_positions': 4, 'miss_magnitude_fraction': .5,
                'smooth_difference_sd_ratio': .5},
              'limitations': 'Descriptive heuristics, not proof of accuracy or statistical seasonality. Earliest tied peak; observed positions only; directions exclude pairs crossing missing observations.'}
    for name, path in predictions.items():
        path = np.asarray(path, float)
        predicted_peak = int(positions[np.argmax(path[mask])])
        predicted_changes = np.diff(path)[pairs]
        change_sd = float(np.std(changes)) if len(changes) else 0
        ratio = float(np.std(predicted_changes) / change_sd) if change_sd else None
        timing = predicted_peak - peak
        magnitude = float(path[predicted_peak] - actual[peak])
        result['models'][name] = {
            'peak_week': index[predicted_peak], 'peak_position': predicted_peak + 1,
            'peak_count': float(path[predicted_peak]), 'peak_timing_error_positions': timing,
            'peak_magnitude_error_cases': magnitude,
            'directional_agreement_rate': float(np.mean(np.sign(changes) == np.sign(predicted_changes))) if len(changes) else None,
            'direction_pairs_scored': int(pairs.sum()), 'difference_sd_ratio': ratio,
            'substantially_smoother': ratio is not None and ratio < .5,
            'missed_surge': bool(result['clear_surge_heuristic'] and
                                 (abs(timing) > 4 or abs(magnitude) > .5 * actual[peak]))}
    return result


def interpretation(result):
    metrics = result['metrics']
    differences = [metrics['hybrid'][k] - metrics['sarima'][k] for k in ('rmse', 'mae')]
    comparison = ('Similar RMSE and MAE' if all(v == 0 for v in differences) else
                  'Hybrid performed better on RMSE and MAE' if all(v <= 0 for v in differences) else
                  'SARIMA-only performed better on RMSE and MAE' if all(v >= 0 for v in differences) else
                  'Mixed result: RMSE and MAE favor different models')
    shape = result['shape_diagnostics']['models']['hybrid']
    statements = [comparison + ' in the Final Test. MAPE is supporting evidence, with zero-actual exclusions reported.']
    if shape['missed_surge']:
        statements.append('Provisional validation indicates weak reproduction of the held-out seasonal pattern. Review selected configuration and candidate evidence.')
    if shape['substantially_smoother']:
        statements.append('The Hybrid forecast was substantially smoother than observed week-to-week Final Test changes.')
    agreement = shape['directional_agreement_rate']
    statements.append(f"Hybrid peak timing error: {shape['peak_timing_error_positions']:+d} chronological weeks; peak magnitude error: {shape['peak_magnitude_error_cases']:+.3f} cases.")
    if agreement is not None:
        statements.append(f'Direction agreement: {agreement:.1%} across {shape["direction_pairs_scored"]} consecutive observed pairs; supplementary only.')
    components = result['components']
    changes = {k: float(components[k][-1] - components[k][0]) for k in ('raw_sarima', 'nnar_correction', 'hybrid')}
    clipping = changes['hybrid'] - changes['raw_sarima'] - changes['nnar_correction']
    result['future_shape'] = {'first_to_last_change_cases': changes, 'clipping_change_cases': clipping,
                              'hybrid_nondecreasing': bool(np.all(np.diff(result['hybrid']) >= 0)),
                              'hybrid_nonincreasing': bool(np.all(np.diff(result['hybrid']) <= 0))}
    statements.append(f"Future first-to-last changes: raw SARIMA {changes['raw_sarima']:+.3f}, NNAR correction {changes['nnar_correction']:+.3f}, clipped Hybrid {changes['hybrid']:+.3f} cases. Inspect component paths for intervening rises and falls.")
    statements.append('A held-out test is historical evidence; it cannot establish that a future smooth decline will occur. No variability was added to the predictions.')
    return statements


def run_provisional(dataset, disease, output=None, progress=None):
    # Bound BLAS thread usage; numerical settings, grid and iteration limits remain unchanged.
    with threadpool_limits(limits=1):
        return _run(dataset, disease, output, progress)


def _run(dataset, disease, output, progress):
    emit = progress or (lambda stage, message: None)
    started = now()
    run_id = uuid.uuid4().hex
    root = Path(output) if output is not None else ROOT / run_id
    emit('prepare', 'Preparing uploaded dataset; checking structural validity independently of research eligibility.')
    if dataset['metadata'].get('dataset_type') == 'synthetic' or dataset.get('context') == 'Synthetic / Demo Data':
        raise ValueError('Provisional validation requires an uploaded dataset, not the synthetic demo.')
    prepared, assumptions = prepare_uploaded(dataset, 'Provisional')
    for assumption in assumptions:
        emit('data_assumptions', assumption)
    values, index = model.training_series(prepared, disease)
    fingerprint = digest({'records': dataset['records'], 'metadata': dataset['metadata'], 'disease': disease})
    emit('split', 'Creating chronological Training / Validation (52) / Final Test (52) split.')
    train, validation, test, periods = selection.chronological_split(values, index)
    if not np.isfinite(validation).any() or not np.isfinite(test).any():
        raise ValueError('Provisional validation requires observed cases in both Validation and Final Test.')
    c, audit = selection.select_configuration(train, validation, disease, periods,
        checkpoint=lambda a: selection.write_json(root / 'search.json', a), progress=emit)
    emit('lock', 'Locking provisional configuration before any Final Test fitting or scoring.')
    c.pop('locked_configuration_id')
    c.update(status='PROVISIONAL', source='uploaded_dataset', research_validated=False,
             validation_scope='provisional', label=TITLE + ' — ' + NOTICE,
             dataset_fingerprint=fingerprint, provisional_run_id=run_id,
             data_assumptions=assumptions, modeling_calendar=prepared['metadata'].get('year_lengths', {}))
    c['locked_configuration_id'] = digest(c)
    selection.verify_lock(c)
    selection.write_json(root / 'locked.json', c)
    audit.update(configuration=deepcopy(c), status='PROVISIONAL', research_validated=False)
    selection.write_json(root / 'search.json', audit)
    result = {'provisional_validation': True, 'status': 'PROVISIONAL', 'source': 'uploaded_dataset',
              'research_validated': False, 'context': TITLE + ' — ' + NOTICE, 'eligible': False,
              'dataset_id': dataset['id'], 'dataset_fingerprint': fingerprint, 'disease': disease,
              'metadata': deepcopy(dataset['metadata']), 'model_version': VERSION, 'issued_at': now(),
              'configuration': deepcopy(c), 'configuration_label': c['label'], 'metrics': {},
              'warnings': [NOTICE, *dataset['quality']['warnings'], *assumptions,
                           'Population, case classification and provenance retain their supplied verification status; this run does not establish research eligibility.'],
              'eligibility_reasons': dataset.get('eligibility_reasons', []),
              'data_status': {'structure': 'Valid', 'research_eligibility': 'Not confirmed by provisional validation',
                              'population': dataset['metadata'].get('population') or 'Unverified',
                              'case_classification': dataset['metadata'].get('case_classification') or 'Unverified'},
              'training_index': [list(p) for p in index],
              'history': [float(v) if np.isfinite(v) else None for v in values],
              'training_observed_count': int(np.isfinite(values).sum()),
              'validation_metrics': {'sarima': c['selection_diagnostics']['sarima']['validation'],
                                    'hybrid_seed_median': c['selection_diagnostics']['nnar']['median_validation']},
              'validation_seed_metrics': c['selection_diagnostics']['nnar']['seeds'],
              'search_summary': {'sarima_attempted': len(audit['sarima_candidates']),
                'sarima_successful': sum(r['fit_status'] == 'available' for r in audit['sarima_candidates']),
                'sarima_shortlisted': sum(r.get('shortlisted', False) for r in audit['sarima_candidates']),
                'nnar_configurations': len(audit['nnar_candidates']),
                'nnar_successful_all_seeds': sum(r['status'] == 'available' for r in audit['nnar_candidates'])}}
    try:
        model.retrospective_evaluation(result, values, index, c, disease, progress=emit)
    except ValueError as exc:
        reason = str(exc)
        if reason.startswith('Terminal residual lag window'):
            window = index[:-52][-max(c['nnar_lags']):]
            missing = [list(p) for p, value in zip(window, values[:-52][-max(c['nnar_lags']):]) if not np.isfinite(value)]
            reason = ('Provisional Final Test blocked: the NNAR starting window contains missing observed residuals at '
                      + str(missing) + '. Source counts were not filled or removed. Selected configuration and candidate evidence were retained.')
        selection.write_json(root / 'failure.json', {'status': 'failed', 'research_validated': False,
            'stage': 'final_test_refit', 'failure_reason': reason, 'partial_evidence': result,
            'provisional_run_id': run_id, 'started_at': started, 'failed_at': now()})
        raise ValueError(reason) from exc
    selection.write_json(root / 'evaluation.json', result)
    emit('charts', 'Preparing Final Test comparison, peak timing, directional and component chart data.')
    result['shape_diagnostics'] = shape_diagnostics(result['evaluation']['actual'], result['evaluation']['predictions'], result['evaluation']['index'])
    emit('future_refit', 'Refitting the provisional locked configuration on all usable uploaded history.')
    future = model.fit_models(values, 52, c, progress=emit)
    if future['hybrid'] is None:
        raise ValueError(future.get('failure_reason', 'Provisional future refit failed. Historical test evidence was retained.'))
    result.update(future)
    emit('future', 'Generated one provisional 52-week future path; 4/13/26/52 displays use slices.')
    result['forecast_label'] = 'Provisional Future Forecast — Uploaded Dataset'
    result['forecast_index'] = []
    point = index[-1]
    for offset in range(1, 53):
        try:
            point = model.advance(point, prepared['metadata']['year_lengths']) if point else None
        except ValueError:
            point = None
        result['forecast_index'].append({'horizon_week': offset, 'year': point[0] if point else None,
                                         'morbidity_week': point[1] if point else None})
    if any(p['year'] is None for p in result['forecast_index']):
        result['warnings'].append('Future source calendar unresolved: affected weeks use horizon offsets without invented calendar labels.')
    result['interpretation'] = interpretation(result)
    if result['shape_diagnostics']['models']['hybrid']['missed_surge']:
        result['warnings'].append(result['interpretation'][1])
    result['run_metadata'] = {'provisional_run_id': run_id, 'selection_run_id': c['selection_run_id'],
                               'started_at': started, 'completed_at': now(), 'artifact_directory': str(root),
                               'status': 'complete', 'mode': 'provisional'}
    selection.verify_lock(c)
    selection.write_json(root / 'report.json', methodology_report(result, audit))
    selection.write_json(root / 'result.json', result)
    write_readable_report(root / 'report.md', result)
    emit('complete', 'Provisional validation and future forecast complete — Not Thesis-Validated.')
    return result


def methodology_report(result, audit=None):
    report = {'title': 'Provisional Model Validation — Not Thesis-Validated', **deepcopy(result)}
    if audit is not None:
        report['candidate_evidence'] = audit
    return report


def write_readable_report(path, result):
    c = result['configuration']
    selected = c['candidates'][0]
    lines = ['# Provisional Model Validation — Not Thesis-Validated', '',
             f"Disease: {result['disease']}. Source: {result['metadata'].get('source_file', 'uploaded dataset')}.", '',
             f"Dataset fingerprint: `{result['dataset_fingerprint']}`", '',
             f"Lock: `{c['locked_configuration_id']}`", '',
             *[f'- {name}: {start} through {end}' for name, (start, end) in c['periods'].items()], '',
             f"Selected SARIMA: {selected['order']} {selected['seasonal_order']}, no exogenous inputs.",
             f"Selected NNAR: lag {max(c['nnar_lags'])}, hidden nodes {c['hidden_nodes']}, alpha {c['alpha']}; ReLU/L-BFGS; seeds 42/137/2026; production seed 42.", '',
             '| Period / model | RMSE | MAE | MAPE (%) |', '|---|---:|---:|---:|']
    for period, models in [('Validation', result['validation_metrics']), ('Final Test', result['metrics'])]:
        for name, metrics in models.items():
            lines.append('| ' + period + ' / ' + name + ' | ' + ' | '.join(
                'Unavailable' if metrics[k] is None else f'{metrics[k]:.6f}' for k in ('rmse', 'mae', 'mape')) + ' |')
    lines += ['', 'Validation Hybrid errors are seed medians; Final Test uses seed 42. Full-precision errors, seed coverage, ADF and Ljung–Box diagnostics are in report.json.', '',
              *result['interpretation'], '', '## Peak evidence', '',
              'Actual peak: ' + str(result['shape_diagnostics']['actual_peak']), '',
              '| Model | Peak week | Peak count | Timing error (positions) | Magnitude error (cases) | Direction agreement |',
              '|---|---|---:|---:|---:|---:|']
    for name, row in result['shape_diagnostics']['models'].items():
        agreement = row['directional_agreement_rate']
        lines.append(f"| {name} | {row['peak_week']} | {row['peak_count']:.6f} | {row['peak_timing_error_positions']} | {row['peak_magnitude_error_cases']:.6f} | " + ('Unavailable' if agreement is None else f'{agreement:.2%}') + ' |')
    lines += ['', result['shape_diagnostics']['limitations'], '', '## Warnings and assumptions', '',
              *['- ' + w for w in result['warnings']], '',
              '## Provisional future 52-week path', '',
              'Horizon positions are relative to the last supplied usable week. Calendar labels are omitted where the future source calendar is unverified. Values below are rounded for reading only; JSON retains full precision.', '',
              '| Horizon week | Raw SARIMA | NNAR correction | Final Hybrid |', '|---:|---:|---:|---:|']
    for i in range(52):
        lines.append(f'| {i + 1} | ' + ' | '.join(f"{result['components'][key][i]:.6f}" for key in ('raw_sarima', 'nnar_correction', 'hybrid')) + ' |')
    Path(path).write_text('\n'.join(lines) + '\n', encoding='utf-8')
