"""
Step B of the hybrid pipeline: a small MLPRegressor (stand-in for NNAR(p))
trained on lagged SARIMA residuals, to capture whatever non-linear structure
SARIMA left behind.

Note on warning capture: this deliberately records EVERY warning raised
during training (by category name, in `notes`) rather than filtering for a
specific warning class. An earlier version of this code imported sklearn's
ConvergenceWarning specifically to filter on, then never actually used it --
dead code, since "catch everything and label it" is both simpler and more
complete (it also surfaces warning types nobody anticipated). That import has
been removed here rather than carried forward.
"""

import warnings

import numpy as np
import pandas as pd
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler

from dashboard.config import NNAR_LAGS, NNAR_HIDDEN, NNAR_ALPHA, FORECAST_MONTHS


def run_nnar(residuals: pd.Series, n_lags: int = NNAR_LAGS,
             forecast_steps: int = FORECAST_MONTHS, forecast_index=None):
    """
    Trains a small MLPRegressor on lagged SARIMA residuals, then recursively
    forecasts `forecast_steps` residuals ahead (each prediction is fed back
    in as the newest lag).

    Returns (in_sample_fitted_residuals, forecast_residuals, notes). If there
    isn't enough residual history to train reliably, returns an empty fitted
    series and an all-zero forecast (i.e. the hybrid model degrades
    gracefully to SARIMA-only) -- and says so in `notes` rather than silently.
    """
    notes = []
    resid = residuals.dropna()
    idx = forecast_index if forecast_index is not None else pd.RangeIndex(forecast_steps)

    if len(resid) <= n_lags + 5:
        notes.append(f"Only {len(resid)} residual points available (need > {n_lags + 5}); "
                    f"skipped NNAR training, hybrid degrades to SARIMA-only for this leg.")
        return pd.Series(dtype=float), pd.Series(np.zeros(forecast_steps), index=idx), notes

    vals = resid.values
    X, y = [], []
    for i in range(n_lags, len(vals)):
        X.append(vals[i - n_lags:i])
        y.append(vals[i])
    X, y = np.array(X), np.array(y)

    scaler = StandardScaler().fit(X)
    Xs = scaler.transform(X)

    nn = MLPRegressor(
        hidden_layer_sizes=NNAR_HIDDEN, activation="relu", solver="lbfgs",
        max_iter=2000, random_state=42, alpha=NNAR_ALPHA,
    )
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        nn.fit(Xs, y)
    for w in caught:
        notes.append(f"NNAR training: {w.category.__name__}: {str(w.message)[:120]}")

    fitted_vals = nn.predict(Xs)
    fitted_series = pd.Series(fitted_vals, index=resid.index[n_lags:])

    history = list(vals[-n_lags:])
    preds = []
    for _ in range(forecast_steps):
        x = scaler.transform([history[-n_lags:]])
        p = float(nn.predict(x)[0])
        preds.append(p)
        history.append(p)

    forecast_series = pd.Series(preds, index=idx)
    return fitted_series, forecast_series, notes
