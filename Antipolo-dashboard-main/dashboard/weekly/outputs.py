"""Provenance-rich exports and append-only prospective snapshots."""
import json
import os
import re
from pathlib import Path

import numpy as np
import pandas as pd

from dashboard.modeling.metrics import compute_metrics
from dashboard.weekly.result_schema import current_result
from dashboard.weekly.data import digest, now
from dashboard.weekly import calendar as mmwr


def export_frame(dataset, result=None):
    result = current_result(result or {})
    meta = dataset['metadata']
    common = {'dataset_id': dataset['id'], 'population': meta.get('population'),
              'case_classification': meta.get('case_classification'), 'source': meta.get('source_system'),
              'source_file': meta.get('source_file'), 'dataset_type': meta.get('dataset_type'),
              'frequency': meta.get('frequency'), 'context': result.get('context', dataset['context']),
              'thesis_eligible_dataset': dataset['eligible'], 'issue_time': result.get('issued_at'),
              'model_version': result.get('model_version'), 'hybrid_status': result.get('hybrid_status', 'Not run'),
              'sarima_status': result.get('sarima_status', 'Not run'), 'forecast_horizon': 52,
              'model_configuration': json.dumps(result.get('configuration', {})),
              'configuration_label': result.get('configuration_label'),
              'horizon_metrics': json.dumps(result.get('horizon_metrics', {})),
              'sarima_configuration': json.dumps(result.get('sarima_configuration', {})),
              'hybrid_base_configuration': json.dumps(result.get('hybrid_configuration', {})),
              'evaluation_metrics': json.dumps(result.get('metrics', {})),
              'evaluation_period': json.dumps(result.get('evaluation', {})),
              'warnings': json.dumps(result.get('warnings', dataset['quality']['warnings'])),
              'failure_reason': result.get('failure_reason'), 'provenance': json.dumps(meta),
              'transformation_provenance': json.dumps((dataset.get('transformation') or {}).get('sheets', [])),
              'eligibility_reasons': json.dumps(dataset['eligibility_reasons'])}
    records = []
    for r in dataset['records']:
        row = {**common, **r, 'observed_or_forecast': 'observed', 'model_used': None,
               'weekly_index': f"{r['year']}-W{r['morbidity_week']:02d}",
               'excluded_from_training': str(r.get('reporting_status') or meta.get('reporting_status', '')).lower() != 'complete'}
        records.append(row)
    for model, label in [('hybrid', 'Hybrid SARIMA–NNAR'), ('sarima', 'SARIMA-only')]:
        for i, value in enumerate(result.get(model) or []):
            point = result['forecast_index'][i]
            band = result.get('range') if model == 'hybrid' else None
            records.append({**common, **point, 'disease': result['disease'], 'case_count': value,
                            'weekly_index': f"+{i + 1}", 'observed_or_forecast': 'forecast', 'model_used': label,
                            'range_lower': band['lower'][i] if band else None,
                            'range_upper': band['upper'][i] if band else None,
                            'range_method': band['method'] if band else None})
    return pd.DataFrame(records)


def snapshot_root():
    return Path(os.environ.get('WEEKLY_SNAPSHOT_DIR', 'evidence/weekly_snapshots'))


def save_snapshot(dataset, result, root=None):
    result = current_result(result)
    if result.get('dataset_id') != dataset['id'] or not (result.get('hybrid') or result.get('sarima')):
        raise ValueError('A matching, generated forecast is required before issuing a snapshot.')
    if any(p['year'] is None for p in result['forecast_index']):
        raise ValueError('Resolve future reporting calendar labels before issuing a reconcilable snapshot.')
    payload = {'schema': 'weekly-snapshot-1', 'status': 'Future prospective validation — not completed',
               'snapshot_created_at': now(), 'dataset': dataset, 'forecast': result}
    identifier = digest(payload)
    directory = Path(root) if root else snapshot_root()
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / f'{identifier}.json').open('x', encoding='utf-8') as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2, allow_nan=False)
    return identifier


