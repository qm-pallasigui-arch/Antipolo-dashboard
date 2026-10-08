"""Mandatory SARIMA+NNAR, rolling diagnostics, holdout evaluation and full refit."""
import numpy as np
import pandas as pd

from dashboard.config import (
    HOLDOUT_MONTHS, FORECAST_MONTHS, SELECTION_FOLDS,
)
from dashboard.logging_config import get_logger
from dashboard.modeling.series_utils import get_disease_series, train_test_split_series
from dashboard.modeling.sarima import run_arima, ModelFailure
from dashboard.modeling.nnar import run_nnar
from dashboard.modeling.metrics import hybrid_forecast
from dashboard.modeling.historical_metrics import compute_metrics

logger = get_logger(__name__)


def _provenance(df, disease):
    rows = df.loc[df.disease == disease]
    result = {}
    for key, default in (("source", "unknown"), ("population", "unknown"),
                         ("case_classification", "unknown"), ("source_dataset", "unspecified upload"), ("coverage_status", "not verified")):
        values = rows[key].fillna(default).astype(str).unique() if key in rows else [default]
        if len(values) != 1:
            raise ModelFailure("invalid_input", f"Mixed {key} values for {disease}; evaluate datasets separately.")
        result[key] = values[0]
    result["dataset_class"] = "synthetic demonstration" if result["source"] == "mock" else "provisional surveillance"
    if result["source"] == "mock":
        result["population"] = "synthetic; no actual population"
        result["case_classification"] = "synthetic"
    elif result["population"] == "all-age":
        result["dataset_class"] = "all-age surveillance; separate evaluation"
    result["research_eligibility"] = "not established; ages 5-19 and confirmed-only verification required"
    return result


def _detect_data_source(df, disease):
    return _provenance(df, disease)["source"]


def _fit_components(series, steps):
    neural = {}
    def validate(fitted, forecast):
        residuals = (series-fitted).dropna()
        nnfit, nnfc, notes = run_nnar(residuals, forecast_steps=steps, forecast_index=forecast.index)
        neural.update(fitted=nnfit, forecast=nnfc, notes=notes, residuals=residuals)
    fitted, forecast, low, high, tier, notes = run_arima(series, forecast_steps=steps, residual_validator=validate)
    return fitted, forecast, tier, notes, neural


def _run_backtest_leg(series: pd.Series, holdout: int) -> dict:
    """Forecast one window and score two thesis candidates plus an internal benchmark."""
    train, test = train_test_split_series(series, holdout=holdout)

    try:
        fitted_tr, fc_test, tier_bt, notes_bt, neural = _fit_components(train, holdout)
    except ModelFailure as exc:
        seasonal = pd.Series(np.resize(train.iloc[-12:].to_numpy(dtype=float), holdout), index=test.index).clip(lower=0)
        exc.diagnostics["holdout_benchmarks"] = {"dates": [str(x) for x in test.index],
            "actual": test.tolist(), "seasonal_naive": seasonal.tolist(),
            "seasonal_naive_metrics": _score_aligned(test, seasonal)}
        base = exc.diagnostics.get("best_sarima_benchmark")
        if base:
            exc.diagnostics["holdout_benchmarks"]["sarima_only_metrics"] = compute_metrics(test, base["forecast"])
        raise
    nnar_resid_test, notes_nnar_bt = neural["forecast"], neural["notes"]

    best_base = fitted_tr.attrs.get("identification", {}).get("best_sarima_benchmark")
    test_sarima_only = pd.Series(best_base["forecast"], index=test.index) if best_base else fc_test.clip(lower=0)
    test_hybrid = hybrid_forecast(fc_test, nnar_resid_test)
    seasonal_values = np.resize(train.iloc[-12:].to_numpy(dtype=float), holdout)
    test_seasonal_naive = pd.Series(seasonal_values, index=test.index).clip(lower=0)

    return {
        "identification": {**fitted_tr.attrs.get("identification", {}), "nnar": nnar_resid_test.attrs.get("nnar", {})},
        "test": test,
        "test_sarima_only": test_sarima_only,
        "test_hybrid": test_hybrid,
        "test_seasonal_naive": test_seasonal_naive,
        "metrics": _score_aligned(test, test_hybrid),
        "sarima_only_metrics": _score_aligned(test, test_sarima_only),
        "seasonal_naive_metrics": _score_aligned(test, test_seasonal_naive),
        "tier": tier_bt,
        "warnings": [f"[backtest SARIMA] {n}" for n in notes_bt] + [f"[backtest NNAR] {n}" for n in notes_nnar_bt],
    }


