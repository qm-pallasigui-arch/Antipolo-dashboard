"""Tests for dashboard.modeling: SARIMA tiering, NNAR, metrics, and the
full hybrid pipeline (including the auto-select safeguard)."""

import numpy as np
import pandas as pd
import pytest

from dashboard.modeling.sarima import run_arima, run_decomposition
from dashboard.modeling.nnar import run_nnar
from dashboard.modeling.metrics import compute_metrics, hybrid_forecast
from dashboard.modeling.pipeline import run_hybrid_pipeline
from dashboard.modeling.serialization import serialize_pipeline_result, deserialize_pipeline_result
from dashboard.data.mock_data import generate_fallback_data
from dashboard.config import DISEASES


def _synthetic_series(n_months=120, seed=0):
    rng = np.random.RandomState(seed)
    idx = pd.date_range("2016-01-01", periods=n_months, freq="MS")
    seasonal = 20 * np.sin(np.arange(n_months) * 2 * np.pi / 12)
    trend = np.linspace(50, 80, n_months)
    noise = rng.normal(0, 3, n_months)
    values = np.clip(trend + seasonal + noise, 0, None)
    return pd.Series(values, index=idx)


# -- compute_metrics --------------------------------------------------------

def test_compute_metrics_perfect_prediction_is_zero_error():
    actual = [10, 20, 30]
    m = compute_metrics(actual, actual)
    assert m == {"rmse": 0.0, "mae": 0.0, "mape": 0.0}


def test_compute_metrics_handles_zero_actuals_without_dividing_by_zero():
    # This is exactly the sparse-disease scenario (e.g. Leptospirosis) that
    # produces very high but finite MAPE -- it must not raise or return inf/nan.
    actual = [0, 5, 10]
    predicted = [2, 5, 8]
    m = compute_metrics(actual, predicted)
    assert np.isfinite(m["rmse"])
    assert np.isfinite(m["mae"])
    assert np.isfinite(m["mape"])


# -- hybrid_forecast ---------------------------------------------------------

def test_hybrid_forecast_clips_negative_combined_values_to_zero():
    idx = pd.date_range("2025-01-01", periods=3, freq="MS")
    sarima_fc = pd.Series([1, 1, 1], index=idx)
    nnar_resid = pd.Series([-5, 0, 5], index=idx)
    result = hybrid_forecast(sarima_fc, nnar_resid)
    assert (result >= 0).all()
    assert result.iloc[0] == 0  # 1 + (-5) clipped to 0
    assert result.iloc[2] == 6  # 1 + 5, no clipping needed


# -- run_arima tiering --------------------------------------------------------

def test_run_arima_uses_sarima_tier_on_well_behaved_series():
    series = _synthetic_series(120)
    fitted, fc_mean, fc_lo, fc_hi, tier, notes = run_arima(series, forecast_steps=12)
    assert tier.startswith("SARIMA")
    assert len(fc_mean) == 12
    assert (fc_lo <= fc_mean).all()
    assert (fc_mean <= fc_hi).all()


def test_run_arima_short_series_skips_straight_to_holt_winters():
    series = _synthetic_series(24)  # < 36 months
    fitted, fc_mean, fc_lo, fc_hi, tier, notes = run_arima(series, forecast_steps=6)
    assert tier == "Holt-Winters (fallback)"
    assert any("skipped SARIMA" in n for n in notes)


def test_run_decomposition_reports_reason_when_too_short():
    series = _synthetic_series(10)
    decomp, reason = run_decomposition(series)
    assert decomp is None
    assert "10 months" in reason


def test_run_decomposition_succeeds_on_long_series():
    series = _synthetic_series(48)
    decomp, reason = run_decomposition(series)
    assert decomp is not None
    assert reason is None


# -- run_nnar -----------------------------------------------------------------

def test_run_nnar_degrades_gracefully_with_too_few_residuals():
    residuals = pd.Series(np.random.randn(5))
    fitted, forecast, notes = run_nnar(residuals, n_lags=3, forecast_steps=4)
    assert len(fitted) == 0
    assert (forecast == 0).all()
    assert any("skipped NNAR" in n for n in notes)


def test_run_nnar_produces_a_forecast_with_enough_residuals():
    residuals = pd.Series(np.random.RandomState(1).randn(60))
    fitted, forecast, notes = run_nnar(residuals, n_lags=3, forecast_steps=12)
    assert len(forecast) == 12
    assert len(fitted) > 0


# -- run_hybrid_pipeline: the auto-select safeguard --------------------------

def test_pipeline_raises_clearly_on_insufficient_history():
    df = pd.DataFrame({
        "year": [2024] * 6, "month": list(range(1, 7)),
        "disease": ["Dengue"] * 6, "cases": [10, 20, 15, 30, 25, 18],
        "source": ["real"] * 6,
    })
    df["date"] = pd.to_datetime(df["year"].astype(str) + "-" + df["month"].astype(str).str.zfill(2) + "-01")
    with pytest.raises(ValueError, match="months of history"):
        run_hybrid_pipeline(df, "Dengue")


def test_pipeline_final_forecast_never_worse_than_either_component_on_backtest():
    """The core safeguard this whole architecture depends on: whichever leg
    the pipeline reports as 'final' must have a backtest MAPE that's <= both
    the hybrid-only and SARIMA-only MAPE (since it IS one of those two)."""
    df = generate_fallback_data()
    for disease in DISEASES:
        result = run_hybrid_pipeline(df, disease)
        best_possible = min(result["metrics"]["mape"], result["sarima_only_metrics"]["mape"])
        assert result["final_metrics"]["mape"] == pytest.approx(best_possible)
        assert result["selected_model"] in ("hybrid", "sarima_only")
        assert (result["final_forecast"] >= 0).all()
        assert len(result["final_forecast"]) == 12


def test_pipeline_data_source_detection():
    df = generate_fallback_data()  # all rows have source == "mock"
    result = run_hybrid_pipeline(df, "Dengue")
    assert result["data_source"] == "mock"

    df.loc[df["disease"] == "Dengue", "source"] = "real"
    result = run_hybrid_pipeline(df, "Dengue")
    assert result["data_source"] == "real"


def test_pipeline_result_survives_serialization_roundtrip():
    df = generate_fallback_data()
    result = run_hybrid_pipeline(df, "Dengue")
    serialized = serialize_pipeline_result(result)
    restored = deserialize_pipeline_result(serialized)

    assert restored["selected_model"] == result["selected_model"]
    assert restored["metrics"] == result["metrics"]
    pd.testing.assert_series_equal(
        restored["final_forecast"].round(6), result["final_forecast"].round(6), check_freq=False
    )
