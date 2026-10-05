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

    MAPE is defined only for months whose actual count is non-zero; ``mape_n``
    makes that denominator coverage explicit. WAPE remains defined for sparse
    series whenever the total actual count is non-zero. Values stay unrounded
    here so model selection never depends on display precision.
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
    mape = float(np.mean(absolute_errors[nonzero] / np.abs(actual[nonzero])) * 100) if nonzero.any() else None
    actual_total = float(np.abs(actual).sum())
    wape = float(absolute_errors.sum() / actual_total * 100) if actual_total else None
    return {
        "rmse": rmse,
        "mae": mae,
        "mape": mape,
        "wape": wape,
        "mape_n": int(nonzero.sum()),
        "n": int(actual.size),
    }
