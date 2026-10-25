"""Guided forecasting, immutable historical windows and isolated research evidence."""
from copy import deepcopy
import json
from pathlib import Path
import uuid

import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

from dashboard.weekly import model, selection, settings
from dashboard.weekly.data import digest, now, validate
from dashboard.weekly.estimators import VERSION
from dashboard.weekly.provisional import run_provisional, shape_diagnostics, interpretation

ROOT = Path(__file__).resolve().parents[2] / '.weekly-models' / 'research'
METHODOLOGY_VERSION = 'weekly-3-guided-1'


def synthetic(dataset):
    return dataset.get('metadata', {}).get('dataset_type') == 'synthetic' or dataset.get('context') == 'Synthetic / Demo Data'


def installed_lock(disease):
    try:
        registry = settings.model_configuration()
        if 'configurations' in registry:
            if not isinstance(registry['configurations'], dict):
                raise ValueError('Invalid registry')
            c = registry['configurations'].get(disease)
            if disease in registry['configurations'] and not isinstance(c, dict):
                raise ValueError('Invalid disease configuration')
        else:
            c = registry
        if c is not None:
            check_lock(c, disease)
        return c
    except (ValueError, KeyError, TypeError, OSError) as exc:
        raise ValueError('The installed research configuration failed integrity checks. Forecasting was stopped rather than substituting another configuration.') from exc


def check_lock(c, disease):
    selection.verify_lock(c)
    if (c.get('validation_scope') == 'provisional' or c.get('status') == 'PROVISIONAL'
            or c.get('version') != VERSION or c.get('disease', disease) != disease):
        raise ValueError('Research configuration scope, disease or model version is incompatible.')
    model.validate_config(c, disease)


def source_key(dataset, disease):
    meta = dataset['metadata']
    return digest({'disease': disease, 'source': {k: meta.get(k) for k in
        ('population', 'case_classification', 'location', 'source_system', 'provenance', 'frequency', 'dataset_type')}})


def load_json(path):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError) as exc:
        raise ValueError('Research evidence could not be read. Forecasting stopped; existing evidence was preserved.') from exc


def resolve_lock(dataset, disease):
    c = installed_lock(disease)
    source = ROOT / source_key(dataset, disease)
    if c is not None:
        return c, ROOT / 'installed' / c['locked_configuration_id'], 'installed'
    pointer = source / 'selected.json'
    if pointer.exists():
        reference = load_json(pointer)
        if not isinstance(reference, dict):
            raise ValueError('Research runtime configuration reference failed integrity checks.')
        lock_id = reference.get('locked_configuration_id')
        if not isinstance(lock_id, str) or len(lock_id) != 64 or any(x not in '0123456789abcdef' for x in lock_id):
            raise ValueError('Research runtime configuration reference failed integrity checks.')
        c = load_json(source / lock_id / 'locked.json')
        try:
            check_lock(c, disease)
        except (ValueError, KeyError, TypeError) as exc:
            raise ValueError('Research runtime configuration failed integrity checks. Forecasting stopped without substituting another configuration.') from exc
        if c['locked_configuration_id'] != lock_id:
            raise ValueError('Research runtime configuration reference does not match its lock.')
        return c, source / lock_id, 'runtime'
    return None, source, 'missing'


def preparation(dataset, last_year):
    meta = dataset['metadata']
    # Future calendar extensions do not change the original evaluation window.
    return {**{k: meta.get(k) for k in ('frequency', 'reporting_status', 'calendar_rule', 'population',
               'case_classification', 'location', 'source_system', 'provenance', 'dataset_type')},
            'year_lengths': {str(k): v for k, v in meta.get('year_lengths', {}).items() if int(k) <= last_year},
            'missing_policy': 'state_space', 'week53_policy': 'preserve_sequence'}