def _validate_observation_coverage(df: pd.DataFrame, disease: str, required_months: int) -> None:
    rows = df[df["disease"] == disease].copy()
    if rows.empty:
        raise ModelFailure("invalid_input", f"No observations are available for '{disease}'.")
    if "coverage_status" in rows and rows["coverage_status"].eq("incomplete").any():
        raise ModelFailure("invalid_input", "Known incomplete weekly observations cannot support a monthly forecast.")
    counts = pd.to_numeric(rows["cases"], errors="coerce")
    if not np.isfinite(counts).all() or (counts < 0).any() or (counts % 1 != 0).any():
        raise ModelFailure("invalid_input", "Case counts must be finite nonnegative integers.")
    dates = pd.to_datetime(rows["date"], errors="coerce")
    if dates.isna().any() or not dates.dt.is_month_start.all() or dates.duplicated().any():
        raise ModelFailure("invalid_input", "Need unique month-start dates; duplicates cannot be silently summed.")
    observed = pd.PeriodIndex(pd.to_datetime(rows["date"]), freq="M").unique().sort_values()
    expected = pd.period_range(observed.min(), observed.max(), freq="M")
    missing = expected.difference(observed)
    if len(missing):
        raise ModelFailure("invalid_input",
            f"'{disease}' is missing {len(missing)} month(s) inside its observed range. "
            "Forecasting is blocked because missing reports cannot be assumed to mean zero cases."
        )
    if len(observed) < required_months:
        raise ModelFailure("insufficient_data",
            f"'{disease}' has {len(observed)} complete observed months; need at least {required_months} "
            "for rolling model selection plus an untouched holdout."
        )


def _aggregate_fold_metrics(folds: list[dict], prediction_key: str) -> dict:
    for fold in folds:
        if not fold["test"].index.equals(fold[prediction_key].index):
            raise ValueError(f"Forecast dates do not align with actual dates for '{prediction_key}'.")
    actual = np.concatenate([fold["test"].to_numpy(dtype=float) for fold in folds])
    predicted = np.concatenate([fold[prediction_key].to_numpy(dtype=float) for fold in folds])
    return compute_metrics(actual, predicted)


def _selection_score(metrics: dict) -> float:
    """WAPE is the preregistered selection metric; MAE handles all-zero windows."""
    return metrics["wape"] if metrics["wape"] is not None else metrics["mae"]


def _score_aligned(actual: pd.Series, predicted: pd.Series) -> dict:
    """Score only forecasts whose dates exactly match their actual observations."""
    if not actual.index.equals(predicted.index):
        raise ValueError("Forecast dates do not align with actual dates.")
    return compute_metrics(actual.to_numpy(dtype=float), predicted.to_numpy(dtype=float))


def _historical_error_band(final_forecast: pd.Series, errors: np.ndarray) -> tuple[pd.Series, pd.Series, str]:
    """Historical maximum-absolute-error band for the selected forecast path."""
    absolute = np.abs(np.asarray(errors, dtype=float))
    n = len(absolute)
    radius = float(absolute.max())
    lower = (final_forecast - radius).clip(lower=0)
    upper = final_forecast + radius
    method = (
        f"Historical max-absolute-error band ({n} rolling/holdout errors; "
        f"radius {radius:.2f} cases; future coverage not validated)"
    )
    return lower, upper, method


