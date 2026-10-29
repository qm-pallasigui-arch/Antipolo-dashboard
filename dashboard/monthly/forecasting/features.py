"""Validate chronological error provenance before residual feature creation."""
from datetime import date
import numpy as np
import pandas as pd
from .adapter import observed_frame
from .errors import ForecastComponentError


def generate_residual_training_data(frame, fitted, config):
    """Provisional in-sample residuals, with lags measured in calendar months."""
    observed = observed_frame(frame).set_index('actual_timestamp')
    residuals = observed.consultation_count.astype(float) - fitted.reindex(observed.index)
    if not np.isfinite(residuals.to_numpy()).all():
        raise ForecastComponentError('xgboost_failed', 'Residual alignment produced nonfinite values.')
    features, targets = [], []
    for timestamp, target in residuals.items():
        if timestamp < residuals.index.min() + pd.DateOffset(months=config.lags):
            continue
        lagged = lag_features(residuals, timestamp, config.lags)
        if np.isnan(lagged).all():
            continue
        features.append(lagged)
        targets.append(float(target))
    if len(targets) < config.min_residual_rows:
        raise ForecastComponentError('xgboost_insufficient_history',
            f'Only {len(targets)} usable calendar-lag residual rows; provisional minimum is {config.min_residual_rows}.')
    return np.asarray(features), np.asarray(targets), residuals


def lag_features(history, timestamp, lags):
    # Unknown calendar months are NaN for XGBoost's native missing-value handling.
    # They are never moved, interpolated, zero-filled or added to canonical data.
    return np.asarray([history.get(timestamp - pd.DateOffset(months=n), np.nan) for n in range(1, lags + 1)], dtype=float)


def validate_error_rows(rows):
    seen = set()
    for row in rows:
        origin = date.fromisoformat(row['training_cutoff'])
        target = date.fromisoformat(row['target_month'])
        if origin >= target:
            raise ValueError('Residual targets must occur after the training cutoff.')
        key = (origin, target)
        if key in seen:
            raise ValueError('Duplicate chronological error record.')
        seen.add(key)
    if not seen:
        raise ValueError('Chronological forecast errors are required.')
    return rows
