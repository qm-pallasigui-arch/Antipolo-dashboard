"""Source categories and population boundaries survive ingestion and export."""
import pandas as pd
import pytest

from dashboard.data.date_parser import normalize_surveillance_table
from dashboard.data.combine import prepare_uploaded_data
from dashboard.data.xlsx_parser import parse_surveillance_xlsx
from tests.test_data_ingestion import _build_minimal_workbook
from tests.test_callbacks import _result
from dashboard.callbacks.view_callbacks import _build_forecast_export
from dashboard.modeling.serialization import serialize_pipeline_result


def test_combined_source_category_is_not_renamed():
    frame, _ = parse_surveillance_xlsx(_build_minimal_workbook(sheet_name="Measles-Rubella"))
    assert set(frame.disease) == {"Measles-Rubella"}
    assert set(frame.population) == {"unknown"}
    assert set(frame.case_classification) == {"unknown"}


@pytest.mark.parametrize("column,values", [
    ("population", ["all-age", "ages 5-19"]),
    ("case_classification", ["confirmed", "suspected"]),
    ("source", ["real", "mock"]),
])
def test_mixed_populations_and_sources_rejected_before_aggregation(column, values):
    frame = pd.DataFrame({"date": ["2024-01-01", "2024-01-02"],
                          "disease": ["Dengue"] * 2, "cases": [1, 2], column: values})
    with pytest.raises(ValueError, match="Mixed"):
        normalize_surveillance_table(frame)


def test_metadata_preserved_through_daily_aggregation_and_storage():
    frame = pd.DataFrame({"date": ["2024-01-01", "2024-01-02"],
                          "disease": ["Dengue"] * 2, "cases": [1, 2],
                          "population": ["all-age"] * 2, "case_classification": ["unknown"] * 2,
                          "source_dataset": ["original.csv"] * 2})
    monthly, _ = normalize_surveillance_table(frame)
    monthly["source"] = "real"
    stored = prepare_uploaded_data(monthly)
    assert stored.iloc[0].population == "all-age"
    assert stored.iloc[0].source_dataset == "original.csv"
    assert stored.iloc[0].cases == 3


def test_export_preserves_provenance_benchmarks_and_identification():
    result = _result()
    result.update(status="hybrid_success", provenance={"population": "all-age",
                  "case_classification": "unknown", "source_dataset": "original.xlsx"},
                  model_identification={"production": {"order": [1, 0, 0]}})
    result["test_seasonal_naive"] = result["test_actual"] * 0
    exported = _build_forecast_export(serialize_pipeline_result(result), "Dengue")
    assert set(exported.population) == {"all-age"}
    assert set(exported.case_classification) == {"unknown"}
    assert set(exported.sarima_holdout_wape) == {7.0}
    assert exported.test_seasonal_naive.notna().sum() == 2
    assert "production" in exported.model_identification.iloc[0]


def test_partial_workbook_coverage_is_visible():
    _, notes = parse_surveillance_xlsx(_build_minimal_workbook(weeks=range(1, 3)))
    assert any("missing week rows" in note for note in notes)
    assert any("provisional" in note for note in notes)


def test_synthetic_upload_cannot_be_reclassified_real():
    frame = pd.DataFrame({"year":[2024],"month":[1],"disease":["Dengue"],"cases":[1],"source":["mock"]})
    with pytest.raises(ValueError, match="cannot be relabeled"):
        normalize_surveillance_table(frame)


def test_duplicate_week_is_rejected_before_monthly_sum():
    frame = pd.DataFrame({"year":[2024,2024],"week":[1,1],"disease":["Dengue"]*2,"cases":[1,2]})
    with pytest.raises(ValueError, match="Duplicate weekly"):
        normalize_surveillance_table(frame)


@pytest.mark.parametrize("column,value", [("month",1.5),("year",2024.5),("month",13)])
def test_fractional_or_invalid_calendar_fields_rejected(column,value):
    frame=pd.DataFrame({"year":[2024],"month":[1],"disease":["Dengue"],"cases":[1]})
    frame[column]=value
    with pytest.raises(ValueError, match="Invalid month"):
        normalize_surveillance_table(frame)
