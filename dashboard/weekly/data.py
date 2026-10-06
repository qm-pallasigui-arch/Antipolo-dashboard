"""Lossless morbidity-week ingestion and explicit research eligibility."""
import hashlib
import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd

REQUIRED = ['disease', 'year', 'morbidity_week', 'case_count']
TECHNICAL = 'Technical / Retrospective Evaluation'
THESIS = 'Final Thesis Evaluation'
DEMO = 'Synthetic / Demo Data'


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def parse_upload(contents, filename):
    from dashboard.weekly.transform import prepare, read_source
    return pd.DataFrame(prepare(read_source(contents, filename))['records'])


def validate(frame, metadata=None, filename=None):
    metadata = dict(metadata or {})
    if not set(REQUIRED).issubset(frame.columns):
        raise ValueError('Required columns: ' + ', '.join(REQUIRED))
    if frame.empty:
        raise ValueError('No observations supplied.')
    frame = frame.copy()
    errors, warnings = [], []
    row_metadata_incomplete = []
    for field in ['population', 'case_classification', 'location', 'source_system', 'source_file',
                  'provenance', 'frequency', 'dataset_type', 'reporting_status', 'source_date', 'date_extracted']:
        if field not in frame or metadata.get(field) is not None:
            continue
        supplied = [str(x) for x in frame[field] if pd.notna(x) and str(x).strip()]
        if len(supplied) == len(frame) and len(set(supplied)) == 1:
            metadata[field] = supplied[0]
        elif supplied:
            row_metadata_incomplete.append(field)
    for column, low, high in [('year', 1900, 9999), ('morbidity_week', 1, 53)]:
        numeric = pd.to_numeric(frame[column], errors='coerce')
        bad = numeric.isna() | ~np.isfinite(numeric) | (numeric % 1 != 0) | ~numeric.between(low, high)
        if bad.any():
            rows = list(dict.fromkeys(frame.loc[bad, 'source_row'].tolist())) if 'source_row' in frame else (np.flatnonzero(bad) + 2).tolist()
            values = list(dict.fromkeys(str(v) for v in frame.loc[bad, column]))
            guidance = ('Expected a whole week number from 1 to 53. Correct these cells in the source and upload again, '
                        'or exclude this worksheet to use the other sheets. No week numbers were guessed.') if column == 'morbidity_week' else 'Expected a whole reporting year from 1900 to 9999.'
            raise ValueError(f'Invalid {column} at source rows {rows}; values: {values[:10]}. {guidance}')
        frame[column] = numeric.astype(int)
    if frame.disease.map(lambda x: not isinstance(x, str) or not x.strip()).any():
        raise ValueError('Disease labels must be nonblank text.')
    # Retain source spelling, punctuation and distinct disease categories.
    labels = sorted(frame.disease.unique())
    normalized = [x.strip().casefold() for x in labels]
    if len(set(normalized)) != len(labels) or any(x != x.strip() for x in labels):
        errors.append('Inconsistent disease labels; resolve source spelling/whitespace explicitly.')
    blank = frame.case_count.map(lambda x: pd.isna(x) or (isinstance(x, str) and not x.strip()))
    counts = pd.to_numeric(frame.case_count, errors='coerce')
    bad = ~blank & (counts.isna() | ~np.isfinite(counts) | (counts < 0) | (counts % 1 != 0))
    if bad.any():
        raise ValueError(f'Case counts must be non-negative integers or blank; rows {(np.flatnonzero(bad) + 2).tolist()}')
    frame['case_count'] = counts.where(~blank, np.nan)
    keys = ['disease', 'year', 'morbidity_week']
    duplicates = frame.loc[frame.duplicated(keys, keep=False), keys].to_dict('records')
    if duplicates:
        errors.append('Duplicate observations')
    lengths = metadata.get('year_lengths', {})
    if not isinstance(lengths, dict) or any(type(v) is not int or v not in (52, 53) for v in lengths.values()):
        raise ValueError('year_lengths must map reporting years to 52 or 53, based on the source calendar.')
    missing, calendar_unknown = [], []
    for disease, group in frame.groupby('disease', sort=False):
        pairs = set(zip(group.year, group.morbidity_week))
        start, end = min(pairs), max(pairs)
        for year in range(start[0], end[0] + 1):
            last = lengths.get(str(year))
            if last == 52 and (year, 53) in pairs:
                errors.append(f'{disease}: supplied week 53 conflicts with calendar for {year}; record preserved.')
            if year < end[0] and last is None:
                calendar_unknown.append(year)
            # Weeks 1–52 exist; week 53 is included only when supplied/established.
            top = end[1] if year == end[0] else (last or (53 if (year, 53) in pairs else 52))
            first = start[1] if year == start[0] else 1
            missing.extend({'disease': disease, 'year': year, 'morbidity_week': week}
                           for week in range(first, top + 1) if (year, week) not in pairs)
    if missing:
        warnings.append('Missing weeks detected; retained as missing, without zero filling or imputation.')
    if blank.any():
        warnings.append('Blank/unreported observations are missing, not zero.')
    week53 = frame.loc[frame.morbidity_week == 53, keys].to_dict('records')
    if week53:
        warnings.append('Week 53 present and preserved; statistical treatment pending unless explicitly configured.')
    if calendar_unknown:
        warnings.append('Reporting calendar incomplete: week 53 existence is unresolved for some year boundaries.')
    metadata.setdefault('frequency', 'weekly')
    metadata.setdefault('source_file', filename)
    metadata.setdefault('date_extracted', None)
    metadata['uploaded_at'] = now()
    excluded = []
    for row in frame.to_dict('records'):
        status = row.get('reporting_status') or metadata.get('reporting_status') or 'unknown'
        if str(status).lower() != 'complete':
            excluded.append({**{k: row[k] for k in keys}, 'reporting_status': status})
    if excluded:
        warnings.append('Weeks with incomplete or unknown reporting status are excluded from training; raw values remain visible.')
    reasons = []
    if row_metadata_incomplete:
        reasons.append('Row metadata incomplete or inconsistent: ' + ', '.join(row_metadata_incomplete))
    expected = {'population': '5–19', 'case_classification': 'confirmed', 'location': 'Antipolo City',
                'frequency': 'weekly', 'dataset_type': 'real'}
    for field, required in expected.items():
        supplied = metadata.get(field)
        values = set(str(x) for x in frame[field] if pd.notna(x) and str(x).strip()) if field in frame else set()
        if supplied is not None:
            values.add(str(supplied))
        # ASCII hyphen is an accepted age-range spelling, not a source relabel.
        if field == 'population':
            values = {x.replace('-', '–') for x in values}
        if values != {required}:
            reasons.append(f'{field}: requires established {required}; found {sorted(values) or "unknown"}.')
        if field == 'dataset_type' and len(values) > 1:
            errors.append('Synthetic and real records cannot be mixed in one active dataset.')
    if metadata.get('source_system') != 'CESU/PIDSAR' or not metadata.get('source_file') or not metadata.get('provenance'):
        reasons.append('Source metadata incomplete: CESU/PIDSAR provenance and source file required.')
    if 'source_system' in frame and any(str(x).strip() and str(x) != metadata.get('source_system') for x in frame.source_system if pd.notna(x)):
        reasons.append('Source metadata mismatch between row-level and dataset-level source systems.')
    if metadata.get('frequency') != 'weekly' or ('frequency' in frame and any(str(x).strip() and str(x) != 'weekly' for x in frame.frequency if pd.notna(x))):
        errors.append('Frequency mismatch: canonical observations must be weekly.')
    approved = metadata.get('approved_diseases', [])
    if not isinstance(approved, list) or not set(labels).issubset(approved):
        reasons.append('Disease scope awaits documented approval.')
    protocol = metadata.get('weekly_protocol', {})
    minimum = protocol.get('minimum_complete_weeks') if isinstance(protocol, dict) else None
    if (not isinstance(protocol, dict) or protocol.get('approved') is not True
            or not protocol.get('approval_reference') or type(minimum) is not int or minimum < 1):
        reasons.append('Sufficient history cannot be established until the weekly protocol is approved.')
    else:
        for disease, group in frame.groupby('disease'):
            n = sum(pd.notna(r['case_count']) and str(r.get('reporting_status') or metadata.get('reporting_status', '')).lower() == 'complete'
                    for r in group.to_dict('records'))
            if n < minimum:
                reasons.append(f'{disease}: insufficient complete history under approved protocol.')
    if missing or blank.any():
        if not isinstance(protocol, dict) or not protocol.get('gap_evaluation_approval'):
            reasons.append('Formal evaluation implications of missing observations require documented approval.')
    if week53 and (not isinstance(protocol, dict) or not protocol.get('week53_approval')):
        reasons.append('Week 53 statistical treatment awaits approval.')
    if calendar_unknown:
        reasons.append('Reporting-year calendar is unresolved.')
    reasons.extend(errors)
    if reasons:
        warnings.extend(r for r in reasons if r.startswith(('population:', 'case_classification:', 'Source metadata')))
    frame = frame.sort_values(keys, kind='stable')
    # JSON conversion retains blanks as null and never fabricates observations.
    records = json.loads(frame.to_json(orient='records', date_format='iso'))
    eligible = not reasons
    context = DEMO if metadata.get('dataset_type') == 'synthetic' else THESIS if eligible else TECHNICAL
    quality = {'statuses': errors + warnings or ['Complete'], 'errors': errors, 'warnings': warnings,
               'diseases': labels, 'observation_count': len(frame), 'year_coverage': [int(frame.year.min()), int(frame.year.max())],
               'week_coverage': {d: [list(min(zip(g.year, g.morbidity_week))), list(max(zip(g.year, g.morbidity_week)))] for d, g in frame.groupby('disease')},
               'missing_weeks': missing, 'duplicates': duplicates, 'week53': week53,
               'zero_case_weeks': frame.loc[frame.case_count == 0, keys].to_dict('records'),
               'blank_observations': frame.loc[blank, keys].to_dict('records'), 'excluded_from_training': excluded,
               'calendar_unknown_years': sorted(set(calendar_unknown))}
    identity = digest({'records': records, 'metadata': metadata})
    return {'id': identity, 'records': records, 'metadata': metadata, 'quality': quality,
            'eligible': eligible, 'eligibility_reasons': reasons, 'context': context,
            'audit': [{'event': 'uploaded', 'at': metadata['uploaded_at']}, {'event': 'validated', 'at': now()}]}


def activate(pending, current=None):
    if not pending or pending.get('review_only') or pending['quality']['errors']:
        raise ValueError('Resolve validation errors before activation.')
    result = json.loads(json.dumps(pending))
    history = list((current or {}).get('audit', []))
    if current and current.get('id'):
        history.append({'event': 'replaced', 'dataset': current['id'], 'at': now()})
    result['audit'] = history + result['audit'] + [
        {'event': event, 'dataset': result['id'], 'at': now()} for event in ('confirmed', 'activated')]
    return result


def demo():
    rows = [{'disease': 'Demo disease', 'year': 2024 + i // 52, 'morbidity_week': i % 52 + 1,
             'case_count': int(15 + 8 * np.sin(i / 8) + (i % 3)), 'reporting_status': 'complete'} for i in range(104)]
    return validate(pd.DataFrame(rows), {'dataset_type': 'synthetic', 'population': 'all-age',
                    'source_system': 'Synthetic generator', 'source_file': 'built-in demo',
                    'year_lengths': {str(y): 52 for y in range(2024, 2028)},
                    'notes': 'Artificial 52-week calendar for demonstration only.'})
