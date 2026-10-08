"""Deterministic source-to-weekly transformation with reviewable provenance."""
import base64
import hashlib
import io
import json
import re

import pandas as pd

from dashboard.config import (MAX_UPLOAD_BYTES, MAX_WORKBOOK_SHEETS, MAX_WORKSHEET_ROWS,
                              MAX_WORKSHEET_COLUMNS, MAX_WORKBOOK_CELLS)
from dashboard.weekly.data import REQUIRED, now, validate

LABELS = {'disease': 'Disease', 'year': 'Year', 'morbidity_week': 'Morbidity Week', 'case_count': 'Case Count'}
ALIASES = {
    'disease': ['disease', 'disease name', 'illness', 'diagnosis', 'condition'],
    'year': ['year', 'reporting year', 'report year', 'morbidity year'],
    'morbidity_week': ['morbidity week', 'week', 'week no', 'week number', 'epi week', 'epidemiological week', 'mw'],
    'case_count': ['case count', 'cases', 'case total', 'total cases', 'number of cases', 'no of cases', 'count', 'total'],
    'population': ['population', 'age group', 'age range'],
    'case_classification': ['case classification', 'classification', 'case status'],
    'source_system': ['source system', 'source'], 'reporting_status': ['reporting status', 'reporting completeness'],
    'dataset_type': ['dataset type', 'data type'], 'location': ['location', 'city'],
    'week_start_date': ['week start date', 'week starting'], 'source_date': ['source date'],
    'date_extracted': ['date extracted', 'extraction date'], 'provenance': ['provenance', 'source reference'],
}


def normalized(value):
    return re.sub(r'[^a-z0-9]+', ' ', str(value).lower()).strip()


def year_header(value):
    try:
        number = float(value)
        return int(number) if number.is_integer() and 1900 <= number <= 9999 else None
    except (ValueError, TypeError):
        return None


def sheet_hint(name):
    if not name or non_data_name(name) or re.fullmatch(r'(sheet\s*\d*|data|records|weekly data|surveillance|table\s*\d*)', name.strip(), re.I):
        return None
    return name  # Preserve source spelling, including combined disease categories.


def non_data_name(name):
    return bool(re.match(r'^(notes?|read\s*me|instructions?|summary|overview|contents|cover|legend|definitions?|guide|documentation|metadata|changelog)(\b|\d)', normalized(name or '')))


def plausible_columns(sheet, field):
    """Prefer field meaning; use observed types only for unnamed/unknown fields."""
    plausible = []
    for col in sheet['columns']:
        base = re.sub(r' \(column \d+\)$', '', col)
        label = normalized(base)
        meanings = {key for key, aliases in ALIASES.items() if label in aliases}
        if field in meanings:
            plausible.append(col)  # Named fields may contain invalid values; validation reports them.
            continue
        if meanings or label in ('month', 'quarter', 'date', 'notes', 'remarks'):
            continue
        if year_header(base) is not None:
            continue  # Year-headed case columns belong to the automatic wide-table transform.
        values = [r[col] for r in sheet['rows'][:100] if r.get(col) not in (None, '')
                  and normalized(r.get(col)) not in ('total', 'grand total', 'subtotal')]
        if not values:
            continue
        numbers = pd.to_numeric(pd.Series(values), errors='coerce')
        numeric = numbers.notna()
        if field == 'disease' and not numeric.any():
            plausible.append(col)
        elif field == 'year' and numeric.all() and ((numbers % 1 == 0) & numbers.between(1900, 9999)).all():
            plausible.append(col)
        elif field == 'morbidity_week' and numeric.all() and ((numbers % 1 == 0) & numbers.between(1, 53)).all():
            plausible.append(col)
        elif field == 'case_count' and numeric.all() and ((numbers % 1 == 0) & (numbers >= 0)).all():
            plausible.append(col)
    return plausible


