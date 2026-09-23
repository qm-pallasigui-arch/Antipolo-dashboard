"""Flexible-date and offline-PDF preprocessing contracts."""

import json
from pathlib import Path

import pandas as pd

from dashboard.data.date_parser import normalize_surveillance_table
from dashboard.data import pdf_converter


def test_day_first_convention_resolves_ambiguous_numeric_dates():
    frame = pd.DataFrame({
        "date": ["03/04/2024", "17/04/2024"],
        "disease": ["Dengue", "Dengue"],
        "cases": [2, 3],
    })
    monthly, notes = normalize_surveillance_table(frame, "day-first")

    assert monthly.to_dict("records") == [
        {"year": 2024, "month": 4, "disease": "Dengue", "cases": 5}
    ]
    assert any("day/month/year" in note for note in notes)


def test_month_first_convention_changes_ambiguous_date_interpretation():
    frame = pd.DataFrame({"date": ["03/04/2024"], "disease": ["Dengue"], "cases": [2]})
    monthly, _ = normalize_surveillance_table(frame, "month-first")

    assert (monthly.iloc[0]["year"], monthly.iloc[0]["month"]) == (2024, 3)


def test_text_month_iso_timestamp_and_excel_serial_are_supported():
    frame = pd.DataFrame({
        "date": ["15 January 2024", "2024-01-20T10:30:00", 45322],
        "disease": ["Dengue"] * 3,
        "cases": [1, 2, 3],
    })
    monthly, _ = normalize_surveillance_table(frame, "day-first")

    assert monthly["cases"].sum() == 6
    assert set(monthly["year"]) == {2024}


def test_iso_week_rows_are_aggregated_to_months():
    frame = pd.DataFrame({
        "year": [2024, 2024], "week": [1, 2],
        "disease": ["Dengue", "Dengue"], "cases": [4, 6],
    })
    monthly, notes = normalize_surveillance_table(frame)

    assert monthly.iloc[0]["cases"] == 10
    assert any("epidemiological weeks" in note for note in notes)


def test_textual_month_with_year_columns_is_supported():
    frame = pd.DataFrame({
        "year": [2024, 2024], "month": ["January", "Jan"],
        "disease": ["Dengue", "Dengue"], "cases": [4, 6],
    })
    monthly, notes = normalize_surveillance_table(frame)

    assert monthly.to_dict("records") == [
        {"year": 2024, "month": 1.0, "disease": "Dengue", "cases": 10}
    ]
    assert any("textual month" in note for note in notes)


def test_invalid_dates_are_reported_and_removed():
    frame = pd.DataFrame({
        "date": ["not a date", "2024-05-01"],
        "disease": ["Dengue", "Dengue"], "cases": [99, 1],
    })
    monthly, notes = normalize_surveillance_table(frame)

    assert monthly["cases"].sum() == 1
    assert any("could not be interpreted" in note.lower() for note in notes)


def test_pdf_converter_writes_canonical_csv_and_review_report(monkeypatch):
    extracted = pd.DataFrame({
        "Report Date": ["01/02/2024", "15/02/2024"],
        "Disease": ["Dengue", "Dengue"],
        "Cases": [4, 6],
    })
    monkeypatch.setattr(
        pdf_converter,
        "extract_pdf_tables",
        lambda path: ([extracted], {"pages": 1, "page_results": [], "tables_extracted": 1}),
    )
    captured = {}
    monkeypatch.setattr(Path, "mkdir", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        pd.DataFrame,
        "to_csv",
        lambda self, path, index=False: captured.update({"rows": self.to_dict("records"), "index": index}),
    )
    monkeypatch.setattr(
        Path,
        "write_text",
        lambda self, text, encoding=None: captured.update({"report": json.loads(text)}) or len(text),
    )
    report = pdf_converter.convert_pdf("source.pdf", "converted.csv", "day-first")

    assert captured["rows"] == [
        {"year": 2024, "month": 2, "disease": "Dengue", "cases": 10}
    ]
    assert report["review_required"] is True
    assert captured["report"]["rows_written"] == 1

