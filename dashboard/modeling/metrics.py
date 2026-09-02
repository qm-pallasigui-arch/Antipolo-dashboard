"""Step C (recombination) and backtest scoring."""

import numpy as np
import pandas as pd


def hybrid_forecast(sarima_fc: pd.Series, nnar_resid_fc: pd.Series) -> pd.Series:
    """Step C: SARIMA forecast + NNAR residual forecast, clipped at 0 (cases can't be negative)."""
    aligned = nnar_resid_fc.reindex(sarima_fc.index).fillna(0)
    combined = sarima_fc.values + aligned.values
    return pd.Series(combined, index=sarima_fc.index).clip(lower=0)


def compute_metrics(actual, predicted) -> dict:
    """RMSE, MAE, MAPE (%) between two equal-length arrays/series."""
    actual = np.asarray(actual, dtype=float)
    predicted = np.asarray(predicted, dtype=float)
    rmse = float(np.sqrt(np.mean((actual - predicted) ** 2)))
    mae = float(np.mean(np.abs(actual - predicted)))
    denom = np.where(actual == 0, 1, actual)  # avoid div-by-zero on zero-case months
    mape = float(np.mean(np.abs((actual - predicted) / denom)) * 100)
    return {"rmse": round(rmse, 2), "mae": round(mae, 2), "mape": round(mape, 2)}