def reconcile(identifier, observed, root=None):
    if not re.fullmatch(r'[0-9a-f]{64}', identifier or ''):
        raise ValueError('A valid snapshot ID is required.')
    directory = Path(root) if root else snapshot_root()
    original = json.loads((directory / f'{identifier}.json').read_text(encoding='utf-8'))
    if digest(original) != identifier:
        raise ValueError('Snapshot integrity check failed.')
    if observed['quality']['errors']:
        raise ValueError('Resolve observation validation errors before reconciliation.')
    source_meta = original['dataset']['metadata']
    for key in ['population', 'case_classification', 'source_system', 'dataset_type', 'frequency', 'location']:
        if observed['metadata'].get(key) != source_meta.get(key):
            raise ValueError(f'Snapshot/observation context mismatch: {key}.')
    forecast = original['forecast']
    lookup = {(r['year'], r['morbidity_week']): r for r in observed['records'] if r['disease'] == forecast['disease']}
    rows = []
    for i, point in enumerate(forecast['forecast_index']):
        observation = lookup.get((point['year'], point['morbidity_week']))
        if not observation:
            continue
        for key in ['population', 'case_classification', 'source_system', 'dataset_type', 'frequency', 'location']:
            supplied = observation.get(key)
            if supplied is not None and str(supplied).strip():
                expected = source_meta.get(key)
                if key == 'population':
                    supplied = str(supplied).replace('-', '–')
                    expected = str(expected).replace('-', '–')
                if supplied != expected:
                    raise ValueError(f'Snapshot/observation row context mismatch: {key}.')
        complete = str(observation.get('reporting_status') or observed['metadata'].get('reporting_status', '')).lower() == 'complete'
        for model in ['hybrid', 'sarima']:
            if forecast.get(model) is None:
                continue
            predicted = forecast[model][i]
            actual = observation['case_count']
            rows.append({**point, 'model': model, 'original_prediction': predicted, 'observed': actual,
                         'reporting_complete': complete,
                         'metrics': compute_metrics([actual], [predicted]) if complete and actual is not None else None})
    result = {'snapshot_id': identifier, 'reconciled_at': now(), 'observed_dataset_id': observed['id'],
              'context': forecast['context'], 'status': 'Prospective reconciliation; original issue timing and protocol require researcher verification.',
              'horizon_specific_results': rows}
    revision = digest(result)
    with (directory / f'{identifier}.revision-{revision}.json').open('x', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
    return result


def reporting_period(row, aggregation):
    """Reporting period label for one record.

    Uses the source week-start date when the record has one, otherwise derives
    the week's start from the MMWR reporting calendar. historical_summary groups
    by this same function, so a period in the date-range dropdown and a period
    in the chart are guaranteed to be the same label rather than two rules that
    could drift apart.
    """
    if aggregation == 'Weekly':
        return f"{row['year']}-W{row['morbidity_week']:02d}"
    source = pd.to_datetime(row.get('week_start_date'), errors='coerce')
    date = source if not pd.isna(source) else pd.Timestamp(mmwr.week_start(int(row['year']), int(row['morbidity_week'])))
    return str(date.to_period('M' if aggregation == 'Monthly' else 'Q'))


def historical_summary(dataset, disease, aggregation):
    rows = [r for r in dataset['records'] if r['disease'] == disease]
    if aggregation == 'Weekly':
        return [f"{r['year']}-W{r['morbidity_week']:02d}" for r in rows], [r['case_count'] for r in rows], 'Weekly source observations'
    if not rows:
        raise ValueError('No observations are available for this disease.')
    # A source week-start date is used when the source supplies one for every row.
    # Otherwise the period comes from the reporting week under the MMWR rule the
    # calendar already applies. The two are never mixed within one summary, so a
    # total is never part source-dated and part derived.
    if all(r.get('week_start_date') for r in rows):
        basis = 'the source week-start date'
    else:
        basis = ('the reporting calendar derived from the CDC MMWR rule, not a '
                 'source-established date')
    frame = pd.DataFrame(rows)
    frame['period'] = [reporting_period(r, aggregation) for r in rows]
    grouped = frame.groupby('period', sort=True).case_count.agg(lambda s: np.nan if s.isna().any() else s.sum())
    explanation = (f'{aggregation} summary by {basis}. Weeks are counted whole, in the period they begin in; '
                   f'a week straddling a period boundary is counted entirely in the period it starts in. '
                   f'Counts are never split across periods and blanks are never filled. '
                   f'Missing weeks may make totals incomplete.')
    return grouped.index.tolist(), [None if pd.isna(x) else x for x in grouped], explanation
