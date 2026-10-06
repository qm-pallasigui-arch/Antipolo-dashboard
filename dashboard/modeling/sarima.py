"""Training-window-only bounded SARIMA identification; no model-family fallback."""
import warnings
import numpy as np
import pandas as pd
from statsmodels.tsa.statespace.sarimax import SARIMAX
from statsmodels.tsa.seasonal import seasonal_decompose
from statsmodels.tsa.stattools import adfuller, acf, pacf
from statsmodels.stats.diagnostic import acorr_ljungbox
from statsmodels.tools.sm_exceptions import ConvergenceWarning
from dashboard.config import FORECAST_MONTHS
from dashboard.logging_config import get_logger
logger = get_logger(__name__)

class ModelFailure(ValueError):
    """Explicit unavailable state, never a substitute forecast."""
    def __init__(self, status, message, diagnostics=None):
        self.status = status
        self.diagnostics = diagnostics or {}
        super().__init__(f"{status}: {message}")


def _stationarity(values):
    if np.ptp(values) == 0:
        return {"pvalue": None, "d": 0, "reason": "constant series; ADF undefined"}
    try:
        result = adfuller(values, autolag="AIC")
        return {"pvalue": float(result[1]), "d": int(result[1] > .05), "lag": int(result[2])}
    except ValueError as exc:
        raise ModelFailure("invalid_input", f"ADF assessment unavailable: {exc}") from exc


def run_arima(series: pd.Series, forecast_steps: int = FORECAST_MONTHS, residual_validator=None):
    """Fit 12 bounded candidates; choose lowest AIC valid candidate.

    For each D in {0,1}, ADF chooses d in {0,1} on seasonally differenced
    training values. p,q in {(1,0),(0,1),(1,1)}, P,Q in {(1,0),(0,1)}.
    Common likelihood burn=13 makes the scored time span identical. ACF/PACF
    are retained as identification evidence, not interpreted as automatic proof.
    Residual whiteness is a warning, not an exclusion (NNAR models residuals).
    residual_validator may reject a base whose NNAR component cannot fit;
    remaining converged candidates are tried in AIC order.
    """
    if forecast_steps < 1 or not np.isfinite(series.to_numpy(dtype=float)).all():
        raise ModelFailure("invalid_input", "Finite observations and a positive horizon are required.")
    if len(series) < 36:
        raise ModelFailure("insufficient_data", "SARIMA identification needs at least 36 months.")
    report = {"training_start": str(series.index[0]), "training_end": str(series.index[-1]),
              "training_n": len(series), "likelihood_burn": 13, "maxiter": 300,
              "seasonal_period": 12, "stationarity": {}, "correlations": {}, "candidates": []}
    valid = []
    for D in (0, 1):
        seasonal = series.diff(12).dropna() if D else series
        assessment = _stationarity(seasonal.to_numpy(dtype=float))
        report["stationarity"][str(D)] = assessment
        d = assessment["d"]
        transformed = seasonal.diff().dropna() if d else seasonal
        lag = min(12, len(transformed)//2-1)
        if np.ptp(transformed.to_numpy()) > 0:
            report["correlations"][str(D)] = {"acf": acf(transformed, nlags=lag).tolist(),
                "pacf": pacf(transformed, nlags=lag, method="ywm").tolist(), "d": d}
        else:
            report["correlations"][str(D)] = {"reason": "constant transformed series", "d": d}
        for p,q in ((1,0),(0,1),(1,1)):
            for P,Q in ((1,0),(0,1)):
                order, seasonal_order = (p,d,q), (P,D,Q,12)
                record = {"order": list(order), "seasonal_order": list(seasonal_order), "status": "rejected"}
                report["candidates"].append(record)
                try:
                    with warnings.catch_warnings(record=True) as caught:
                        warnings.simplefilter("always")
                        model = SARIMAX(series, order=order, seasonal_order=seasonal_order,
                            trend="c", enforce_stationarity=True, enforce_invertibility=True,
                            loglikelihood_burn=13)
                        fit = model.fit(disp=False, maxiter=300)
                    record["warnings"] = [str(w.message) for w in caught]
                    record["converged"] = bool(fit.mle_retvals.get("converged", False))
                    if not record["converged"] or any(issubclass(w.category, ConvergenceWarning) for w in caught):
                        raise ValueError("optimizer did not converge")
                    if not np.isfinite(fit.aic):
                        raise ValueError("nonfinite AIC")
                    roots = np.r_[fit.arroots, fit.maroots]
                    if len(roots) and (np.abs(roots) <= 1.000001).any():
                        raise ValueError("AR/MA root on or within stability boundary")
                    prediction = fit.get_forecast(steps=forecast_steps)
                    fc = prediction.predicted_mean
                    if not np.isfinite(fc).all():
                        raise ValueError("nonfinite forecast")
                    fitted = fit.fittedvalues.copy()
                    fitted.iloc[:13] = np.nan  # discard state/differencing initialization
                    resid = (series-fitted).dropna()
                    lb = acorr_ljungbox(resid, lags=[12], model_df=p+q+P+Q, return_df=True)
                    prob = float(lb.lb_pvalue.iloc[0])
                    record.update(status="valid", aic=float(fit.aic), ljung_box_lag=12,
                                  ljung_box_pvalue=prob if np.isfinite(prob) else None,
                                  min_root_modulus=float(np.abs(roots).min()) if len(roots) else None)
                    ci = prediction.conf_int()
                    valid.append((float(fit.aic), fitted, fc, ci, record))
                except Exception as exc:
                    record["reason"] = str(exc)
    if not valid:
        raise ModelFailure("sarima_failure", "No valid SARIMA candidate; hybrid unavailable.", report)
    ordered = sorted(valid, key=lambda v:v[0])
    best = ordered[0]
    report["best_sarima_benchmark"] = {"order": best[4]["order"], "seasonal_order": best[4]["seasonal_order"],
        "dates": [str(x) for x in best[2].index], "forecast": best[2].clip(lower=0).tolist()}
    for _, fitted, fc, ci, record in ordered:
        if residual_validator is not None:
            try:
                residual_validator(fitted, fc)
            except Exception as exc:
                record["hybrid_rejection"] = str(exc)
                continue
        report["selected"] = record.copy()
        fitted.attrs["identification"] = report
        tier = f"SARIMA{tuple(record['order'])}{tuple(record['seasonal_order'])}"
        notes = list(record.get("warnings", []))
        if record.get("ljung_box_pvalue") is not None and record["ljung_box_pvalue"] < .05:
            notes.append("Selected SARIMA residuals retain lag-12 autocorrelation (Ljung-Box p<0.05).")
        return fitted, fc, ci.iloc[:,0], ci.iloc[:,1], tier, notes
    raise ModelFailure("nnar_failure", "NNAR failed for every valid SARIMA candidate; hybrid unavailable.", report)


def run_decomposition(series: pd.Series):
    """Classical additive seasonal decomposition (period=12). Needs >= 24 points.
    Returns (result_or_None, reason_or_None) so a genuine fit failure isn't
    mislabeled as "not enough data"."""
    if len(series) < 24:
        return None, f"Only {len(series)} months of history (< 24 required)."
    try:
        return seasonal_decompose(series, model="additive", period=12), None
    except Exception:
        logger.warning("seasonal decomposition failed", exc_info=True)
        return None, "Decomposition failed; the chart is unavailable for this series."