def historical_window(dataset, disease, c):
    values, index = model.training_series(dataset, disease)
    try:
        start = index.index(tuple(c['periods']['training'][0]))
        stop = index.index(tuple(c['periods']['final_test'][1])) + 1
    except (ValueError, KeyError, TypeError) as exc:
        raise ValueError('Historical evaluation requires the original locked history and boundaries. No new test window was substituted.') from exc
    historical, dates = values[start:stop], index[start:stop]
    train, val, _, periods = selection.chronological_split(historical, dates)
    if periods != c['periods'] or selection.selection_fingerprint(train, val) != c['selection_data_fingerprint']:
        raise ValueError('Training or validation data changed since configuration selection. Forecasting stopped; the lock was not retuned.')
    snapshot = {'index': [list(p) for p in dates],
                'values': [float(v) if np.isfinite(v) else None for v in historical],
                'preparation': preparation(dataset, dates[-1][0])}
    return values, index, historical, dates, snapshot


def performance_key(c, disease, snapshot):
    return digest({'disease': disease, 'configuration_id': c['locked_configuration_id'],
                   'periods': c['periods'], 'model_version': VERSION,
                   'methodology_version': METHODOLOGY_VERSION, 'snapshot': snapshot})


def explanation(dataset, disease):
    if not dataset or not disease:
        return 'Upload and activate weekly data, then select a disease.'
    if synthetic(dataset):
        return 'Synthetic data uses Advanced Options → Quick Preview — Fixed Settings. Main forecasting is unavailable.'
    try:
        c, _, _ = resolve_lock(dataset, disease)
        selection.require_research_data(dataset, disease)
    except ValueError as exc:
        if str(exc).startswith(('Research dataset eligibility', 'Research disease must')):
            return 'Provisional workflow: selects model settings, evaluates historical performance, then generates a forecast. This can take several minutes. Not Thesis-Validated.'
        return str(exc)
    return ('Research workflow: checks performance for the locked configuration, then refits on all eligible history.' if c else
            'Research selection workflow: selects and locks model settings, evaluates the Final Test, then forecasts. This can take several minutes; selection does not grant adviser approval.')


def run_guided_forecast(dataset, disease, progress=None):
    emit = progress or (lambda stage, message: None)
    emit('validation', 'Checking active dataset structure.')
    if synthetic(dataset):
        raise ValueError('Synthetic data requires Quick Preview — Fixed Settings; no model lock was created.')
    checked = validate(pd.DataFrame(dataset['records']), dataset['metadata'])
    if checked['quality']['errors']:
        raise ValueError('Unresolved data validation errors.')
    emit('routing', 'Determining forecast workflow and checking installed configuration integrity.')
    c, root, origin = resolve_lock(dataset, disease)
    try:
        selection.require_research_data(dataset, disease)
    except ValueError:
        emit('provisional', 'Starting provisional validation — Not Thesis-Validated.')
        result = run_provisional(dataset, disease, progress=emit)
        result.update(workflow_mode='provisional', context='Provisional Forecast — Not Thesis-Validated')
        return result
    with threadpool_limits(limits=1):
        return research_forecast(dataset, disease, c, root, origin, emit)


