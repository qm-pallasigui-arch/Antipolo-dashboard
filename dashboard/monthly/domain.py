"""Source semantics and deterministic eligibility, independent of any model."""
import calendar
import hashlib
import io
import json
import re
from datetime import datetime, timezone

import pandas as pd

AVAILABLE_YEARS = (2016, 2017, 2018, 2019, 2021, 2023, 2024, 2025)
UNAVAILABLE_YEARS = (2020, 2022)
OBSERVED = ('observed', 'observed_zero')
STATUSES = (*OBSERVED, 'city_report_unavailable', 'outside_annual_top5')
PROVENANCE = {
    'source_organization': 'Department of Health Regional Office IV-A CALABARZON',
    'source_database': 'Field Health Services Information System Database',
    'document_title': 'Top 5 Leading Infectious Diseases among School-Aged Children Aged 5–19 Years in Antipolo City, Rizal, 2016–2025',
    'population': 'Ages 5–19', 'geographic_scope': 'Antipolo City, Rizal',
    'frequency': 'Monthly', 'document_prepared_at': '2026-08-24',
    'known_unavailable_years': list(UNAVAILABLE_YEARS),
}
LIMITATIONS = ('Consultations through RHUs and public health facilities are not necessarily confirmed cases or unique individuals. '
               'Outside annual Top 5 means the count is unknown. Forecast eligibility does not indicate epidemiological importance. '
               'Forecasts are estimates of monthly consultations, not outbreak confirmation or future Top-5 rankings.')


class DataError(ValueError):
    pass


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def block_code(value):
    value = re.sub(r'\s+', '', str(value)).upper().replace('–', '-').replace('—', '-')
    if not re.fullmatch(r'[AB]\d{2}-[AB]\d{2}', value) or value[:3] > value[4:]:
        raise DataError(f'Invalid infectious-disease ICD-10 block: {value}')
    return value


def integer(value, label):
    if isinstance(value, bool) or pd.isna(value):
        raise DataError(f'{label} must be an integer.')
    try:
        number = float(value)
        if not number.is_integer():
            raise ValueError()
        return int(number)
    except (ValueError, TypeError, OverflowError):
        raise DataError(f'{label} must be an integer.') from None


def month_number(value):
    names = {name.lower(): n for n in range(1, 13) for name in (calendar.month_name[n], calendar.month_abbr[n])}
    number = names.get(str(value).strip().lower())
    number = number if number else integer(value, 'Month')
    if not 1 <= number <= 12:
        raise DataError('Month must be 1–12 or an English month name.')
    return number


def evaluate_forecast_eligibility(block_data):
    """Unique reported months, never raw row counts, determine eligibility."""
    presence = {r['year'] for r in block_data if r['year'] in AVAILABLE_YEARS and r['top5_present']}
    months = {(r['year'], r['month_number']) for r in block_data
              if r['year'] in AVAILABLE_YEARS and r['top5_present']
              and r['observation_status'] in OBSERVED and r['consultation_count'] is not None}
    missing_years = sorted(set(AVAILABLE_YEARS) - presence)
    missing_months = [f'{y}-{m:02}' for y in AVAILABLE_YEARS for m in range(1, 13) if (y, m) not in months]
    eligible = len(presence) == 8 and len(months) == 96
    reason = ('Block appears in all available reporting years and contains all required monthly observations.' if eligible
              else f'Block is absent from {len(missing_years)} available annual Top-5 report(s); {len(missing_months)} required monthly observation(s) are missing.')
    return dict(eligible=eligible, available_report_years=list(AVAILABLE_YEARS), required_available_years=8,
                top5_year_count=len(presence), required_top5_year_count=8, reported_month_count=len(months),
                required_reported_month_count=96, missing_years=missing_years, missing_months=missing_months, reason=reason)


