"""Tests for dashboard.data: XLSX parsing and validation."""

import base64
import io

import openpyxl
import pandas as pd
import pytest

from dashboard.data.xlsx_parser import epi_week_to_month, parse_surveillance_xlsx
from dashboard.data.validation import find_date_range_gap_notes, validate_and_clean_disease_df
from dashboard.callbacks.data_callbacks import load_data
import app as app_entry


# -- epi_week_to_month --------------------------------------------------

def test_epi_week_to_month_normal_week():
    year, month = epi_week_to_month(2024, 1)
    assert year == 2024
    assert month == 1


def test_epi_week_to_month_week_53_in_a_real_iso_53_week_year():
    # 2020 genuinely has an ISO week 53.
    year, month = epi_week_to_month(2020, 53)
    assert (year, month) == (2020, 12)


def test_epi_week_to_month_week_53_in_a_non_iso_53_week_year_falls_back_to_december():
    # 2025 does NOT have an ISO week 53 -- this must not raise, and must not
    # silently drop the data point (see the real bug this guards against).
    year, month = epi_week_to_month(2025, 53)
    assert (year, month) == (2025, 12)


def test_epi_week_to_month_week_54_still_raises():
    # Anything genuinely out of range should still fail loudly.
    with pytest.raises(ValueError):
        epi_week_to_month(2025, 60)


# -- parse_surveillance_xlsx ---------------------------------------------

def _build_minimal_workbook(sheet_name="Dengue", years=(2016, 2017), weeks=range(1, 6)):
    """Builds a tiny in-memory workbook matching the real DOH/PIDSR shape:
    a title row, a 'Morbidity Week' header row with year columns, then
    week rows, then a GRAND TOTAL row that must be ignored."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = sheet_name
    ws.append(["SOME TITLE ROW"])
    ws.append(["Morbidity Week"] + list(years))
    for w in weeks:
        ws.append([w] + [10 + w for _ in years])
    ws.append(["GRAND TOTAL"] + [999 for _ in years])  # must be excluded
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_parse_surveillance_xlsx_happy_path():
    file_bytes = _build_minimal_workbook()
    df, notes = parse_surveillance_xlsx(file_bytes)
    assert df is not None
    assert set(df["disease"]) == {"Dengue"}
    assert set(df["year"]) == {2016, 2017}
    assert (df["cases"] > 0).all()
    # The GRAND TOTAL row's value (999) must not have leaked into any month.
    assert (df["cases"] < 999).all()


def test_parse_surveillance_xlsx_fuzzy_sheet_name_match():
    # Real-world case that used to silently discard the whole disease.
    file_bytes = _build_minimal_workbook(sheet_name="dengue ")
    df, notes = parse_surveillance_xlsx(file_bytes)
    assert df is not None
    assert set(df["disease"]) == {"Dengue"}
    assert any("case/whitespace-insensitive" in n for n in notes)


def test_parse_surveillance_xlsx_missing_sheet_reports_which_one():
    wb = openpyxl.Workbook()
    wb.active.title = "SomethingElseEntirely"
    buf = io.BytesIO()
    wb.save(buf)
    df, notes = parse_surveillance_xlsx(buf.getvalue())
    assert df is None
    assert any("Dengue" in n for n in notes)
    assert any("Measles-Rubella" in n for n in notes)
    assert any("Leptospirosis" in n for n in notes)


def test_parse_surveillance_xlsx_not_an_excel_file():
    df, notes = parse_surveillance_xlsx(b"this is not a real xlsx file")
    assert df is None
    assert len(notes) == 1
    assert "Could not open" in notes[0]


# -- validate_and_clean_disease_df ----------------------------------------

def test_validate_drops_unrecognized_disease_but_keeps_known_ones():
    df = pd.DataFrame({
        "year": [2020, 2020],
        "month": [1, 1],
        "disease": ["Dengue", "Malaria"],
        "cases": [10, 500],
    })
    clean, notes = validate_and_clean_disease_df(df)
    assert list(clean["disease"]) == ["Dengue"]
    assert any("Malaria" in n for n in notes)


def test_validate_clips_negative_cases_to_zero():
    df = pd.DataFrame({"year": [2020], "month": [1], "disease": ["Dengue"], "cases": [-5]})
    clean, notes = validate_and_clean_disease_df(df)
    assert clean.iloc[0]["cases"] == 0
    assert any("negative" in n.lower() for n in notes)


def test_validate_drops_invalid_month_and_year():
    df = pd.DataFrame({
        "year": [2020, 3000],
        "month": [13, 5],
        "disease": ["Dengue", "Dengue"],
        "cases": [10, 20],
    })
    clean, notes = validate_and_clean_disease_df(df)
    assert clean.empty
    assert any("invalid month" in n.lower() for n in notes)


def test_validate_reports_no_issues_when_data_is_clean():
    df = pd.DataFrame({"year": [2020], "month": [1], "disease": ["Dengue"], "cases": [10]})
    clean, notes = validate_and_clean_disease_df(df)
    assert len(clean) == 1
    assert notes == ["No data-quality issues found in the uploaded data."]


def test_validate_discards_duplicate_observation_and_reports_it():
    df = pd.DataFrame({
        "year": [2020, 2020],
        "month": [6, 6],
        "disease": ["Dengue", "Dengue"],
        "cases": [100, 9999],
    })
    clean, notes = validate_and_clean_disease_df(df)
    assert len(clean) == 1
    assert clean.iloc[0]["cases"] == 100
    assert any("discarded 2 duplicate row(s)" in note.lower() for note in notes)


def test_date_range_gap_warning_distinguishes_absent_from_zero_case_months():
    df = pd.DataFrame({
        "year": [2024, 2024, 2024],
        "month": [1, 2, 4],
        "disease": ["Dengue"] * 3,
        "cases": [10, 0, 12],
        "source": ["real"] * 3,
    })

    notes = find_date_range_gap_notes(df)

    assert len(notes) == 1
    assert "Dengue: missing data for 1 month(s) between 2024-01 and 2024-04." in notes[0]
    assert "2 month(s)" not in notes[0]  # February's explicit zero is present, not missing.


def test_server_rejects_upload_exceeding_max_content_length_cleanly():
    client = app_entry.server.test_client()
    response = client.post(
        "/_dash-update-component",
        data=b"x" * (app_entry.server.config["MAX_CONTENT_LENGTH"] + 1),
        content_type="application/json",
    )
    assert response.status_code == 413
    assert response.get_json() == {"error": "The uploaded file is too large. Please upload a smaller file."}


def test_unicode_decode_error_returns_friendly_upload_message():
    contents = "data:text/csv;base64," + base64.b64encode(b"year,month,disease,cases\n2020,1,Dengue,\xff").decode("ascii")
    _, status, summary = load_data(contents, "corrupted.csv", None)
    assert "valid csv" in status.lower()
    assert "unicodedecodeerror" not in status.lower()
    assert "utf-8" not in status.lower()
    assert summary["success"] is False