def _run_production_leg(series: pd.Series, forecast_steps: int) -> dict:
    """Refits on the FULL series and forecasts `forecast_steps` real months ahead."""
    fitted_full, fc_future, tier_prod, notes_prod, neural = _fit_components(series, forecast_steps)
    residuals_full = neural["residuals"]
    nnar_fitted_full, nnar_resid_future, notes_nnar_prod = neural["fitted"], neural["forecast"], neural["notes"]
    return {
        "identification": {**fitted_full.attrs.get("identification", {}), "nnar": nnar_resid_future.attrs.get("nnar", {})},
        "raw_sarima_forecast": fc_future,
        "nnar_forecast": nnar_resid_future,
        "fitted": fitted_full,
        "residuals": residuals_full,
        "nnar_fitted": nnar_fitted_full,
        "sarima_forecast": pd.Series(fitted_full.attrs["identification"]["best_sarima_benchmark"]["forecast"], index=fc_future.index)
            if "best_sarima_benchmark" in fitted_full.attrs.get("identification", {}) else fc_future.clip(lower=0),
        "hybrid_forecast": hybrid_forecast(fc_future, nnar_resid_future),
        "tier": tier_prod,
        "warnings": [f"[production SARIMA] {n}" for n in notes_prod] + [f"[production NNAR] {n}" for n in notes_nnar_prod],
    }


def _leg_evidence(leg):
    return {"dates": [str(x) for x in leg["test"].index], "actual": leg["test"].tolist(),
            "hybrid": leg["test_hybrid"].tolist(), "sarima_only": leg["test_sarima_only"].tolist(),
            "seasonal_naive": leg["test_seasonal_naive"].tolist(), "hybrid_metrics": leg["metrics"],
            "sarima_only_metrics": leg["sarima_only_metrics"], "seasonal_naive_metrics": leg["seasonal_naive_metrics"],
            "identification": leg["identification"], "warnings": leg["warnings"]}


