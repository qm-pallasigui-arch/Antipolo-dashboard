"""Tests for dashboard.modeling: SARIMA tiering, NNAR, metrics, and the
full hybrid pipeline (including the auto-select safeguard)."""

import numpy as np
import pandas as pd
import pytest

from dashboard.modeling.sarima import run_arima, run_decomposition
from dashboard.modeling.nnar import run_nnar
from dashboard.modeling.metrics import compute_metrics, hybrid_forecast
from dashboard.modeling.pipeline import run_hybrid_pipeline, _score_aligned
from dashboard.modeling.serialization import serialize_pipeline_result, deserialize_pipeline_result
from dashboard.data.mock_data import generate_fallback_data
from dashboard.modeling.sarima import ModelFailure


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
    assert m == {"rmse": 0.0, "mae": 0.0, "mape": 0.0, "wape": 0.0, "mape_n": 3, "n": 3}


def test_compute_metrics_handles_zero_actuals_without_dividing_by_zero():
    # This is exactly the sparse-disease scenario (e.g. Leptospirosis) that
    # produces very high but finite MAPE -- it must not raise or return inf/nan.
    actual = [0, 5, 10]
    predicted = [2, 5, 8]
    m = compute_metrics(actual, predicted)
    assert np.isfinite(m["rmse"])
    assert np.isfinite(m["mae"])
    assert np.isfinite(m["mape"])
    assert m["mape"] == pytest.approx(10.0)
    assert m["mape_n"] == 2
    assert m["wape"] == pytest.approx(26.6666667)


def test_scoring_rejects_same_length_forecast_on_wrong_dates():
    actual = pd.Series([1.0, 2.0], index=pd.date_range("2025-01-01", periods=2, freq="MS"))
    shifted = pd.Series([1.0, 2.0], index=pd.date_range("2025-02-01", periods=2, freq="MS"))
    with pytest.raises(ValueError, match="dates do not align"):
        _score_aligned(actual, shifted)


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


def test_run_arima_short_series_explicit_failure():
    with pytest.raises(ModelFailure, match="insufficient_data"):
        run_arima(_synthetic_series(24), forecast_steps=6)


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

def test_run_nnar_insufficient_residuals_explicit_failure():
    with pytest.raises(ModelFailure, match="nnar_failure"):
        run_nnar(pd.Series(np.arange(5)), n_lags=3, forecast_steps=4)


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
    with pytest.raises(ValueError, match="complete observed months"):
        run_hybrid_pipeline(df, "Dengue")


def test_pipeline_selection_is_rolling_and_final_metrics_use_untouched_holdout():
    df = generate_fallback_data()
    for disease in ["Dengue"]:
        result = run_hybrid_pipeline(df, disease)
        expected = "hybrid"
        assert result["selected_model"] == expected
        expected_metrics = {
            "hybrid": result["metrics"],
            "sarima_only": result["sarima_only_metrics"],
        }[expected]
        assert result["final_metrics"] == expected_metrics
        assert result["selected_model"] in ("hybrid", "sarima_only")
        assert (result["final_forecast"] >= 0).all()
        assert (result["ci_lower"] >= 0).all()
        assert (result["ci_lower"] <= result["final_forecast"]).all()
        assert (result["final_forecast"] <= result["ci_upper"]).all()
        assert len(result["final_forecast"]) == 12
        assert result["selection_folds"] == 2
        assert result["selection_metric"] == "wape"
        assert result["selection_threshold"] is None
        assert len(result["selection_tiers"]) == 2
        assert result["evaluation_tier"]
        assert "Historical max-absolute-error band" in result["interval_method"]
        assert "coverage not validated" in result["interval_method"]


def test_pipeline_rejects_missing_months_instead_of_imputing_zero():
    df = pd.DataFrame({
        "year": [2016, 2025], "month": [1, 12],
        "disease": ["SparseDisease"] * 2, "cases": [10, 20], "source": ["real"] * 2,
    })
    df["date"] = pd.to_datetime(dict(year=df["year"], month=df["month"], day=1))
    with pytest.raises(ValueError, match="missing 118 month"):
        run_hybrid_pipeline(df, "SparseDisease")


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


def test_hybrid_rejects_missing_or_shifted_correction():
    idx = pd.date_range("2025-01-01", periods=2, freq="MS")
    with pytest.raises(ValueError, match="dates"):
        hybrid_forecast(pd.Series([1,2], index=idx), pd.Series([1], index=idx[:1]))
    with pytest.raises(ValueError, match="finite"):
        hybrid_forecast(pd.Series([1,2], index=idx), pd.Series([1,np.nan], index=idx))


def test_pipeline_rejects_mixed_population_and_synthetic():
    df = generate_fallback_data()
    rows = df.disease == "Dengue"
    df.loc[rows, "population"] = "all-age"
    df.loc[df.index[rows][0], "population"] = "ages 5-19"
    with pytest.raises(ModelFailure, match="Mixed population"):
        run_hybrid_pipeline(df, "Dengue")
    df["population"] = "unknown"
    df.loc[df.index[rows][0], "source"] = "real"
    with pytest.raises(ModelFailure, match="Mixed source"):
        run_hybrid_pipeline(df, "Dengue")