def inspect_sheet(raw, name):
    raw = raw.fillna('')
    if raw.empty:
        return {'name': name or 'CSV file', 'worksheet': name, 'columns': [], 'rows': [], 'header_row': 1,
                'original_row_count': 0, 'mapping': {}, 'year_columns': [], 'kind': 'rows', 'disease_hint': None,
                'needs_mapping': True, 'unresolved': list(REQUIRED), 'problems': [],
                'suggest_exclude': True, 'exclusion_reason': 'This worksheet is empty.', 'default_included': False}
    candidates = []
    for index in range(min(20, len(raw))):
        values = raw.iloc[index].tolist()
        found = {field for field, aliases in ALIASES.items() if field in REQUIRED
                 and any(normalized(value) in aliases for value in values)}
        years = sum(year_header(v) is not None for v in values)
        score = len(found) + (2 if 'morbidity_week' in found and years else 0)
        candidates.append((score, -index))
    header = -max(candidates)[1] if candidates else 0
    columns, seen = [], {}
    for i, value in enumerate(raw.iloc[header].tolist()):
        label = str(value) if str(value).strip() else f'Unnamed column {i + 1}'
        seen[label] = seen.get(label, 0) + 1
        columns.append(label if seen[label] == 1 else f'{label} (column {i + 1})')
    body = raw.iloc[header + 1:].copy()
    body.columns = columns
    records = json.loads(body.to_json(orient='records', date_format='iso'))
    mapping, ambiguous = {}, []
    for field, aliases in ALIASES.items():
        matches = [col for col in columns if normalized(col) in aliases or
                   (re.search(r' \(column \d+\)$', col) and normalized(re.sub(r' \(column \d+\)$', '', col)) in aliases)]
        if len(matches) == 1:
            mapping[field] = matches[0]
        elif len(matches) > 1:
            ambiguous.append(field)
    # Duplicate year headings retain separate source columns; validation then
    # exposes duplicate disease/year/week records instead of dropping a column.
    year_columns = [col for col in columns if year_header(re.sub(r' \(column \d+\)$', '', col)) is not None]
    kind = 'week_by_year' if mapping.get('morbidity_week') and year_columns and not mapping.get('year') else 'rows'
    if kind == 'week_by_year':
        mapping.pop('case_count', None)  # A cross-year total is not a weekly/year observation.
    hint = sheet_hint(name)
    problems = []
    if hint and mapping.get('disease'):
        labels = {str(r[mapping['disease']]) for r in records if str(r.get(mapping['disease'], '')).strip()}
        if labels and labels != {hint}:
            problems.append('The worksheet name and Disease column do not agree. Choose which source to use below.')
    if not mapping.get('disease') and hint:
        mapping['disease'] = '__worksheet__'
    required = ['disease', 'morbidity_week'] if kind == 'week_by_year' else REQUIRED
    unresolved = [field for field in required if field not in mapping or field in ambiguous]
    if problems and 'disease' not in unresolved:
        unresolved.append('disease')
    # Non-data names are suggestions, not an irreversible classification. A
    # clearly structured weekly table stays included even if named Summary.
    recognizable = (kind == 'week_by_year' or all(field in mapping for field in ('year', 'morbidity_week', 'case_count')))
    suggest_exclude = non_data_name(name) or not records
    default_included = bool(records) and not (non_data_name(name) and not recognizable)
    return {'name': name or 'CSV file', 'worksheet': name, 'columns': columns, 'rows': records,
            'header_row': header + 1, 'original_row_count': len(records), 'mapping': mapping,
            'year_columns': year_columns, 'kind': kind, 'disease_hint': hint,
            'needs_mapping': bool(unresolved or problems), 'unresolved': unresolved, 'problems': problems,
            'suggest_exclude': suggest_exclude, 'default_included': default_included,
            'exclusion_reason': 'This looks like a notes, instructions or summary worksheet. Exclude it unless it contains weekly case records.' if non_data_name(name) else 'This worksheet has no data rows.' if not records else None}


def read_source(contents, filename):
    try:
        raw = base64.b64decode(contents.split(',', 1)[1], validate=True)
    except Exception as exc:
        raise ValueError('We could not read this upload. Please select the file again.') from exc
    if len(raw) > MAX_UPLOAD_BYTES:
        raise ValueError('This file is too large. Please upload a file smaller than 10 MB.')
    extension = (filename or '').rsplit('.', 1)[-1].lower()
    if extension not in ('csv', 'xlsx'):
        raise ValueError('Please upload a CSV or XLSX file. PDFs can be kept as source references.')
    try:
        if extension == 'csv':
            frames = {None: pd.read_csv(io.BytesIO(raw), header=None, keep_default_na=False, sep=None, engine='python')}
        else:
            with pd.ExcelFile(io.BytesIO(raw)) as workbook:
                if len(workbook.sheet_names) > MAX_WORKBOOK_SHEETS:
                    raise ValueError('This workbook has too many worksheets. Please split it into smaller files.')
                frames = {name: workbook.parse(name, header=None, keep_default_na=False) for name in workbook.sheet_names}
    except ValueError as exc:
        raise ValueError('We could not read the tables in this file. Check that it is a valid CSV or XLSX and try again.') from exc
    except Exception as exc:
        raise ValueError('We could not open this file. Please save a fresh CSV or XLSX copy and try again.') from exc
    sheets, cells = [], 0
    for name, frame in frames.items():
        cells += frame.size
        if len(frame) > MAX_WORKSHEET_ROWS or len(frame.columns) > MAX_WORKSHEET_COLUMNS or cells > MAX_WORKBOOK_CELLS:
            raise ValueError('This workbook is too large to prepare safely. Please split it into smaller files.')
        sheets.append(inspect_sheet(frame, name))
    if not sheets:
        raise ValueError('There are no data rows in this file.')
    return {'filename': filename, 'file_sha256': hashlib.sha256(raw).hexdigest(), 'uploaded_at': now(), 'sheets': sheets}