def research_forecast(dataset, disease, c, root, origin, emit):
    attempt = uuid.uuid4().hex
    state = {'attempt_id': attempt, 'started_at': now(), 'selection': 'pending',
             'evaluation': 'pending', 'forecast': 'pending', 'origin': origin}
    try:
        if c is None:
            emit('selection', 'Selecting a research-scope configuration; adviser approval is not granted automatically.')
            values, index = model.training_series(dataset, disease)
            train, val, _, periods = selection.chronological_split(values, index)
            source = root
            root = source / 'attempts' / attempt
            c, audit = selection.select_configuration(train, val, disease, periods,
                checkpoint=lambda a: selection.write_json(root / 'search.json', a), progress=emit)
            c.pop('locked_configuration_id')
            c.update(validation_scope='research', disease=disease, methodology_version=METHODOLOGY_VERSION,
                     preparation_rules=preparation(dataset, index[-1][0]))
            c['locked_configuration_id'] = digest(c)
            root = source / c['locked_configuration_id']
            emit('lock', 'Saving immutable research configuration before Final Test evaluation.')
            selection.write_json(root / 'locked.json', c)
            audit['configuration'] = deepcopy(c)
            selection.write_json(root / 'search.json', audit)
            _, _, _, _, snapshot = historical_window(dataset, disease, c)
            selection.write_json(root / 'snapshot.json', snapshot)
            selection.write_json(source / 'selected.json', {'locked_configuration_id': c['locked_configuration_id']})
        check_lock(c, disease)
        state['selection'] = 'locked'
        selection.write_json(root / 'attempts' / (attempt + '.json'), state)
        values, index, historical, dates, snapshot = historical_window(dataset, disease, c)
        if c.get('preparation_rules', snapshot['preparation']) != snapshot['preparation']:
            raise ValueError('Training or validation preparation rules changed since configuration selection.')
        snapshot_path = root / 'snapshot.json'
        original = load_json(snapshot_path) if snapshot_path.exists() else None
        if original is not None and (original['preparation'] != snapshot['preparation'] or
                original['index'] != snapshot['index'] or original['values'][:-52] != snapshot['values'][:-52]):
            raise ValueError('Training or validation data or preparation rules changed since configuration selection.')
        if original is None:
            selection.write_json(snapshot_path, snapshot)
        key = performance_key(c, disease, snapshot)
        performance_path = root / 'performance' / (key + '.json')
        emit('performance', 'Checking historical performance against the original locked window.')
        evidence = load_json(performance_path) if performance_path.exists() else None
        # Only completed, fingerprinted evidence is reusable. Legacy metrics are recomputed.
        if (evidence is None or evidence.get('compatibility_key') != key or evidence.get('status') != 'complete'
                or evidence.get('payload_hash') != digest(evidence.get('result'))):
            evaluated = {'metrics': {}, 'warnings': [], 'configuration': deepcopy(c)}
            model.retrospective_evaluation(evaluated, historical, dates, c, disease, progress=emit)
            evidence = {'status': 'complete', 'compatibility_key': key, 'snapshot': snapshot,
                        'methodology_version': METHODOLOGY_VERSION, 'evaluated_at': now(),
                        'test_outcomes_revised': bool(original and original['values'][-52:] != snapshot['values'][-52:]),
                        'result': evaluated, 'payload_hash': digest(evaluated)}
            selection.write_json(performance_path, evidence)
            reused = False
        else:
            emit('performance_reused', 'Reusing compatible completed performance for the original historical window.')
            reused = True
        state['evaluation'] = 'complete'
        selection.write_json(root / 'attempts' / (attempt + '.json'), state)
        emit('operational_refit', 'Refitting locked settings on all eligible history for one 52-week future path.')
        result = model.run(dataset, disease, c, defer_evaluation=True, progress=emit)
        if result.get('failure_reason'):
            raise ValueError(result['failure_reason'])
        result.update({k: deepcopy(evidence['result'][k]) for k in ('metrics', 'evaluation', 'horizon_metrics')})
        result['warnings'].extend(evidence['result']['warnings'])
        result.update(workflow_mode='research', status='RESEARCH', research_validated=bool(c.get('approved')),
            context='Research Forecast' + ('' if c.get('approved') else ' — Adviser Approval Pending'),
            forecast_label='Research Forecast', methodology_version=METHODOLOGY_VERSION,
            dataset_fingerprint=digest({'records': dataset['records'], 'metadata': dataset['metadata'], 'disease': disease}),
            history=[float(v) if np.isfinite(v) else None for v in values],
            historical_evaluation_index=[list(p) for p in dates],
            historical_evaluation_values=snapshot['values'],
            performance_provenance={k: evidence[k] for k in ('compatibility_key', 'methodology_version', 'evaluated_at', 'test_outcomes_revised')},
            performance_reused=reused,
            validation_metrics={'sarima': c.get('selection_diagnostics', {}).get('sarima', {}).get('validation'),
                                'hybrid_seed_median': c.get('selection_diagnostics', {}).get('nnar', {}).get('median_validation')},
            validation_seed_metrics=c.get('selection_diagnostics', {}).get('nnar', {}).get('seeds', []))
        result['shape_diagnostics'] = shape_diagnostics(result['evaluation']['actual'], result['evaluation']['predictions'], result['evaluation']['index'])
        result['interpretation'] = interpretation(result)
        state.update(forecast='complete', completed_at=now())
        result['run_metadata'] = {**state, 'artifact_directory': str(root)}
        selection.write_json(root / 'attempts' / (attempt + '.json'), state)
        selection.write_json(root / 'results' / (attempt + '.json'), result)
        return result
    except Exception as exc:
        state.update(status='failed', failed_at=now(), failure_reason=str(exc))
        selection.write_json(root / 'attempts' / (attempt + '.json'), state)
        raise
