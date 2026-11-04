"""Descriptive coverage assessment; never a gate to the modeling workflow."""
from .forecasting.config import CANDIDATE_BLOCKS


def coverage_summary(rows):
    observed = {(r['year'], r['month_number']) for r in rows
                if r['observation_status'] in ('observed', 'observed_zero') and r['consultation_count'] is not None}
    zeros = {(r['year'], r['month_number']) for r in rows if r['observation_status'] == 'observed_zero'}
    years = sorted({y for y, _ in observed})
    available = (2016, 2017, 2018, 2019, 2021, 2023, 2024, 2025)
    return dict(top5_year_count=len(years), reported_month_count=len(observed), observed_zero_count=len(zeros),
                available_report_years=list(available), missing_years=sorted(set(available) - set(years)),
                missing_months=[f'{y}-{m:02}' for y in available for m in range(1, 13) if (y, m) not in observed],
                coverage_summary=f'{len(observed)} reported months across {len(years)} reporting years; {len(zeros)} observed zeros. Unknown periods remain unavailable.')


def refresh_dataset(dataset):
    """Rebuild descriptive fields, dropping obsolete derived fields on old payloads."""
    if dataset is None:
        return None
    dataset = dict(dataset)
    old = {b['icd10_block']: b for b in dataset['blocks']}
    old_reasons = {f'{code}: {block["reason"]}' for code, block in old.items() if 'reason' in block}
    dataset['warnings'] = [w for w in dataset.get('warnings', []) if w not in old_reasons]
    dataset['blocks'] = [dict(icd10_block=code,
        icd10_description=old.get(code, {}).get('icd10_description', 'Not represented in this upload'),
        **coverage_summary([r for r in dataset['observations'] if r['icd10_block'] == code])) for code in CANDIDATE_BLOCKS]
    dataset['data_quality'] = {'assessment': 'coverage_described', 'candidate_count': len(CANDIDATE_BLOCKS),
                               'warnings': list(dataset['warnings'])}
    return dataset