def normalize(frame, source_file, raw_hash=None):
    frame = frame.copy()
    frame.columns = [str(c).strip().lower().replace(' ', '_').replace('-', '_') for c in frame.columns]
    aliases = {'icd_10_block': 'icd10_block', 'icd_10_description': 'icd10_description', 'month_number': 'month'}
    for old, new in aliases.items():
        if old in frame and new not in frame:
            frame = frame.rename(columns={old: new})
    required = {'year', 'month', 'icd10_block', 'icd10_description', 'consultation_count'}
    missing = required - set(frame.columns)
    if missing:
        raise DataError('Required columns missing: ' + ', '.join(sorted(missing)))
    if frame.empty or frame.columns.duplicated().any():
        raise DataError('Empty file or duplicate column names.')
    records, descriptions, presence = {}, {}, set()
    for row in frame.to_dict('records'):
        y, m = integer(row['year'], 'Year'), month_number(row['month'])
        if y not in (*AVAILABLE_YEARS, *UNAVAILABLE_YEARS):
            raise DataError('Year must be within the approved 2016–2025 study period.')
        code = block_code(row['icd10_block'])
        if pd.isna(row['icd10_description']) or not str(row['icd10_description']).strip():
            raise DataError(f'{code}: description is required.')
        description = ' '.join(str(row['icd10_description']).split())
        if code in descriptions and descriptions[code].casefold() != description.casefold():
            raise DataError(f'{code}: conflicting descriptions. Confirm source wording.')
        descriptions[code] = description
        key = (code, y, m)
        if key in records:
            raise DataError(f'Duplicate block/year/month: {key}')
        status = row.get('observation_status')
        status = None if pd.isna(status) else str(status).strip()
        value = row['consultation_count']
        if pd.isna(value):
            if status not in ('city_report_unavailable', 'outside_annual_top5'):
                raise DataError(f'{key}: missing required observed value; do not infer zero.')
            count = None
        else:
            count = integer(value, 'Consultation count')
            if count < 0:
                raise DataError('Consultation count cannot be negative.')
            inferred = 'observed_zero' if count == 0 else 'observed'
            if status and status != inferred:
                raise DataError(f'{key}: count conflicts with observation status.')
            status = inferred
        if y in UNAVAILABLE_YEARS and status != 'city_report_unavailable':
            raise DataError(f'{y}: city report is unavailable; numerical observations are not permitted.')
        if y in AVAILABLE_YEARS and status == 'city_report_unavailable':
            raise DataError(f'{y}: city report is available; cannot mark it city-wide unavailable.')
        if status in OBSERVED:
            presence.add((code, y))
        records[key] = (count, status)
    for y in AVAILABLE_YEARS:
        if sum(year == y for _, year in presence) > 5:
            raise DataError(f'{y}: more than five distinct blocks in an annual Top-5 report.')
    normalized = []
    for code, description in sorted(descriptions.items()):
        if not any(c == code for c, _ in presence):
            raise DataError(f'{code}: no historically reported observations.')
        for y in range(2016, 2026):
            for m in range(1, 13):
                present = (code, y) in presence
                item = records.get((code, y, m))
                if present and (item is None or item[1] not in OBSERVED):
                    raise DataError(f'{code} {y}-{m:02}: required monthly observation missing in a reported annual entry.')
                count, status = item or (None, 'city_report_unavailable' if y in UNAVAILABLE_YEARS else 'outside_annual_top5')
                normalized.append(dict(year=y, month=calendar.month_name[m], month_number=m,
                    icd10_block=code, icd10_description=description, consultation_count=count,
                    observation_status=status, top5_present=present, source_year_available=y in AVAILABLE_YEARS))
    signature = digest({'observations': normalized, 'provenance': PROVENANCE})
    dataset = dict(dataset_id=signature[:16], dataset_signature=signature, observations=normalized,
                   provenance=dict(PROVENANCE), source_file=source_file, raw_sha256=raw_hash,
                   uploaded_at=now(), validation_status='warning', warnings=['City reports unavailable for 2020 and 2022; no imputation applied.'])
    for row in normalized:
        row.update(dataset_id=dataset['dataset_id'], dataset_signature=signature, source_file=source_file)
    dataset['blocks'] = []
    for code, description in sorted(descriptions.items()):
        rows = [r for r in normalized if r['icd10_block'] == code]
        result = evaluate_forecast_eligibility(rows)
        dataset['blocks'].append(dict(icd10_block=code, icd10_description=description, **result))
        if not result['eligible']:
            dataset['warnings'].append(f'{code}: {result["reason"]}')
        zero_run = 0
        for row in rows:
            zero_run = zero_run + 1 if row['observation_status'] == 'observed_zero' else 0
            if zero_run == 3:
                dataset['warnings'].append(f'{code}: three or more consecutive reported zeros ending {row["year"]}-{row["month_number"]:02}; retained as reported.')
    return dataset


def parse_upload(raw, filename):
    if len(raw) > 10 * 1024 * 1024:
        raise DataError('File exceeds 10 MB.')
    try:
        if filename.lower().endswith('.csv'):
            frame = pd.read_csv(io.BytesIO(raw))
        elif filename.lower().endswith('.xlsx'):
            sheets = pd.read_excel(io.BytesIO(raw), sheet_name=None)
            frame = pd.concat(sheets.values(), ignore_index=True)
        else:
            raise DataError('Supported file types: CSV and XLSX.')
        return normalize(frame, filename, hashlib.sha256(raw).hexdigest())
    except DataError:
        raise
    except Exception as exc:
        raise DataError('Unreadable file. Use the documented monthly table format.') from exc


def annual_history(dataset, code):
    rows = [r for r in dataset['observations'] if r['icd10_block'] == code]
    return [dict(year=y, top5_present=any(r['top5_present'] for r in rows if r['year'] == y),
                 annual_total=sum(r['consultation_count'] for r in rows if r['year'] == y)
                 if any(r['top5_present'] for r in rows if r['year'] == y) else None,
                 status='reported' if any(r['top5_present'] for r in rows if r['year'] == y)
                 else 'city_report_unavailable' if y in UNAVAILABLE_YEARS else 'outside_annual_top5') for y in range(2016, 2026)]
