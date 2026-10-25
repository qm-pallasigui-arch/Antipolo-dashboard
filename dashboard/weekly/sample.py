"""Explicit sample-only forecasts with a fixed, untuned demonstration preset."""
from copy import deepcopy

import pandas as pd

from dashboard.weekly.data import validate
from dashboard.weekly.selection import base_config

SAMPLE_VERSION = 'sample-weekly-1'
SAMPLE_NOTICE = ('Quick Preview only — fixed demonstration parameters, not selected or validated for this disease. '
                 'Do not use as thesis performance evidence or operational health guidance.')


def sample_configuration():
    c = base_config()
    c.update(version=SAMPLE_VERSION, model_version=SAMPLE_VERSION,
             label='Quick Preview — Fixed Settings — Unvalidated demonstration forecast',
             candidates=[{'order': [1, 0, 0], 'seasonal_order': [1, 0, 0, 52], 'trend': 'n'}],
             nnar_lags=[1, 2], hidden_nodes=2, alpha=1.0,
             selection_status='sample preset — not selected', holdout_weeks=None)
    return c


def prepare_sample(dataset):
    prepared, notes = prepare_uploaded(dataset, 'Sample')
    return prepared, [SAMPLE_NOTICE, *notes]


def prepare_uploaded(dataset, scope):
    """Make explicit working assumptions without rewriting the uploaded source."""
    checked = validate(pd.DataFrame(dataset['records']), dataset['metadata'])
    if checked['quality']['errors']:
        raise ValueError('Unresolved data validation errors.')
    prepared = deepcopy(dataset)
    meta = prepared['metadata']
    notes = []
    assumed = 0
    for row in prepared['records']:
        status = str(row.get('reporting_status') or meta.get('reporting_status') or 'unknown').lower()
        if status not in ('complete', 'incomplete'):
            row['reporting_status'] = 'complete'
            assumed += 1
    if assumed:
        notes.append(f'{scope} assumption: {assumed} rows with unverified reporting status are included as supplied; historical completeness is not established.')
    lengths = dict(meta.get('year_lengths') or {})
    years = sorted({r['year'] for r in prepared['records']})
    assumed_years = []
    for year in range(min(years), max(years) + 1):
        if str(year) not in lengths:
            lengths[str(year)] = 53 if any(r['year'] == year and r['morbidity_week'] == 53 for r in prepared['records']) else 52
            assumed_years.append(year)
    if assumed_years:
        notes.append(scope + ' calendar assumption for ' + ', '.join(map(str, assumed_years)) +
                     ': retain supplied Week 53; otherwise use 52 positions. This is not source calendar verification.')
    meta['year_lengths'] = lengths
    return prepared, notes
