import copy

import numpy as np
import pytest

from dashboard.weekly import data, model, outputs
from dashboard.weekly.sample import prepare_sample, sample_configuration


def test_genuine_demo_hybrid_forecast_without_research_lock():
    active = data.demo()
    before = copy.deepcopy(active)
    result = model.run(active, 'Demo disease', sample_configuration(), sample=True)
    assert result.get('failure_reason') is None, result.get('failure_reason')
    assert len(result['hybrid']) == len(result['sarima']) == len(result['forecast_index']) == 52
    assert np.isfinite(result['hybrid']).all() and min(result['hybrid']) >= 0
    assert result['sample_forecast'] and not result['eligible']
    assert result['context'] == 'Quick Preview — Fixed Settings — Unvalidated demonstration forecast'
    assert result['metrics'] == {} and 'Not performed' in result['evaluation']['status']
    assert result['range'] is None and active == before
    exported = outputs.export_frame(active, result)
    assert exported['sample_forecast'].all()
    assert set(exported['context']) == {'Quick Preview — Fixed Settings — Unvalidated demonstration forecast'}


def test_sample_assumptions_keep_source_zeros_gaps_and_week53():
    active = data.demo()
    active['metadata']['year_lengths'] = {}
    for r in active['records']:
        r['reporting_status'] = 'unknown'
    active['records'][0]['case_count'] = 0
    active['records'][1]['case_count'] = None
    active['records'].append({'disease': 'Demo disease', 'year': 2020, 'morbidity_week': 53,
                              'case_count': 3, 'reporting_status': 'unknown'})
    before = copy.deepcopy(active)
    prepared, notes = prepare_sample(active)
    values, index = model.training_series(prepared, 'Demo disease')
    assert values[0] == 0 and np.isnan(values[1]) and (2020, 53) in index
    assert any('unverified reporting' in n for n in notes)
    assert any('calendar assumption' in n for n in notes)
    assert active == before


def test_sample_does_not_enable_research_or_accept_invalid_records():
    active = data.demo()
    result = model.run(active, 'Demo disease', sample_configuration())
    assert result['hybrid'] is None and 'locked' in result['failure_reason']
    active['records'].append(copy.deepcopy(active['records'][0]))
    with pytest.raises(ValueError, match='validation errors'):
        prepare_sample(active)


def test_sample_retains_explicitly_incomplete_reporting():
    active = data.demo()
    active['records'][10]['reporting_status'] = 'incomplete'
    prepared, _ = prepare_sample(active)
    values, _ = model.training_series(prepared, 'Demo disease')
    assert np.isnan(values[10])


def test_sample_requires_known_preset_and_sufficient_history():
    active = data.demo()
    c = sample_configuration()
    c['alpha'] = 500
    assert 'demonstration preset' in model.run(active, 'Demo disease', c, sample=True)['failure_reason']
    active['records'] = active['records'][:100]
    result = model.run(active, 'Demo disease', sample_configuration(), sample=True)
    assert result['hybrid'] is None and 'Insufficient' in result['failure_reason']