def test_pipeline_rejects_duplicate_and_invalid_counts():
    df = generate_fallback_data()
    with pytest.raises(ModelFailure, match="duplicates"):
        run_hybrid_pipeline(pd.concat([df,df.iloc[:1]]), "Dengue")
    df.loc[df.disease == "Dengue", "cases"] = -1
    with pytest.raises(ModelFailure, match="nonnegative"):
        run_hybrid_pipeline(df, "Dengue")


def test_no_valid_sarima_is_explicit(monkeypatch):
    import dashboard.modeling.sarima as module
    def fail(*args, **kwargs):
        raise RuntimeError("forced fitting error")
    monkeypatch.setattr(module, "SARIMAX", fail)
    with pytest.raises(ModelFailure) as caught:
        module.run_arima(_synthetic_series())
    assert caught.value.status == "sarima_failure"
    assert len(caught.value.diagnostics["candidates"]) == 12
    assert all(c["status"] == "rejected" for c in caught.value.diagnostics["candidates"])


def test_mandatory_hybrid_even_when_benchmarks_better_and_holdout_isolated(monkeypatch):
    import dashboard.modeling.pipeline as module
    seen = []
    def fake_fit(series, steps):
        seen.append(series.index[-1])
        idx = pd.date_range(series.index[-1] + pd.offsets.MonthBegin(), periods=steps, freq="MS")
        fitted = series.copy()
        fitted.attrs["identification"] = {"training_end": str(series.index[-1])}
        forecast = pd.Series(10., index=idx)
        return fitted, forecast, "SARIMA test", [], {"fitted":series*0, "forecast":forecast*100,
                                                      "notes":[], "residuals":series*0}
    monkeypatch.setattr(module, "_fit_components", fake_fit)
    df = generate_fallback_data()
    result = module.run_hybrid_pipeline(df,"Dengue")
    assert result["selected_model"] == "hybrid"
    assert result["metrics"]["wape"] > result["sarima_only_metrics"]["wape"]
    assert result["final_forecast"].equals(result["hybrid_forecast"])
    assert [str(x.date()) for x in seen] == ["2022-12-01","2023-12-01","2024-12-01","2025-12-01"]


def test_sarima_retries_other_valid_candidates_after_neural_failure():
    attempts = []
    def reject_first(fitted, forecast):
        attempts.append(forecast)
        if len(attempts) == 1:
            raise ModelFailure("nnar_failure", "forced first component failure")
    fitted, forecast, *_ = run_arima(_synthetic_series(), residual_validator=reject_first)
    assert len(attempts) == 2
    report = fitted.attrs["identification"]
    assert len(report["candidates"]) == 12
    assert any("hybrid_rejection" in c for c in report["candidates"])
    assert report["training_end"].startswith("2025-12")
    assert np.isnan(fitted.iloc[:13]).all()


def test_all_neural_candidates_fail_without_sarima_substitution():
    def reject_all(fitted, forecast):
        raise ModelFailure("nnar_failure", "forced component failure")
    with pytest.raises(ModelFailure) as caught:
        run_arima(_synthetic_series(), residual_validator=reject_all)
    assert caught.value.status == "nnar_failure"
    assert caught.value.diagnostics["best_sarima_benchmark"]["forecast"]
    assert all("hybrid_rejection" in c for c in caught.value.diagnostics["candidates"] if c["status"] == "valid")


def test_zero_denominator_metrics_are_unavailable_not_perfect():
    metrics = compute_metrics([0,0], [1,2])
    assert metrics["mape"] is None and metrics["wape"] is None
    assert metrics["mae"] == 1.5 and metrics["mape_n"] == 0


def test_known_incomplete_weeks_block_monthly_forecast():
    df = generate_fallback_data()
    df["coverage_status"] = "incomplete"
    with pytest.raises(ModelFailure, match="incomplete weekly"):
        run_hybrid_pipeline(df, "Dengue")


def test_invalid_schema_is_typed_failure():
    with pytest.raises(ModelFailure) as caught:
        run_hybrid_pipeline(pd.DataFrame({"cases":[1]}), "Dengue")
    assert caught.value.status == "invalid_input"


def test_production_failure_preserves_completed_benchmarks(monkeypatch):
    import dashboard.modeling.pipeline as module
    def fake_backtest(series, holdout):
        actual=series.iloc[-holdout:]
        metric=compute_metrics(actual,actual)
        return {"test":actual,"test_hybrid":actual,"test_sarima_only":actual,
                "test_seasonal_naive":actual,"metrics":metric,"sarima_only_metrics":metric,
                "seasonal_naive_metrics":metric,"identification":{},"warnings":[],"tier":"test"}
    def fail_production(*args):
        raise ModelFailure("nnar_failure", "forced production failure")
    monkeypatch.setattr(module,"_run_backtest_leg",fake_backtest)
    monkeypatch.setattr(module,"_run_production_leg",fail_production)
    with pytest.raises(ModelFailure) as caught:
        module.run_hybrid_pipeline(generate_fallback_data(),"Dengue")
    assert len(caught.value.diagnostics["completed_rolling_evaluation"])==2
    assert caught.value.diagnostics["completed_holdout_evaluation"]["seasonal_naive_metrics"]["mae"]==0