class MappingNeeded(ValueError):
    """Readable file whose field mapping needs an explicit user decision."""


def transform_sheet(sheet, choice=None):
    if choice is None and sheet['needs_mapping']:
        raise MappingNeeded('We could not identify all required fields automatically. Please help us match the columns.')
    mapping = dict(sheet['mapping'])
    if choice is not None:
        mapping.update(choice.get('mapping', {}))
    if sheet['problems'] and not (choice or {}).get('mapping', {}).get('disease'):
        raise MappingNeeded('The worksheet name and Disease column disagree. Please choose the Disease source for this worksheet.')
    chosen = [v for field, v in mapping.items() if field in REQUIRED and v and not v.startswith('__')]
    if len(chosen) != len(set(chosen)):
        raise MappingNeeded('Please choose a different source column for each field.')
    required = ['disease', 'morbidity_week'] if sheet['kind'] == 'week_by_year' else REQUIRED
    for field in required:
        source = mapping.get(field)
        if field == 'morbidity_week' and normalized(source) in ('month', 'reporting month', 'quarter'):
            raise MappingNeeded('Monthly or quarterly totals cannot be treated as weekly case counts. Please choose a morbidity-week column or upload weekly records.')
        if source == '__worksheet__' and field == 'disease' and sheet['worksheet']:
            continue
        if source == '__entered__' and field in ('disease', 'year') and (choice or {}).get(field) not in (None, ''):
            continue
        if source not in sheet['columns']:
            raise MappingNeeded(f'Please choose a source for {LABELS[field]}.')
    changes, warnings, records, excluded = [], list(sheet['problems']), [], []
    for field in required:
        source = mapping[field]
        if source == '__worksheet__':
            changes.append(f'Disease detected from worksheet name: {sheet["worksheet"]}')
        elif source == '__entered__':
            changes.append(f'{LABELS[field]} supplied during review: {choice[field]}')
        else:
            changes.append(f'“{source}” matched to {LABELS[field]}.')
    if sheet['problems'] and choice is not None:
        warnings.append('The worksheet/column difference was reviewed. The selected disease source is recorded in the transformation details.')
    if sheet['kind'] == 'week_by_year':
        changes.append('Year columns were unfolded into separate weekly observations; counts were not added together.')
    for index, original in enumerate(sheet['rows']):
        if all(value is None or str(value).strip() == '' for value in original.values()):
            excluded.append({'row': sheet['header_row'] + index + 1, 'reason': 'Empty source row'})
            continue
        week_value = original.get(mapping.get('morbidity_week'))
        if normalized(week_value) in ('total', 'grand total', 'subtotal',
                                      'source reported total for verification'):
            excluded.append({'row': sheet['header_row'] + index + 1, 'reason': 'Source total row, not a weekly observation'})
            continue
        base = {}
        for field, source in mapping.items():
            if source == '__worksheet__':
                base[field] = sheet['worksheet']
            elif source == '__entered__':
                base[field] = choice.get(field)
            elif source in original:
                base[field] = original[source]
        base.update(source_worksheet=sheet['worksheet'], source_row=sheet['header_row'] + index + 1)
        if sheet['kind'] == 'week_by_year':
            for col in sheet['year_columns']:
                records.append({**base, 'year': year_header(re.sub(r' \(column \d+\)$', '', col)), 'case_count': original[col], 'source_year_column': col})
        else:
            records.append(base)
    used = set(mapping.values()) | set(sheet['year_columns'])
    unused = [col for col in sheet['columns'] if col not in used]
    if unused:
        changes.append(f'{len(unused)} source columns were not required for modeling; the original data remain available for review.')
    if excluded:
        changes.append(f'{len(excluded)} empty or total rows were kept in the original preview but not treated as weekly observations.')
        totals = [r['row'] for r in excluded if r['reason'].startswith('Source total')]
        if totals:
            warnings.append(f'Automatic fix: excluded summary totals at worksheet rows {totals}. These are not weekly observations. Original values are retained; no weekly counts were changed. Open "Review automatically excluded rows" in this worksheet\'s "Review and adjust" section before confirming.')
    return records, {'worksheet': sheet['worksheet'], 'mapping': mapping, 'method': sheet['kind'],
                     'choices': choice, 'changes': changes, 'warnings': warnings, 'excluded_rows': excluded,
                     'unused_columns': unused, 'prepared_row_count': len(records)}


