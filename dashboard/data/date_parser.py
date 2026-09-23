"""Normalize common surveillance date layouts to monthly observations.

The dashboard's modeling contract is deliberately small: one row per
``(year, month, disease)`` with a numeric ``cases`` value.  Uploads may arrive
with those canonical columns, a daily/monthly date column, or ISO week fields.
This module converts those representations without silently choosing how an
ambiguous numeric date should be interpreted.
"""

from __future__ import annotations

import calendar
from datetime import date, datetime
import re

import pandas as pd


DATE_CONVENTIONS = {
    "day-first": {"dayfirst": True, "yearfirst": False, "label": "day/month/year"},
    "month-first": {"dayfirst": False, "yearfirst": False, "label": "month/day/year"},
    "year-first": {"dayfirst": False, "yearfirst": True, "label": "year/month/day"},
}
DATE_COLUMN_CANDIDATES = (
    "date", "report_date", "reporting_date", "onset_date", "observation_date",
    "period", "reporting_period",
)


def _normalise_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out.columns = (
        out.columns.astype(str).str.strip().str.lower()
        .str.replace(r"[\s\-]+", "_", regex=True)
    )
    return out


def _parse_one_date(value, convention: str):
    if pd.isna(value):
        return pd.NaT
    if isinstance(value, (pd.Timestamp, datetime, date)):
        return pd.Timestamp(value)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        # Excel's default 1900 date system.  Serial values outside a plausible
        # modern range are allowed to fail validation instead of being guessed.
        if 1 <= float(value) <= 100_000:
            return pd.Timestamp("1899-12-30") + pd.to_timedelta(float(value), unit="D")
    settings = DATE_CONVENTIONS[convention]
    text = str(value).strip()
    iso_like = bool(re.match(r"^\d{4}[-/]\d{1,2}[-/]\d{1,2}(?:[T\s]|$)", text))
    try:
        return pd.to_datetime(
            text,
            errors="raise",
            dayfirst=False if iso_like else settings["dayfirst"],
            yearfirst=True if iso_like else settings["yearfirst"],
        )
    except (TypeError, ValueError, OverflowError):
        return pd.NaT


def _date_column(df: pd.DataFrame) -> str | None:
    return next((name for name in DATE_COLUMN_CANDIDATES if name in df.columns), None)


def _from_year_month(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    out = df.copy()
    numeric_year = pd.to_numeric(out["year"], errors="coerce")
    numeric_month = pd.to_numeric(out["month"], errors="coerce")
    textual_month = numeric_month.isna() & out["month"].notna() & numeric_year.notna()
    if textual_month.any():
        month_lookup = {
            name.lower(): index
            for index, name in enumerate(calendar.month_name)
            if name
        }
        month_lookup.update({
            name.lower(): index
            for index, name in enumerate(calendar.month_abbr)
            if name
        })
        numeric_month.loc[textual_month] = (
            out.loc[textual_month, "month"].astype(str).str.strip().str.lower().map(month_lookup)
        )
    out["year"] = numeric_year
    out["month"] = numeric_month
    notes = ["Used the supplied year and month columns."]
    if textual_month.any():
        notes.append(f"Interpreted {int(textual_month.sum())} textual month value(s).")
    return out, notes


def _from_iso_week(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    # Local import avoids coupling the generic parser to workbook parsing at
    # module-import time while preserving the existing ISO Thursday rule.
    from dashboard.data.xlsx_parser import epi_week_to_month

    out = df.copy()
    years = pd.to_numeric(out["year"], errors="coerce")
    weeks = pd.to_numeric(out["week"], errors="coerce")
    converted = []
    for year, week in zip(years, weeks):
        try:
            converted.append(epi_week_to_month(int(year), int(week)))
        except (TypeError, ValueError, OverflowError):
            converted.append((None, None))
    out["year"] = [item[0] for item in converted]
    out["month"] = [item[1] for item in converted]
    invalid = sum(item == (None, None) for item in converted)
    notes = ["Converted ISO epidemiological weeks to months using each week's Thursday."]
    if invalid:
        notes.append(f"Could not interpret {invalid} row(s) with an invalid year/week value.")
    return out, notes


def _from_date_column(
    df: pd.DataFrame, column: str, convention: str,
) -> tuple[pd.DataFrame, list[str]]:
    out = df.copy()
    parsed = out[column].map(lambda value: _parse_one_date(value, convention))
    invalid = int(parsed.isna().sum())
    out["year"] = parsed.dt.year
    out["month"] = parsed.dt.month
    notes = [
        f"Parsed '{column}' using the selected {DATE_CONVENTIONS[convention]['label']} convention "
        "for ambiguous numeric dates."
    ]
    if invalid:
        notes.append(f"Could not interpret {invalid} row(s) in the '{column}' date column.")
    return out, notes


def normalize_surveillance_table(
    df: pd.DataFrame, date_convention: str = "day-first",
) -> tuple[pd.DataFrame, list[str]]:
    """Return monthly ``year/month/disease/cases`` rows and parsing notes.

    Daily rows and repeated weekly rows are summed into their calendar month.
    Duplicate monthly rows are therefore resolved during intentional temporal
    aggregation, before the downstream duplicate-observation guardrail runs.
    """
    if date_convention not in DATE_CONVENTIONS:
        raise ValueError(f"Unsupported date convention: {date_convention}")

    table = _normalise_columns(df)
    missing_measures = {"disease", "cases"} - set(table.columns)
    if missing_measures:
        raise ValueError(
            "Missing columns: " + ", ".join(sorted(missing_measures))
            + ". Required measure columns: disease and cases."
        )

    if {"year", "month"}.issubset(table.columns):
        table, notes = _from_year_month(table)
    elif {"year", "week"}.issubset(table.columns):
        table, notes = _from_iso_week(table)
    else:
        column = _date_column(table)
        if column is None:
            raise ValueError(
                "Missing date fields. Supply year/month, year/week, or a supported date column "
                f"({', '.join(DATE_COLUMN_CANDIDATES)})."
            )
        table, notes = _from_date_column(table, column, date_convention)

    monthly = table[["year", "month", "disease", "cases"]].copy()
    monthly["cases"] = pd.to_numeric(monthly["cases"], errors="coerce")
    invalid_cases = int(monthly["cases"].isna().sum())
    if invalid_cases:
        notes.append(f"Dropped {invalid_cases} row(s) with a non-numeric 'cases' value before aggregation.")
        monthly = monthly.dropna(subset=["cases"])
    negative_cases = int((monthly["cases"] < 0).sum())
    if negative_cases:
        notes.append(f"Clipped {negative_cases} negative 'cases' value(s) to 0 before aggregation.")
        monthly["cases"] = monthly["cases"].clip(lower=0)
    valid_keys = monthly["year"].notna() & monthly["month"].notna()
    before_valid_dates = len(monthly)
    monthly = monthly.loc[valid_keys].copy()
    if len(monthly) < before_valid_dates:
        notes.append(f"Dropped {before_valid_dates - len(monthly)} row(s) whose date could not be interpreted.")

    before_aggregation = len(monthly)
    monthly = monthly.groupby(["year", "month", "disease"], as_index=False, dropna=False)["cases"].sum(min_count=1)
    aggregated = before_aggregation - len(monthly)
    if aggregated > 0:
        notes.append(f"Aggregated {aggregated} daily or weekly row(s) into monthly totals.")
    return monthly, notes
