"""Assess each candidate without inventing Chapter 3 thresholds."""
from .config import CANDIDATE_BLOCKS, METHOD_PENDING


def provisional_policy(config):
    def decide(rows):
        count = sum(r['observation_status'] in ('observed', 'observed_zero') and r['consultation_count'] is not None for r in rows)
        ready = count >= config.min_observations
        return dict(eligible=ready, is_prototype=True, methodology_status='provisional',
                    configuration_signature=config.signature,
                    reason=f'Provisional readiness: {count} reported months; technical minimum {config.min_observations}. Residual feature availability is checked during fitting. Not a final thesis threshold.')
    return decide


def assess(rows, policy=None):
    observed = {(r['year'], r['month_number']) for r in rows
                if r['observation_status'] in ('observed', 'observed_zero') and r['consultation_count'] is not None}
    years = sorted({y for y, _ in observed})
    available = (2016, 2017, 2018, 2019, 2021, 2023, 2024, 2025)
    result = dict(eligible=False, readiness_status='methodology_configuration_required',
                  top5_year_count=len(years), reported_month_count=len(observed),
                  available_report_years=list(available),
                  missing_years=sorted(set(available) - set(years)),
                  missing_months=[f'{y}-{m:02}' for y in available for m in range(1, 13) if (y, m) not in observed],
                  reason=METHOD_PENDING)
    if not observed:
        result.update(readiness_status='not_ready', reason='No reported observations for this candidate block.')
    elif policy is not None:
        decision = policy(rows)
        if not isinstance(decision.get('eligible'), bool) or not decision.get('reason'):
            raise ValueError('Readiness policy must return an explicit decision and reason.')
        result.update(eligible=decision['eligible'], reason=decision['reason'],
                      readiness_status='ready' if decision['eligible'] else 'not_ready')
        result.update({key: decision[key] for key in ('is_prototype', 'methodology_status', 'configuration_signature') if key in decision})
    return result


def refresh_dataset(dataset, policy=None):
    """Recompute derived fields on reads, preserving source data and signatures."""
    if dataset is None:
        return None
    dataset = dict(dataset)
    old = {b['icd10_block']: b for b in dataset['blocks']}
    old_reasons = {f'{code}: {block["reason"]}' for code, block in old.items() if 'reason' in block}
    dataset['warnings'] = [w for w in dataset.get('warnings', []) if w not in old_reasons]
    dataset['blocks'] = [dict(icd10_block=code,
        icd10_description=old.get(code, {}).get('icd10_description', 'Not represented in this upload'),
        **assess([r for r in dataset['observations'] if r['icd10_block'] == code], policy)) for code in CANDIDATE_BLOCKS]
    dataset['warnings'].extend(f'{b["icd10_block"]}: {b["reason"]}' for b in dataset['blocks'] if not b['eligible'])
    return dataset