def resolution_key(row):
    return json.dumps([row.get('source_worksheet'), row.get('source_row'), row['disease'],
                       int(row['year']), int(row['morbidity_week'])], ensure_ascii=False)


def resolved_records(rows, metadata):
    resolutions = metadata.get('blank_resolutions', {})
    if not resolutions:
        return rows
    result = []
    for original in rows:
        row = dict(original)
        try:
            decision = resolutions.get(resolution_key(row))
        except (ValueError, TypeError):
            decision = None  # Let normal validation report malformed source fields.
        if decision:
            if decision['resolution'] == 'nonexistent':
                if int(row['morbidity_week']) != 53 or metadata.get('year_lengths', {}).get(str(int(row['year']))) != 52:
                    raise ValueError('A nonexistent week exclusion requires a documented 52-week year and a blank week-53 observation.')
                continue
            row['case_count'] = decision['value']
        result.append(row)
    return result


def prepare(document, choices=None, metadata=None, allow_partial=False):
    choices = choices or {}
    records, transformations, units, failures = [], [], [], []
    meta = dict(metadata or {})
    meta.update(source_file=document['filename'], source_file_sha256=document['file_sha256'],
                transformation_method='weekly-source-transform-v2')
    for i, sheet in enumerate(document['sheets']):
        choice = choices.get(str(i))
        included = (choice or {}).get('included', sheet.get('default_included', True))
        unit = {'index': i, 'name': sheet['name'], 'included': bool(included), 'records': [], 'errors': [],
                'status': 'excluded', 'unresolved': list(sheet['unresolved'])}
        report = {'worksheet': sheet['worksheet'], 'sheet_index': i, 'included': bool(included),
                  'choices': choice, 'changes': [], 'warnings': [], 'prepared_row_count': 0}
        if included:
            try:
                rows, transformed = transform_sheet(sheet, choice)
                rows = resolved_records(rows, meta)
                report.update(transformed)
                checked = validate(pd.DataFrame(rows), meta, document['filename'])
                unit.update(records=checked['records'], quality=checked['quality'], unresolved=[],
                            status='invalid' if checked['quality']['errors'] else 'ready',
                            errors=[f"Worksheet “{sheet['name']}”: {error}" for error in checked['quality']['errors']])
                records.extend(rows)
            except ValueError as exc:
                message = f"Worksheet “{sheet['name']}”: {exc}"
                failures.append(message)
                unit.update(status='needs_mapping' if isinstance(exc, MappingNeeded) else 'invalid', errors=[message])
        else:
            report['changes'] = ['Excluded from the active dataset by the worksheet selection. Original source retained for review.']
        units.append(unit)
        transformations.append(report)
    history = {'source': document, 'sheets': transformations, 'prepared_at': now(), 'no_zero_filling': True}
    if failures or not records:
        message = '\n'.join(failures) if failures else 'Include at least one worksheet containing weekly observations.'
        if not allow_partial:
            raise MappingNeeded(message)
        return {'review_only': True, 'transformation': history, 'worksheet_units': units,
                'worksheet_choices': choices, 'review_message': message, 'review_metadata': meta}
    result = validate(pd.DataFrame(records), meta, document['filename'])
    # Workbook-level duplicate checks still run after independently preparing
    # included sheets, and identify every involved worksheet.
    for duplicate in result['quality']['duplicates']:
        for unit in units:
            if any(all(row[k] == duplicate[k] for k in ('disease', 'year', 'morbidity_week')) for row in unit['records']):
                error = f"Worksheet “{unit['name']}”: {duplicate['disease']} {duplicate['year']} week {duplicate['morbidity_week']} repeats within the included worksheets."
                if error not in unit['errors']:
                    unit['errors'].append(error)
                unit['status'] = 'invalid'
    result.update(transformation=history, worksheet_units=units, worksheet_choices=choices)
    result['audit'].append({'event': 'prepared', 'at': now(), 'file_sha256': document['file_sha256']})
    return result


