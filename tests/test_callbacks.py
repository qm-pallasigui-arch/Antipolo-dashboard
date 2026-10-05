"""Behavioral regression tests for the callback layer."""

import pandas as pd
import pytest
from dash import html
from dash.exceptions import PreventUpdate

from dashboard.callbacks import view_callbacks
from dashboard.callbacks.view_callbacks import (
    CACHE_SIGNATURE_KEY,
    _build_forecast_export,
    _build_hybrid_metric_cards,
    _build_model_diagnostics,
    _build_source_indicators,
    _data_signature,
    _get_or_compute_disease,
    _prepare_hybrid_entry,
    download_forecast_csv,
    render_hybrid_section,
    update_disease_controls,
    update_forecast_download_state,
    update_hybrid_dropdown_status,
    update_year_control,
)
from dashboard.data.mock_data import generate_fallback_data
from dashboard.modeling.serialization import serialize_pipeline_result
from dashboard.charts.figures import fig_backtest, fig_disease_bar, fig_donut, fig_hybrid_forecast


def _store(df=None):
    frame = generate_fallback_data() if df is None else df
    return frame.to_json(date_format="iso", orient="split")


def _result(data_source="real"):
    history_index = pd.date_range("2023-01-01", periods=24, freq="MS")
    future_index = pd.date_range("2025-01-01", periods=2, freq="MS")
    backtest_index = history_index[-2:]
    history = pd.Series(range(24), index=history_index, dtype=float)
    future = pd.Series([25.0, 26.0], index=future_index)
    return {
        "series": history,
        "sarima_fitted": history,
        "residuals": history * 0,
        "nnar_fitted": history * 0,
        "sarima_forecast": future - 1,
        "hybrid_forecast": future,
        "final_forecast": future,
        "ci_lower": future - 2,
        "ci_upper": future + 2,
        "test_actual": history[-2:],
        "test_sarima_only": pd.Series([21.0, 22.0], index=backtest_index),
        "test_hybrid": pd.Series([21.5, 22.5], index=backtest_index),
        "metrics": {"rmse": 1.0, "mae": 1.0, "mape": 5.0, "wape": 4.0, "mape_n": 2, "n": 2},
        "sarima_only_metrics": {"rmse": 2.0, "mae": 2.0, "mape": 8.0, "wape": 7.0, "mape_n": 2, "n": 2},
        "final_metrics": {"rmse": 1.0, "mae": 1.0, "mape": 5.0, "wape": 4.0, "mape_n": 2, "n": 2},
        "baseline_metrics": {"rmse": 3.0, "mae": 3.0, "mape": 10.0, "wape": 9.0, "mape_n": 2, "n": 2},
        "selection_metrics": {
            "hybrid": {"rmse": 1.0, "mae": 1.0, "mape": 5.0, "wape": 4.0, "mape_n": 4, "n": 4},
            "sarima_only": {"rmse": 2.0, "mae": 2.0, "mape": 8.0, "wape": 7.0, "mape_n": 4, "n": 4},
        },
        "selected_model": "hybrid",
        "data_source": data_source,
        "model_tier": "SARIMA(1,1,1)(0,1,1)[12]",
        "evaluation_tier": "SARIMA(1,1,1)(0,1,1)[12]",
        "selection_tiers": ["SARIMA(1,1,1)(0,1,1)[12]"] * 2,
        "selection_metric": "wape",
        "selection_threshold": 1.0,
        "interval_method": "Historical max-absolute-error band (test; future coverage not validated)",
        "evaluation_window": "2024-11 to 2024-12",
        "selection_folds": 2,
        "warnings_log": [],
    }


def test_prepare_hybrid_entry_computes_only_selected_disease(monkeypatch):
    calls = []

    def fake_compute(cache, df, disease):
        calls.append(disease)
        cache[disease] = {"selected": disease}
        return cache[disease]

    monkeypatch.setattr(view_callbacks, "_get_or_compute_disease", fake_compute)
    store = _store()
    cache, entry, error = _prepare_hybrid_entry(store, "Dengue", {})

    assert error is None
    assert calls == ["Dengue"]
    assert set(cache) == {CACHE_SIGNATURE_KEY, "Dengue"}
    assert entry == {"selected": "Dengue"}


def test_prepare_hybrid_entry_reuses_matching_cache(monkeypatch):
    store = _store()
    cached = {CACHE_SIGNATURE_KEY: _data_signature(store), "Dengue": {"cached": True}}
    monkeypatch.setattr(
        view_callbacks,
        "_get_or_compute_disease",
        lambda *args: pytest.fail("cached disease should not be recomputed"),
    )

    returned, entry, error = _prepare_hybrid_entry(store, "Dengue", cached)

    assert returned is cached
    assert entry == {"cached": True}
    assert error is None


