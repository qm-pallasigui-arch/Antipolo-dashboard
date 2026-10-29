"""Metric utilities; the evaluation split and scaling remain methodology decisions."""
import math
import pandas as pd
from .adapter import observed_frame
from .errors import ForecastComponentError


def metrics(actual, predicted, *, mase_scale=None):
    if len(actual) == 0 or len(actual) != len(predicted):
        raise ValueError('Evaluation requires matched nonempty observations.')
    errors = [a - p for a, p in zip(actual, predicted)]
    if not all(math.isfinite(e) for e in errors):
        raise ValueError('Evaluation values must be finite.')
    mae = sum(abs(e) for e in errors) / len(errors)
    return dict(mae=mae, rmse=math.sqrt(sum(e * e for e in errors) / len(errors)),
                mase=mae / mase_scale if mase_scale is not None and math.isfinite(mase_scale) and mase_scale > 0 else None)


def build_chronological_split(series, methodology_config):
    if methodology_config.evaluation_split != 'last_reported_year':
        raise ValueError('Unsupported evaluation split.')
    observed = observed_frame(series)
    if observed.empty:
        raise ForecastComponentError('xgboost_insufficient_history', 'No observations for evaluation.')
    test_year = int(observed.year.max())
    train = series.loc[series.year < test_year].copy()
    test = observed.loc[observed.year == test_year].copy()
    if len(observed_frame(train)) < methodology_config.min_observations:
        raise ForecastComponentError('xgboost_insufficient_history', 'Insufficient pre-test history for provisional evaluation.')
    return train, test


def training_mase_scale(train, season_months):
    values = observed_frame(train).set_index('actual_timestamp').consultation_count.astype(float)
    differences = [abs(v - values.loc[previous]) for timestamp, v in values.items()
                   if (previous := timestamp - pd.DateOffset(months=season_months)) in values.index]
    scale = sum(differences) / len(differences) if differences else None
    return scale if scale is not None and scale > 0 else None


def evaluate_prototype(frame, config, forecast_components):
    """Hold out the last reported year generically; never use its values in fitting/scaling."""
    try:
        train, test = build_chronological_split(frame, config)
        output = forecast_components(train, list(test.actual_timestamp), config)
        scale = training_mase_scale(train, config.mase_season_months)
        actual = test.consultation_count.tolist()
        base = metrics(actual, output['baseline'], mase_scale=scale)
        hybrid = metrics(actual, output['hybrid'], mase_scale=scale)
        train_dates = observed_frame(train).actual_timestamp
        notes = ['Prototype comparison only. MASE uses training-only pairs at the configured calendar-month season; undefined scale yields null.']
        if config.prophet.get('yearly_seasonality') and train_dates.max() < train_dates.min() + pd.DateOffset(years=2):
            notes.append('Yearly seasonality was fitted with less than two years of calendar span; the decomposition may be unstable.')
        return dict(status='completed', is_prototype=True, methodology_status='provisional',
            split=config.evaluation_split, residual_method=config.residual_method,
            train_end=observed_frame(train).actual_timestamp.max().strftime('%Y-%m-%d'),
            test_months=[t.strftime('%Y-%m') for t in test.actual_timestamp], actual=actual,
            prophet_predictions=output['baseline'], hybrid_predictions=output['hybrid'],
            prophet=base, hybrid=hybrid, mae_improvement=base['mae'] - hybrid['mae'], mase_scale=scale,
            notes=notes)
    except ForecastComponentError as exc:
        return dict(status='unavailable', component_status=exc.status, reason=str(exc),
                    is_prototype=True, methodology_status='provisional')
