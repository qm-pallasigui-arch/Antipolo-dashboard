"""Rank comparable completed twelve-month hybrid forecasts, never source Top Five."""
import math
import secrets
from ..domain import now
from ..forecasting.config import CANDIDATE_BLOCKS, RANKING_SCOPE
from ..repositories.forecast_repository import is_current


def rank_forecasts(results, signature, group_id):
    months, seen, totals = None, set(), []
    context = None
    for result in results:
        if not is_current(result):
            raise ValueError('Rankings require completed Prophet + XGBoost results.')
        if result['dataset_signature'] != signature or result['forecast_run_group_id'] != group_id:
            raise ValueError('Cannot mix dataset versions or forecast groups.')
        mode = (result['is_prototype'], result['methodology_status'], result.get('configuration_signature'))
        if context is not None and context != mode:
            raise ValueError('Cannot mix prototype/final results or methodology configurations.')
        context = mode
        code = result['icd10_block']
        if code not in CANDIDATE_BLOCKS or code in seen:
            raise ValueError('Duplicate or unknown ranking block.')
        values = result['forecast_values']
        dates = [row['month'] for row in values]
        indexes = [int(d[:4]) * 12 + int(d[5:]) - 1 for d in dates]
        if len(dates) != 12 or indexes != list(range(indexes[0], indexes[0] + 12)):
            raise ValueError('Rankings require twelve consecutive calendar months.')
        if months is not None and months != dates:
            raise ValueError('Rankings require the same twelve calendar months.')
        counts = [row['consultation_count'] for row in values]
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0 for v in counts):
            raise ValueError('Invalid forecast count.')
        total = sum(counts)
        if not math.isfinite(total):
            raise ValueError('Invalid projected total.')
        months = dates
        seen.add(code)
        totals.append(dict(icd10_block=code, projected_total=total, forecast_run_id=result['forecast_run_id']))
    totals.sort(key=lambda row: (-row['projected_total'], row['icd10_block']))
    ranked = [dict(rank=n, **row) for n, row in enumerate(totals, 1)]
    return dict(ranking_run_id=secrets.token_hex(16), forecast_run_group_id=group_id,
                dataset_signature=signature, generated_at=now(), ranking_horizon_months=12,
                forecast_months=months or [], rankings=ranked, top_five=ranked[:5] if len(ranked) >= 5 else [],
                top_five_status='available' if len(ranked) >= 5 else 'unavailable',
                is_prototype=context[0] if context else True,
                methodology_status=context[1] if context else 'provisional',
                configuration_signature=context[2] if context else None,
                scope=RANKING_SCOPE,
                warnings=(['Projected Top Five unavailable: fewer than five valid forecasts. The complete available ranking is retained.'] if len(ranked) < 5 else []),
                tie_rule='Equal totals are ordered by ICD-10 block code; this is a display tie-break only.')
