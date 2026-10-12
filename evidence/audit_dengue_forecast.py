"""Reproduce Dengue forecasts and score a held-out year; no app state is changed."""
import base64
import argparse
import json
import os
from pathlib import Path

for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[variable] = '1'

import numpy as np
import pandas as pd

from dashboard.logging_config import configure_logging
from dashboard.weekly.model import fit_models, training_series, validate_config
from dashboard.weekly.settings import model_configuration
from dashboard.weekly.transform import prepare, read_source, update_facts

OUTPUT = Path('evidence/dengue-forecast-audit.json')


def score(actual, predicted):
    actual, predicted = np.asarray(actual), np.asarray(predicted)
    mask = np.isfinite(actual) & np.isfinite(predicted)
    a, p = actual[mask], predicted[mask]
    return {'scored_weeks': int(mask.sum()), 'actual_sum': float(a.sum()),
            'predicted_sum': float(p.sum()), 'mae': float(np.mean(np.abs(p-a))),
            'rmse': float(np.sqrt(np.mean((p-a)**2))),
            'bias_per_week': float(np.mean(p-a)),
            'wape_percent': float(np.abs(p-a).sum()/a.sum()*100)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config')
    parser.add_argument('--output', default=str(OUTPUT))
    args = parser.parse_args()
    configure_logging()
    path = Path('Antipolo_Disease_Surveillance_2016-2025.xlsx')
    source = read_source('data:;base64,' + base64.b64encode(path.read_bytes()).decode(), path.name)
    # Analysis scenario only: treats supplied nonblank reports as complete.
    # This assumption does not assert source certification or modify user data.
    dataset = update_facts(prepare(source), {
        'reporting_status': 'complete',
        'reporting_reference': 'AUDIT SCENARIO: assume all supplied counts are complete; not source certification',
    })
    values, index = training_series(dataset, 'Dengue')
    frame = pd.DataFrame(dataset['records'])
    frame = frame[frame.disease == 'Dengue']
    annual = frame.groupby('year').case_count.agg(['sum', 'count', 'max']).reset_index().to_dict('records')
    config = validate_config(json.loads(Path(args.config).read_text(encoding='utf-8'))
                             if args.config else model_configuration(), 'Dengue')
    audit = {'source': path.name, 'file_sha256': source['file_sha256'],
             'assumption': 'All supplied nonblank counts treated as complete for reproduction only.',
             'configuration': config, 'annual': annual, 'training_index': index,
             'training_values': [float(v) if np.isfinite(v) else None for v in values],
             'missing_positions': [p for p,v in zip(index,values) if not np.isfinite(v)],
             'duplicate_keys': dataset['quality']['duplicates']}
    def save():
        Path(args.output).write_text(json.dumps(audit, indent=2, allow_nan=False), encoding='utf-8')
    audit['forecast'] = fit_models(values, 52, config)
    save()
    for name in ('sarima', 'hybrid'):
        p = audit['forecast'][name]
        print('FORECAST', name, None if p is None else {'first':p[0], 'last':p[-1], 'sum':sum(p), 'min':min(p),'max':max(p)}, flush=True)
    audit['holdout'] = fit_models(values[:-52], 52, config)
    actual = values[-52:]
    lookup = dict(zip(index, values))
    baselines = {
        'seasonal_naive_calendar': [lookup.get((y-1,w), np.nan) for y,w in index[-52:]],
        'seasonal_naive_52_positions': values[-104:-52],
        'last_observation': np.repeat(values[-53], 52),
    }
    audit['holdout_index'] = index[-52:]
    audit['metrics'] = {name: score(actual,pred) for name,pred in baselines.items()}
    for name in ('sarima', 'hybrid'):
        if audit['holdout'][name] is not None:
            audit['metrics'][name] = score(actual,audit['holdout'][name])
    audit['horizon_metrics'] = {
        str(h): {name: score(actual[:h], pred[:h])
                 for name,pred in {**baselines, **{k:audit['holdout'][k] for k in ('sarima','hybrid')}}.items()
                 if pred is not None} for h in (4,13,26,52)
    }
    save()
    print('METRICS', json.dumps(audit['metrics']), flush=True)


if __name__ == '__main__':
    main()
