"""Behavioral regression tests for the callback layer."""

import pandas as pd
import pytest
from dash import html
from dash.exceptions import PreventUpdate

from dashboard.callbacks import view_callbacks
from dashboard.callbacks.view_callbacks import (
    CACHE_SIGNATURE_KEY,
    _build_forecast_export,
    _build_source_indicators,
    _data_signature,
    _get_or_compute_disease,
    _prepare_hybrid_entry,
    download_forecast_csv,
    render_hybrid_section,
    update_forecast_download_state,
    update_hybrid_dropdown_status,
)
from dashboard.data.mock_data import generate_fallback_data
from dashboard.modeling.serialization import serialize_pipeline_result


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
        "sarima_forecast": future,
        "hybrid_forecast": future,
        "final_forecast": future,
        "ci_lower": future - 2,
        "ci_upper": future + 2,
        "test_actual": history[-2:],
        "test_sarima_only": pd.Series([21.0, 22.0], index=backtest_index),
        "test_hybrid": pd.Series([21.5, 22.5], index=backtest_index),
        "metrics": {"rmse": 1.0, "mae": 1.0, "mape": 5.0},
        "sarima_only_metrics": {"rmse": 2.0, "mae": 2.0, "mape": 8.0},
        "final_metrics": {"rmse": 1.0, "mae": 1.0, "mape": 5.0},
        "selected_model": "hybrid",
        "data_source": data_source,
        "model_tier": "test",
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
        {CACHE_SIGNATURE_KEY: "old", "Measles": {"stale": True}},
    )

    assert error is None
    assert "Measles" not in returned
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


def test_render_hybrid_section_handles_unreadable_store():
    response = render_hybrid_section("not-json", "Dengue", [2016, 2025], {})

    assert len(response) == 7
    assert isinstance(response[2], html.Div)
    assert "could not read" in str(response[2].children).lower()


def test_dropdown_status_icons_cover_lazy_warning_success_and_error():
    options = update_hybrid_dropdown_status({
        "Dengue": {"warnings_log": []},
        "Measles": {"warnings_log": ["note"]},
        "Leptospirosis": {"error": "failed"},
    })
    labels = {option["value"]: option["label"] for option in options}

    assert labels["Dengue"].startswith("✓")
    assert labels["Measles"].startswith("⚠")
    assert labels["Leptospirosis"].startswith("❌")
    assert labels["Tuberculosis"].startswith("❓")


def test_source_indicators_make_mixed_and_selected_source_visible():
    frame = generate_fallback_data()
    frame.loc[frame["disease"] == "Dengue", "source"] = "real"

    banner, badge = _build_source_indicators(_store(frame), "Dengue")

    assert "MIXED DATA" in banner.children
    assert "1 disease" in banner.children
    assert badge.children == "Uploaded real data"


def test_forecast_export_contains_history_forecast_bounds_and_provenance():
    exported = _build_forecast_export(serialize_pipeline_result(_result()), "Dengue")

    assert list(exported.columns) == [
        "disease", "date", "record_type", "observed_cases", "forecast_cases",
        "lower_95", "upper_95", "selected_model", "data_source",
    ]
    assert set(exported["record_type"]) == {"observed", "forecast"}
    assert set(exported["data_source"]) == {"real"}
    assert exported.loc[exported["record_type"] == "forecast", "lower_95"].notna().all()


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
    assert "uncertainty bounds" in title