def test_prepare_hybrid_entry_invalidates_old_dataset_cache(monkeypatch):
    store = _store()

    def fake_compute(cache, df, disease):
        cache[disease] = {"fresh": True}

    monkeypatch.setattr(view_callbacks, "_get_or_compute_disease", fake_compute)
    returned, entry, error = _prepare_hybrid_entry(
        store,
        "Dengue",
        {CACHE_SIGNATURE_KEY: "old", "Measles-Rubella": {"stale": True}},
    )

    assert error is None
    assert "Measles-Rubella" not in returned
    assert returned[CACHE_SIGNATURE_KEY] == _data_signature(store)
    assert entry == {"fresh": True}


def test_pipeline_failure_is_cached_as_safe_error(monkeypatch):
    monkeypatch.setattr(
        view_callbacks,
        "run_hybrid_pipeline",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("secret traceback detail")),
    )
    cache = {}
    entry = _get_or_compute_disease(cache, generate_fallback_data(), "Dengue")

    assert entry == {"error": "The forecast could not be computed for this disease."}
    assert "secret" not in entry["error"]


def test_pipeline_validation_rejection_is_visible_to_user():
    frame = pd.DataFrame({
        "year": [2016, 2025], "month": [1, 12],
        "disease": ["SparseDisease"] * 2, "cases": [10, 20], "source": ["real"] * 2,
    })
    frame["date"] = pd.to_datetime(dict(year=frame["year"], month=frame["month"], day=1))
    entry = _get_or_compute_disease({}, frame, "SparseDisease")

    assert "missing 118 month" in entry["error"]
    assert "cannot be assumed to mean zero" in entry["error"]


def test_render_hybrid_section_handles_unreadable_store():
    response = render_hybrid_section("not-json", "Dengue", [2016, 2025], {})

    assert len(response) == 7
    assert isinstance(response[2], html.Div)
    assert "could not read" in str(response[2].children).lower()


def test_dropdown_status_icons_cover_lazy_warning_success_and_error():
    options = update_hybrid_dropdown_status({
        "Dengue": {"warnings_log": []},
        "Measles-Rubella": {"warnings_log": ["note"]},
        "Leptospirosis": {"error": "failed"},
    })
    labels = {option["value"]: option["label"] for option in options}

    assert labels["Dengue"].startswith("✓")
    assert labels["Measles-Rubella"].startswith("⚠")
    assert labels["Leptospirosis"].startswith("❌")
    assert labels["Tuberculosis"].startswith("❓")


def test_uploaded_diseases_drive_both_selectors_and_year_range():
    frame = pd.DataFrame({
        "year": [2012, 2027], "month": [1, 2],
        "disease": ["Malaria", "Novel syndrome"], "cases": [3, 4],
        "source": ["real", "real"],
    })
    frame["date"] = pd.to_datetime(dict(year=frame["year"], month=frame["month"], day=1))
    store = _store(frame)

    options = update_hybrid_dropdown_status({}, store)
    overview, overview_value, forecast_value = update_disease_controls(store)
    year_min, year_max, year_value, _ = update_year_control(store)

    assert [item["value"] for item in options] == ["Malaria", "Novel syndrome"]
    assert [item["value"] for item in overview] == ["all", "Malaria", "Novel syndrome"]
    assert (overview_value, forecast_value) == ("all", "Malaria")
    assert (year_min, year_max, year_value) == (2012, 2027, [2012, 2027])


def test_aggregate_charts_render_arbitrary_disease_names():
    frame = pd.DataFrame({
        "year": [2024, 2024], "month": [1, 2],
        "disease": ["Malaria", "Novel syndrome"], "cases": [3, 4],
    })
    bar = fig_disease_bar(frame)
    donut = fig_donut(frame)
    assert {trace.name for trace in bar.data} == {"Malaria", "Novel syndrome"}
    assert set(donut.data[0].labels) == {"Malaria", "Novel syndrome"}


def test_forecast_chart_does_not_plot_selected_candidate_twice():
    result = _result()
    figure = fig_hybrid_forecast(result, [2023, 2025])
    names = [trace.name for trace in figure.data]

    assert names == [
        "Hybrid historical error band",
        "Observed",
        "Benchmark: SARIMA-only",
        "Primary forecast: Hybrid (SARIMA + NNAR)",
    ]
    alternative = next(trace for trace in figure.data if trace.name == "Benchmark: SARIMA-only")
    selected = next(trace for trace in figure.data if trace.name.startswith("Primary forecast"))
    assert list(alternative.y) == list(result["sarima_forecast"].values)
    assert list(selected.y) == list(result["final_forecast"].values)
    assert not figure.layout.shapes  # real uploads do not receive a synthetic-data event annotation


