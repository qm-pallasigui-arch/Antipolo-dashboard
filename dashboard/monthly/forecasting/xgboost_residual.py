"""Residual correction only. Failures propagate; no base-model fallback."""
import numpy as np
import pandas as pd
from .features import lag_features
from .errors import ForecastComponentError


def fit_xgboost_residual_model(features, targets, config):
    try:
        from xgboost import XGBRegressor
        from threadpoolctl import threadpool_limits
        with threadpool_limits(limits=config.threads):
            model = XGBRegressor(**config.xgboost, random_state=config.seed, n_jobs=config.threads)
            model.fit(features, targets)
        return model
    except Exception as exc:
        raise ForecastComponentError('xgboost_failed', 'XGBoost residual fitting failed.') from exc


def predict_residuals(model, residuals, dates, config):
    try:
        history = residuals.to_dict()
        requested = pd.DatetimeIndex(pd.to_datetime(dates))
        if requested.min() <= residuals.index.max():
            raise ValueError('Residual forecasts must be after the last observed training month.')
        # Bridge trailing gaps as predictions only, never as observed history.
        calendar = pd.date_range(residuals.index.max() + pd.offsets.MonthBegin(), requested.max(), freq='MS')
        for timestamp in calendar:
            features = lag_features(history, timestamp, config.lags).reshape(1, -1)
            prediction = float(model.predict(features)[0])
            if not np.isfinite(prediction):
                raise ValueError('Nonfinite residual prediction.')
            history[timestamp] = prediction
        return np.asarray([history[t] for t in requested])
    except Exception as exc:
        raise ForecastComponentError('xgboost_failed', 'XGBoost residual prediction failed; no base-only fallback was used.') from exc


def fit_predict(training_features, chronological_errors, future_features, parameters, *, seed, threads):
    from xgboost import XGBRegressor
    if isinstance(threads, bool) or not isinstance(threads, int) or threads < 1 or isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError('An explicit seed and positive CPU thread limit are required.')
    if 'random_state' in parameters or 'n_jobs' in parameters:
        raise ValueError('Supply seed and threads through their dedicated parameters.')
    model = XGBRegressor(**parameters, random_state=seed, n_jobs=threads)
    model.fit(training_features, chronological_errors)
    return model.predict(future_features).tolist()
