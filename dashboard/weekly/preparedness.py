"""Deterministic descriptive summaries, without epidemiological thresholds."""
import numpy as np

LABEL = 'Forecast-based preparedness interpretation — not an outbreak declaration.'


def summarize(result, reference_values):
    model = 'hybrid' if result.get('hybrid') else 'sarima' if result.get('sarima') else None
    if model is None:
        return {'status': 'Unavailable: no valid future forecast.', 'label': LABEL}
    values = np.asarray(result[model], dtype=float)
    # Fixed recent window: missing positions remain missing, never backfilled.
    recent = np.asarray(reference_values[-13:], dtype=float)
    usable = recent[np.isfinite(recent)]
    reference = float(usable.mean()) if usable.size else None
    windows = {}
    for horizon in (4, 13, 26, 52):
        path = values[:horizon]
        mean = float(path.mean())
        change = mean - reference if reference is not None else None
        direction = ('unavailable' if change is None else 'increase' if change > 1e-9
                     else 'decrease' if change < -1e-9 else 'stable')
        windows[str(horizon)] = {'weeks': len(path), 'mean_forecast': mean, 'direction': direction,
                                  'change_from_reference': change,
                                  'percent_change': 100 * change / reference if reference else None,
                                  'interpretation': f'Next {horizon} weeks: projected {direction} relative to the recent historical mean.'}
    elevated = values > reference if reference is not None else np.zeros(len(values), dtype=bool)
    longest = current = 0
    for above in elevated:
        current = current + 1 if above else 0
        longest = max(longest, current)
    peak = int(np.argmax(values))
    point = result['forecast_index'][peak]
    week = (f"{point['year']} morbidity week {point['morbidity_week']}" if point.get('year')
            else f"forecast week +{point['horizon_week']}")
    model_label = 'Hybrid SARIMA–NNAR' if model == 'hybrid' else 'SARIMA-only'
    text = (f"{model_label}: {windows['4']['interpretation']} {windows['13']['interpretation']} "
            f"The 26-week and 52-week projected means indicate {windows['26']['direction']} and "
            f"{windows['52']['direction']}, respectively. The maximum forecast is {values[peak]:.1f} cases "
            f"around {week}.")
    if reference is not None:
        text += (f' The recent historical mean is {reference:.1f} cases across {len(usable)} reported '
                 f'positions in the last 13 weeks. {int(elevated.sum())} projected weeks exceed that mean; '
                 f'the longest consecutive run is {longest} weeks.')
        text += (' This pattern may support increased surveillance attention and a review of resource readiness.'
                 if longest else ' Continue monitoring current reports and reviewing preparedness.')
    else:
        text += ' A recent historical reference is unavailable; no relative activity comparison is made.'
    if result.get('context') == 'Synthetic / Demo Data':
        text = 'Demo projection. ' + text
    return {'status': 'Available', 'label': LABEL, 'model': model, 'windows': windows,
            'trend_direction': windows['13']['direction'], 'peak_week': point,
            'peak_forecast_count': float(values[peak]), 'recent_reference_mean': reference,
            'reference_positions': len(recent), 'reference_observations': len(usable),
            'reference_method': 'Mean of finite eligible counts in the last 13 chronological positions.',
            'direction_method': 'Horizon mean compared with recent reference (absolute tolerance 1e-9).',
            'elevated_weeks': int(elevated.sum()), 'longest_elevated_run': longest, 'text': text}