def test_forecast_and_backtest_labels_disclose_actual_fallback_tier():
    result = _result()
    result["model_tier"] = "Holt-Winters (fallback)"
    result["evaluation_tier"] = "Naive drift (last resort)"

    forecast_names = [trace.name for trace in fig_hybrid_forecast(result, [2023, 2025]).data]
    backtest_names = [trace.name for trace in fig_backtest(result).data]

    assert "Benchmark: Holt-Winters-only" in forecast_names
    assert "Primary forecast: Hybrid (Holt-Winters + NNAR)" in forecast_names
    assert "Benchmark: Naive drift-only" in backtest_names
    assert "Primary: Hybrid (Naive drift + NNAR)" in backtest_names


def test_headline_includes_neutral_distinct_baselines_and_collapsed_diagnostics():
    result = _result()
    headline = _build_hybrid_metric_cards(result)
    rendered = str(headline)
    assert len(headline.children) == 5
    assert "Historical reference MAPE" in rendered
    assert "32.22%" in rendered
    assert "Seasonal-naive holdout MAPE/WAPE" in rendered
    assert "10.00% / 9.00%" in rendered
    for card in headline.children[-2:]:
        assert card.children[2].style["color"] == "#888"
    assert "Data source" in rendered
    assert "Primary architecture" in rendered
    assert "Holdout WAPE" in rendered
    assert "base-only 7.00% vs Hybrid 4.00%" in rendered
    assert "requires at least" not in rendered
    assert "Holdout RMSE" not in rendered
    assert "Holdout MAE" not in rendered
    assert "Holdout MAPE" not in rendered
    assert "Forecast interval" not in rendered

    diagnostics = str(_build_model_diagnostics(result))
    assert "Show more diagnostics" in diagnostics
    assert "Holdout RMSE" in diagnostics
    assert "Holdout MAE" in diagnostics
    assert "Holdout MAPE" in diagnostics
    assert "NNAR forecast adjustment" in diagnostics


def test_technical_baselines_match_forecast_and_handle_undefined_scores():
    result = _result()
    technical = view_callbacks.render_technical_baselines({'Dengue': result}, 'Dengue')
    assert str(technical) == str(_build_hybrid_metric_cards(result).children[-2:])
    result['baseline_metrics']['mape'] = None
    result['baseline_metrics']['wape'] = None
    technical = str(view_callbacks.render_technical_baselines({'Dengue':result}, 'Dengue'))
    assert '32.22%' in technical and 'N/A / N/A' in technical


def test_source_indicators_make_mixed_and_selected_source_visible():
    frame = generate_fallback_data()
    frame.loc[frame["disease"] == "Dengue", "source"] = "real"

    banner, badge = _build_source_indicators(_store(frame), "Dengue")

    assert "MIXED DATA" in banner.children
    assert "1 disease" in banner.children
    assert "Uploaded records" in badge.children
    assert "Population: unknown" in badge.children
    assert "Case classification: unknown" in badge.children


def test_all_zero_selection_card_names_mae_fallback_instead_of_wape():
    result = _result()
    for candidate in result["selection_metrics"].values():
        candidate["wape"] = None
    result["selection_metric"] = "mae"
    result["selection_threshold"] = 0.0

    rendered = str(_build_hybrid_metric_cards(result))

    assert "rolling MAE (all-zero actuals)" in rendered
    assert "base-only 2.00 cases/month vs Hybrid 1.00 cases/month" in rendered


def test_forecast_export_contains_history_forecast_bounds_and_provenance():
    exported = _build_forecast_export(serialize_pipeline_result(_result()), "Dengue")

    assert list(exported.columns[:21]) == [
        "disease", "date", "record_type", "observed_cases", "forecast_cases",
        "lower_error_band", "upper_error_band", "selected_model", "data_source", "interval_method",
        "production_base_tier", "holdout_base_tier", "selection_metric", "selection_threshold",
        "selection_base_tiers",
        "holdout_rmse", "holdout_mae", "holdout_mape", "holdout_wape",
        "mape_nonzero_months", "holdout_months",
    ]
    assert set(exported["record_type"]) == {"observed", "forecast"}
    assert set(exported["data_source"]) == {"real"}
    assert exported.loc[exported["record_type"] == "forecast", "lower_error_band"].notna().all()


def test_download_is_blocked_until_selected_forecast_is_cached():
    with pytest.raises(PreventUpdate):
        download_forecast_csv(1, {}, "Dengue")


def test_download_button_is_enabled_only_for_ready_selected_forecast():
    assert update_forecast_download_state({}, "Dengue")[0] is True
    assert update_forecast_download_state({"Dengue": {"error": "failed"}}, "Dengue")[0] is True
    disabled, title = update_forecast_download_state(
        {"Dengue": serialize_pipeline_result(_result())}, "Dengue"
    )
    assert disabled is False
    assert "historical error band" in title