def update_facts(pending, facts):
    """Apply explicit user declarations, never replace established row facts."""
    metadata = {**pending['metadata'], **{k: v for k, v in facts.items() if v not in ('', None) and ':' not in k}}
    if facts.get('reporting_status') == 'complete' and not str(metadata.get('reporting_reference', '')).strip():
        raise ValueError('Historical reporting period complete requires a CESU/source documentation reference. Enter the report or email title, issuer, date and covered period in CESU/source evidence for historical completeness, or leave Reporting Status unspecified. Completeness remains unchanged.')
    lengths = dict(metadata.get('year_lengths', {}))
    for key, value in facts.items():
        if key.startswith('calendar:') and value not in ('', None):
            if not str(metadata.get('calendar_reference', '')).strip():
                raise ValueError('Reporting-year lengths require a CESU/source calendar documentation reference. Enter its title, issuer, covered years and page/link in CESU/source evidence for reporting-year lengths, or leave year lengths unspecified.')
            if value not in (52, 53):
                raise ValueError('Please choose 52 or 53 weeks only when established by the source calendar.')
            lengths[key.split(':')[1]] = value
    if lengths:
        metadata['year_lengths'] = lengths
    resolutions = dict(metadata.get('blank_resolutions', {}))
    for key, action in facts.items():
        if not key.startswith('resolution:') or not action:
            continue
        index = int(key.split(':')[1])
        row = pending['records'][index]
        if row['case_count'] is not None:
            raise ValueError('Only blank source counts may be resolved in this review.')
        reference = str(facts.get(f'evidence:{index}') or '').strip()
        if not reference:
            raise ValueError(f"{row['disease']} {row['year']} week {row['morbidity_week']}: supply source evidence for the blank-count decision.")
        if action not in ('zero', 'missing', 'nonexistent', 'corrected'):
            raise ValueError('Unknown blank-count resolution.')
        value = 0 if action == 'zero' else facts.get(f'corrected:{index}') if action == 'corrected' else None
        if action == 'corrected' and (isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0 or value % 1):
            raise ValueError('A corrected count must be a source-established non-negative integer.')
        if action == 'nonexistent' and not str(metadata.get('calendar_reference', '')).strip():
            raise ValueError('A nonexistent reporting week needs documented source calendar evidence.')
        resolutions[resolution_key(row)] = {'resolution': action, 'value': value, 'reference': reference,
                                           'original': dict(row), 'at': now()}
    if resolutions:
        metadata['blank_resolutions'] = resolutions
    if metadata == pending['metadata']:
        return pending  # Confirmation after Apply must not validate the same data again.
    revised = resolved_records(pending['records'], metadata)
    updated = validate(pd.DataFrame(revised), metadata, metadata.get('source_file'))
    updated['metadata']['uploaded_at'] = pending['metadata']['uploaded_at']
    from dashboard.weekly.data import digest
    updated['id'] = digest({'records': updated['records'], 'metadata': updated['metadata']})
    updated['transformation'] = pending.get('transformation')
    for key in ('worksheet_units', 'worksheet_choices'):
        if key in pending:
            updated[key] = pending[key]
    if pending.get('transformation'):
        # Source facts do not change column mappings. Refresh worksheet checks
        # from already prepared records instead of unfolding the workbook again.
        units = json.loads(json.dumps(pending.get('worksheet_units', [])))
        history = json.loads(json.dumps(pending['transformation']))
        for unit in units:
            if not unit['included']:
                continue
            sheet = history['source']['sheets'][unit['index']]
            rows = [row for row in updated['records'] if row.get('source_worksheet') == sheet['worksheet']]
            if rows:
                checked = validate(pd.DataFrame(rows), metadata, metadata.get('source_file'))
                errors = [f"Worksheet “{unit['name']}”: {error}" for error in checked['quality']['errors']]
                unit.update(records=checked['records'], quality=checked['quality'], errors=errors,
                            status='invalid' if errors else 'ready')
            else:
                unit.update(records=[], errors=[], status='ready')
            history['sheets'][unit['index']]['prepared_row_count'] = len(rows)
            for duplicate in updated['quality']['duplicates']:
                if any(all(row[k] == duplicate[k] for k in ('disease', 'year', 'morbidity_week')) for row in rows):
                    unit['errors'].append(f"Worksheet “{unit['name']}”: repeated disease/year/week among included worksheets.")
                    unit['status'] = 'invalid'
        updated['worksheet_units'] = units
        updated['transformation'] = history
    updated['audit'] = pending['audit'] + [{'event': 'reviewed', 'at': now()}]
    return updated
