"""
The master per-disease pipeline: backtest leg -> model-selection safeguard ->
production leg -> packaged result.

The original `run_hybrid_pipeline` was a single 76-line function (radon
cyclomatic complexity 11, grade C) that inlined both the backtest leg and the
production leg. Splitting them into `_run_backtest_leg` and
`_run_production_leg` means each one can be read (and tested) as "fit SARIMA,
extract residuals, fit NNAR, combine" without the other leg's code in the way,
and `run_hybrid_pipeline` itself is now just the orchestration: call backtest,
decide which model wins, call production, assemble the result.
"""

import pandas as pd

from dashboard.config import HOLDOUT_MONTHS, FORECAST_MONTHS
from dashboard.logging_config import get_logger
from dashboard.modeling.series_utils import get_disease_series, train_test_split_series
from dashboard.modeling.sarima import run_arima
from dashboard.modeling.nnar import run_nnar
from dashboard.modeling.metrics import hybrid_forecast, compute_metrics

logger = get_logger(__name__)


def _detect_data_source(df: pd.DataFrame, disease: str) -> str:
    """'real' if any row for this disease came from an upload, else 'mock'."""
    disease_rows = df[df["disease"] == disease]
    has_real = "source" in disease_rows.columns and (disease_rows["source"] == "real").any()
    return "real" if has_real else "mock"


def _run_backtest_leg(series: pd.Series, holdout: int) -> dict:
    """Fits on all-but-last-`holdout` months, forecasts the held-out months,
    and scores SARIMA-only vs. hybrid against the actuals."""
    train, test = train_test_split_series(series, holdout=holdout)

    fitted_tr, fc_test, _, _, tier_bt, notes_bt = run_arima(train, forecast_steps=holdout)
    residuals_tr = (train - fitted_tr).dropna()
    _, nnar_resid_test, notes_nnar_bt = run_nnar(residuals_tr, forecast_steps=holdout, forecast_index=fc_test.index)

    test_sarima_only = fc_test.clip(lower=0)
    test_hybrid = hybrid_forecast(fc_test, nnar_resid_test)

    return {
        "test": test,
        "test_sarima_only": test_sarima_only,
        "test_hybrid": test_hybrid,
        "metrics": compute_metrics(test.values, test_hybrid.values),
        "sarima_only_metrics": compute_metrics(test.values, test_sarima_only.values),
        "tier": tier_bt,
        "warnings": [f"[backtest SARIMA] {n}" for n in notes_bt] + [f"[backtest NNAR] {n}" for n in notes_nnar_bt],
    }


def _run_production_leg(series: pd.Series, forecast_steps: int) -> dict:
    """Refits on the FULL series and forecasts `forecast_steps` real months ahead."""
    fitted_full, fc_future, ci_lo, ci_hi, tier_prod, notes_prod = run_arima(series, forecast_steps=forecast_steps)
    residuals_full = (series - fitted_full).dropna()
    nnar_fitted_full, nnar_resid_future, notes_nnar_prod = run_nnar(
        residuals_full, forecast_steps=forecast_steps, forecast_index=fc_future.index
    )

    return {
        "fitted": fitted_full,
        "residuals": residuals_full,
        "nnar_fitted": nnar_fitted_full,
        "sarima_forecast": fc_future.clip(lower=0),
        "hybrid_forecast": hybrid_forecast(fc_future, nnar_resid_future),
        "ci_lower": ci_lo,
        "ci_upper": ci_hi,
        "tier": tier_prod,
        "warnings": [f"[production SARIMA] {n}" for n in notes_prod] + [f"[production NNAR] {n}" for n in notes_nnar_prod],
    }


def run_hybrid_pipeline(df: pd.DataFrame, disease: str,
                         holdout: int = HOLDOUT_MONTHS,
                         forecast_steps: int = FORECAST_MONTHS) -> dict:
    """
    Runs the full hybrid SARIMA+NNAR pipeline for one disease:
      1. Backtest leg -> RMSE/MAE/MAPE for SARIMA-only and hybrid.
      2. Safeguard: select whichever leg actually won the backtest.
      3. Production leg: refit on everything, forecast the real future.
    The safeguard guarantees the delivered forecast is never worse than
    SARIMA-only on held-out data (SARIMA residuals are frequently close to
    white noise, in which case the NNAR has nothing real to learn and can
    hurt accuracy -- see the note in dashboard/config.py near NNAR_LAGS).
    """
    series = get_disease_series(df, disease)
    if len(series) < holdout + 36:
        raise ValueError(
            f"'{disease}' has only {len(series)} months of history; "
            f"need >= {holdout + 36} for a reliable SARIMA+NNAR backtest."
        )

    data_source = _detect_data_source(df, disease)
    backtest = _run_backtest_leg(series, holdout)

    selected_model = "hybrid" if backtest["metrics"]["mape"] < backtest["sarima_only_metrics"]["mape"] else "sarima_only"
    logger.info("disease=%s data_source=%s selected_model=%s hybrid_mape=%.2f sarima_mape=%.2f",
                disease, data_source, selected_model,
                backtest["metrics"]["mape"], backtest["sarima_only_metrics"]["mape"])

    production = _run_production_leg(series, forecast_steps)

    final_forecast = production["hybrid_forecast"] if selected_model == "hybrid" else production["sarima_forecast"]
    final_metrics = backtest["metrics"] if selected_model == "hybrid" else backtest["sarima_only_metrics"]
    warnings_log = backtest["warnings"] + production["warnings"]
    if warnings_log:
        logger.warning("disease=%s produced %d model warning(s): %s", disease, len(warnings_log), warnings_log)

    return {
        "series": series,
        "sarima_fitted": production["fitted"],
        "residuals": production["residuals"],
        "nnar_fitted": production["nnar_fitted"],
        "sarima_forecast": production["sarima_forecast"],
        "hybrid_forecast": production["hybrid_forecast"],
        "final_forecast": final_forecast,
        "ci_lower": production["ci_lower"],
        "ci_upper": production["ci_upper"],
        "test_actual": backtest["test"],
        "test_sarima_only": backtest["test_sarima_only"],
        "test_hybrid": backtest["test_hybrid"],
        "metrics": backtest["metrics"],
        "sarima_only_metrics": backtest["sarima_only_metrics"],
        "final_metrics": final_metrics,
        "selected_model": selected_model,
        "data_source": data_source,
        "model_tier": production["tier"],
        "warnings_log": warnings_log,
    }
