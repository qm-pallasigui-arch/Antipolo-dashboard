"""
Step A of the hybrid pipeline: SARIMA captures the linear/seasonal signal,
with a tiered fallback (SARIMA -> Holt-Winters -> naive drift) that stays
visible instead of silently swallowing convergence failures.
"""

import warnings

import pandas as pd
from statsmodels.tsa.statespace.sarimax import SARIMAX
from statsmodels.tsa.seasonal import seasonal_decompose
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from statsmodels.tools.sm_exceptions import ConvergenceWarning

from dashboard.config import FORECAST_MONTHS


def run_arima(series: pd.Series, forecast_steps: int = FORECAST_MONTHS):
    """
    Tiered model selection:
      >= 36 months: SARIMA(1,1,1)(0,1,1)[12] -- captures the annual cycle.
      <  36 months: falls straight to Holt-Winters.
    Falls back a tier if fitting fails; last resort is a naive drift forecast.
    Returns (fitted_in_sample, forecast_mean, forecast_ci_lower, forecast_ci_upper,
             model_tier, notes) -- model_tier and notes make the fallback chain
    visible instead of silently swallowing convergence failures.
    """
    notes = []

    def _fit_and_forecast(order, seasonal_order):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            m = SARIMAX(
                series, order=order, seasonal_order=seasonal_order,
                trend="c", enforce_stationarity=False, enforce_invertibility=False,
            )
            r = m.fit(disp=False, maxiter=300)
        conv_issues = [w for w in caught if issubclass(w.category, ConvergenceWarning)]
        if conv_issues:
            raise RuntimeError(f"did not converge cleanly ({str(conv_issues[0].message)[:120]})")
        pred = r.get_forecast(steps=forecast_steps)
        fc_mean = pred.predicted_mean
        fc_ci = pred.conf_int(alpha=0.05)
        cols = fc_ci.columns.tolist()
        return r.fittedvalues, fc_mean, fc_ci[cols[0]], fc_ci[cols[1]]

    if len(series) >= 36:
        try:
            fitted, fc_mean, fc_lo, fc_hi = _fit_and_forecast((1, 1, 1), (0, 1, 1, 12))
            return fitted, fc_mean, fc_lo, fc_hi, "SARIMA(1,1,1)(0,1,1)[12]", notes
        except Exception as e:
            notes.append(f"SARIMA(1,1,1)(0,1,1)[12] {e}; fell back to Holt-Winters.")
    else:
        notes.append(f"Only {len(series)} months of history (<36); skipped SARIMA, used Holt-Winters directly.")

    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            hw = ExponentialSmoothing(
                series, trend="add", seasonal="add", seasonal_periods=12
            ).fit(optimized=True)
        for w in caught:
            notes.append(f"Holt-Winters: {w.category.__name__}: {str(w.message)[:120]}")
        fitted_hw = hw.fittedvalues
        fc_hw = hw.forecast(forecast_steps)
        resid_std = (series - fitted_hw).std()
        steps = pd.Series(range(1, forecast_steps + 1))
        margin = 1.96 * resid_std * steps.apply(lambda k: k ** 0.5).values
        fc_lower = pd.Series((fc_hw.values - margin).clip(min=0), index=fc_hw.index)
        fc_upper = pd.Series(fc_hw.values + margin, index=fc_hw.index)
        return fitted_hw, fc_hw, fc_lower, fc_upper, "Holt-Winters (fallback)", notes
    except Exception as e:
        notes.append(f"Holt-Winters also failed ({type(e).__name__}: {e}); fell back to naive drift (least reliable tier).")

    last_val = series.iloc[-1]
    drift = (series.iloc[-1] - series.iloc[0]) / len(series)
    std = series.std()
    idx = pd.date_range(series.index[-1] + pd.DateOffset(months=1), periods=forecast_steps, freq="MS")
    fc_mean = pd.Series([max(last_val + drift * i, 0) for i in range(1, forecast_steps + 1)], index=idx)
    fc_lower = (fc_mean - 1.96 * std).clip(lower=0)
    fc_upper = fc_mean + 1.96 * std
    return series, fc_mean, fc_lower, fc_upper, "Naive drift (last resort)", notes


def run_decomposition(series: pd.Series):
    """Classical additive seasonal decomposition (period=12). Needs >= 24 points.
    Returns (result_or_None, reason_or_None) so a genuine fit failure isn't
    mislabeled as "not enough data"."""
    if len(series) < 24:
        return None, f"Only {len(series)} months of history (< 24 required)."
    try:
        return seasonal_decompose(series, model="additive", period=12), None
    except Exception as e:
        return None, f"Decomposition failed: {type(e).__name__}: {e}"
