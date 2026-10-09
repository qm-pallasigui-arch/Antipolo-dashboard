"""Step C (recombination) and backtest scoring."""

import numpy as np
import pandas as pd


def hybrid_forecast(sarima_fc: pd.Series, nnar_resid_fc: pd.Series) -> pd.Series:
    """Step C: SARIMA forecast + NNAR residual forecast, clipped at 0 (cases can't be negative)."""
    if not sarima_fc.index.equals(nnar_resid_fc.index):
        raise ValueError("Hybrid component dates do not align.")
    if not (np.isfinite(sarima_fc).all() and np.isfinite(nnar_resid_fc).all()):
        raise ValueError("Hybrid components must be finite; missing corrections cannot become zero.")
    aligned = nnar_resid_fc
    combined = sarima_fc.values + aligned.values
    return pd.Series(combined, index=sarima_fc.index).clip(lower=0)


def compute_metrics(actual, predicted) -> dict:
    """Error metrics between equal-length finite arrays.

    MAPE uses nonzero actuals only; mape_n records that coverage, and the
    scale of those denominators is reported alongside it. A percentage error is
    only as meaningful as the counts it divides by: where the typical nonzero
    weekly count is small, even a near-perfect model posts a large MAPE, because
    one case is a large fraction of the denominator. The median describes the
    typical denominator and the 10th percentile the seasonal low, so a reader can
    see when MAPE is at risk rather than being handed a bare percentage.
    Values remain unrounded. Missing observations must be excluded by callers.
    """
    actual = np.asarray(actual, dtype=float)
    predicted = np.asarray(predicted, dtype=float)
    if actual.shape != predicted.shape:
        raise ValueError("Actual and predicted values must have identical shapes.")
    if actual.size == 0 or not (np.isfinite(actual).all() and np.isfinite(predicted).all()):
        raise ValueError("Metrics require non-empty, finite actual and predicted values.")

    errors = actual - predicted
    absolute_errors = np.abs(errors)
    rmse = float(np.sqrt(np.mean((actual - predicted) ** 2)))
    mae = float(np.mean(absolute_errors))
    nonzero = actual != 0
    nonzero_actual = actual[nonzero]
    mape = float(np.mean(absolute_errors[nonzero] / np.abs(nonzero_actual)) * 100) if nonzero.any() else None
    return {
        "rmse": rmse,
        "mae": mae,
        "mape": mape,
        "mape_n": int(nonzero.sum()),
        "mape_median_actual": float(np.median(nonzero_actual)) if nonzero.any() else None,
        "mape_p10_actual": float(np.percentile(nonzero_actual, 10)) if nonzero.any() else None,
        "n": int(actual.size),
    }