def run_hybrid_pipeline(df: pd.DataFrame, disease: str,
                         holdout: int = HOLDOUT_MONTHS,
                         forecast_steps: int = FORECAST_MONTHS,
                         selection_folds: int = SELECTION_FOLDS) -> dict:
    """Evaluate mandatory hybrid on rolling folds and untouched holdout; refit full history."""
    if not isinstance(df, pd.DataFrame) or not {"disease", "date", "cases"}.issubset(df.columns):
        raise ModelFailure("invalid_input", "A dataframe with disease, date and cases is required.")
    if not isinstance(holdout, int) or holdout < 1 or not isinstance(forecast_steps, int) or forecast_steps < 1:
        raise ModelFailure("invalid_input", "Holdout and horizon must be positive integers.")
    if not isinstance(selection_folds, int) or selection_folds < 1:
        raise ModelFailure("invalid_input", "At least one rolling diagnostic fold is required.")
    required_months = 36 + holdout * (selection_folds + 1)
    _validate_observation_coverage(df, disease, required_months)
    series = get_disease_series(df, disease)

    provenance = _provenance(df, disease)
    data_source = provenance["source"]
    pre_evaluation = series.iloc[:-holdout]
    first_fold_end = len(pre_evaluation) - holdout * (selection_folds - 1)
    selection_legs = []
    try:
        for fold in range(selection_folds):
            selection_legs.append(_run_backtest_leg(pre_evaluation.iloc[:first_fold_end + fold * holdout], holdout))
    except ModelFailure as exc:
        exc.diagnostics["completed_rolling_evaluation"] = [_leg_evidence(x) for x in selection_legs]
        exc.diagnostics["provenance"] = provenance
        raise
    selection_metrics = {
        "hybrid": _aggregate_fold_metrics(selection_legs, "test_hybrid"),
        "sarima_only": _aggregate_fold_metrics(selection_legs, "test_sarima_only"),
    }
    selection_metric = "wape" if selection_metrics["sarima_only"]["wape"] is not None else "mae"
    selection_threshold = None  # retained schema field; no benchmark-based gate
    selected_model = "hybrid"

    try:
        evaluation = _run_backtest_leg(series, holdout)
    except ModelFailure as exc:
        exc.diagnostics["completed_rolling_evaluation"] = [_leg_evidence(x) for x in selection_legs]
        exc.diagnostics["provenance"] = provenance
        raise
    logger.info("disease=%s data_source=%s selected_model=%s hybrid_score=%.2f sarima_score=%.2f",
                disease, data_source, selected_model,
                _selection_score(selection_metrics["hybrid"]),
                _selection_score(selection_metrics["sarima_only"]))

    try:
        production = _run_production_leg(series, forecast_steps)
    except ModelFailure as exc:
        exc.diagnostics["completed_rolling_evaluation"] = [_leg_evidence(x) for x in selection_legs]
        exc.diagnostics["completed_holdout_evaluation"] = _leg_evidence(evaluation)
        exc.diagnostics["provenance"] = provenance
        raise

    forecast_by_model = {
        "hybrid": production["hybrid_forecast"],
        "sarima_only": production["sarima_forecast"],
    }
    metrics_by_model = {
        "hybrid": evaluation["metrics"],
        "sarima_only": evaluation["sarima_only_metrics"],
    }
    prediction_key_by_model = {
        "hybrid": "test_hybrid",
        "sarima_only": "test_sarima_only",
    }
    final_forecast = forecast_by_model[selected_model]
    final_metrics = metrics_by_model[selected_model]
    selected_key = prediction_key_by_model[selected_model]
    calibration_errors = np.concatenate([
        *(fold["test"].to_numpy(dtype=float) - fold[selected_key].to_numpy(dtype=float)
          for fold in selection_legs),
        evaluation["test"].to_numpy(dtype=float) - evaluation[selected_key].to_numpy(dtype=float),
    ])
    ci_lower, ci_upper, interval_method = _historical_error_band(final_forecast, calibration_errors)
    warnings_log = []
    for index, fold in enumerate(selection_legs, start=1):
        warnings_log.extend(f"[selection fold {index}] {warning}" for warning in fold["warnings"])
    warnings_log.extend(f"[untouched holdout] {warning}" for warning in evaluation["warnings"])
    warnings_log.extend(production["warnings"])
    if warnings_log:
        logger.warning("disease=%s produced %d model warning(s): %s", disease, len(warnings_log), warnings_log)

    return {
        "rolling_evaluation": [_leg_evidence(x) for x in selection_legs],
        "status": "hybrid_with_warnings" if warnings_log else "hybrid_success",
        "provenance": provenance,
        "model_identification": {"production": production["identification"],
                                 "evaluation": evaluation["identification"],
                                 "folds": [f["identification"] for f in selection_legs]},
        "test_seasonal_naive": evaluation["test_seasonal_naive"],
        "series": series,
        "sarima_fitted": production["fitted"],
        "residuals": production["residuals"],
        "nnar_fitted": production["nnar_fitted"],
        "sarima_forecast": production["sarima_forecast"],
        "raw_sarima_forecast": production["raw_sarima_forecast"],
        "nnar_forecast": production["nnar_forecast"],
        "hybrid_forecast": production["hybrid_forecast"],
        "final_forecast": final_forecast,
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
        "test_actual": evaluation["test"],
        "test_sarima_only": evaluation["test_sarima_only"],
        "test_hybrid": evaluation["test_hybrid"],
        "metrics": evaluation["metrics"],
        "sarima_only_metrics": evaluation["sarima_only_metrics"],
        "final_metrics": final_metrics,
        "baseline_metrics": evaluation["seasonal_naive_metrics"],
        "selection_metrics": selection_metrics,
        "selection_metric": selection_metric,
        "selection_threshold": selection_threshold,
        "selection_tiers": [fold["tier"] for fold in selection_legs],
        "evaluation_tier": evaluation["tier"],
        "selected_model": selected_model,
        "data_source": data_source,
        "model_tier": production["tier"],
        "interval_method": interval_method,
        "evaluation_window": f"{evaluation['test'].index.min():%Y-%m} to {evaluation['test'].index.max():%Y-%m}",
        "selection_folds": selection_folds,
        "warnings_log": warnings_log,
    }
