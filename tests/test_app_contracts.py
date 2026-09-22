"""Integration-level contracts for Dash wiring and callback-facing state."""

import base64
import json

import pandas as pd
from dash import no_update

import app as app_entry
from dashboard.callbacks.data_callbacks import load_data
from dashboard.callbacks.view_callbacks import _data_signature, update_aggregate_section
from dashboard.ui.layout import build_layout


def _component_ids(component):
    ids = set()
    if isinstance(component, (list, tuple)):
        for child in component:
            ids.update(_component_ids(child))
        return ids
    if component is None:
        return ids
    component_id = getattr(component, "id", None)
    if component_id:
        ids.add(component_id)
    children = getattr(component, "children", None)
    if children is not None:
        ids.update(_component_ids(children))
    return ids


def _csv_upload(rows):
    csv = pd.DataFrame(rows).to_csv(index=False).encode("utf-8")
    return "data:text/csv;base64," + base64.b64encode(csv).decode("ascii")


def test_layout_contains_every_callback_component_id():
    layout_ids = _component_ids(build_layout())
    callback_ids = {
        "store-data", "upload-status", "upload-csv", "store-hybrid",
        "store-upload-summary", "upload-summary-content",
        "f-hybrid-disease", "f-year", "hybrid-metric-row",
        "hybrid-warnings-panel", "chart-hybrid-forecast", "chart-backtest",
        "chart-residual", "chart-decomp", "metric-row", "chart-donut",
        "chart-heatmap", "chart-bar", "data-table", "f-disease",
    }
    assert callback_ids <= layout_ids


def test_app_import_wires_layout_and_callbacks():
    assert app_entry.dash_app.layout is not None
    assert any(
        key.startswith("..store-data.data...upload-status.children...store-upload-summary.data")
        for key in app_entry.dash_app.callback_map
    )
    assert any(
        key.startswith("..store-hybrid.data...hybrid-metric-row.children")
        for key in app_entry.dash_app.callback_map
    )


def test_vercel_entrypoint_is_wsgi_app():
    assert app_entry.app is app_entry.server
    assert callable(app_entry.app)


def test_load_data_initializes_mock_data_without_upload():
    store, status, summary = load_data(None, None, None)
    frame = pd.read_json(store, orient="split")

    assert not frame.empty
    assert set(frame["source"]) == {"mock"}
    assert "synthetic" in status.lower()
    assert summary["uploaded"] is False


def test_load_data_accepts_csv_and_backfills_missing_diseases():
    contents = _csv_upload([
        {"year": 2020, "month": 1, "disease": " dengue ", "cases": 12},
    ])
    store, status, summary = load_data(contents, "observations.csv", None)
    frame = pd.read_json(store, orient="split")

    assert "Dengue" in set(frame["disease"])
    assert set(frame.loc[frame["disease"] == "Dengue", "source"]) == {"real"}
    assert frame["disease"].nunique() == 7
    assert "1 real disease" in status
    assert summary["success"] is True


def test_upload_summary_has_expected_keys_and_upload_grounded_disease_counts():
    contents = _csv_upload([
        {"year": 2022, "month": 1, "disease": "Dengue", "cases": 12},
        {"year": 2022, "month": 2, "disease": "Dengue", "cases": 0},
        {"year": 2023, "month": 1, "disease": "Measles", "cases": 4},
    ])

    _, _, summary = load_data(contents, "observations.csv", None)

    expected_keys = {
        "success", "filename", "loaded_at", "year_min", "year_max",
        "diseases", "warnings", "preview",
    }
    assert expected_keys <= summary.keys()
    by_name = {item["name"]: item for item in summary["diseases"]}
    assert len(by_name) == 7
    assert by_name["Dengue"] == {
        "name": "Dengue", "source": "real", "row_count": 2,
        "year_min": 2022, "year_max": 2022,
    }
    assert by_name["Measles"]["row_count"] == 1
    assert by_name["Acute Respiratory Infection"]["source"] == "mock"
    assert by_name["Acute Respiratory Infection"]["row_count"] == 120
    assert (summary["year_min"], summary["year_max"]) == (2022, 2023)


def test_refresh_preserves_existing_upload_summary():
    contents = _csv_upload([
        {"year": 2024, "month": 1, "disease": "Dengue", "cases": 8},
    ])
    store, _, summary = load_data(contents, "observations.csv", None)

    restored_store, status, restored_summary = load_data(None, None, store, summary)

    assert restored_store is no_update
    assert restored_summary is no_update
    assert "restored" in status.lower()


def test_aggregate_callback_returns_expected_output_shape():
    store, _, _ = load_data(None, None, None)
    outputs = update_aggregate_section(store, [2016, 2025], "all")

    assert len(outputs) == 5
    assert outputs[0] is not None
    assert len(outputs[1].data) > 0
    assert len(outputs[2].data) > 0
    assert len(outputs[3].data) > 0
    assert outputs[4].data


def test_dataset_signature_changes_when_upload_data_changes():
    first, _, _ = load_data(None, None, None)
    second, _, _ = load_data(
        _csv_upload([{"year": 2020, "month": 1, "disease": "Dengue", "cases": 99}]),
        "observations.csv",
        None,
    )

    assert _data_signature(first) != _data_signature(second)
    assert json.loads(first)["columns"] == ["year", "month", "disease", "cases", "source", "date"]
