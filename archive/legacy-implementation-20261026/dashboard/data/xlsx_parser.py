"""
Parser for real DOH/PIDSR-style surveillance workbooks: one sheet per disease,
each with a "Morbidity Week" header row followed by weeks 1-53 (rows) x years
(columns).

This was originally a single ~100-line function (cyclomatic complexity 19 --
radon grade C). It's broken into one function per concern below so each piece
is independently testable and the control flow in `parse_surveillance_xlsx`
itself reads as a short, linear checklist.
"""

import io
from datetime import date

import numpy as np
import pandas as pd

from dashboard.config import (
    MAX_WORKBOOK_CELLS,
    MAX_WORKBOOK_SHEETS,
    MAX_WORKSHEET_COLUMNS,
    MAX_WORKSHEET_ROWS,
    REAL_SHEET_TO_DISEASE,
)
from dashboard.logging_config import get_logger

logger = get_logger(__name__)


def epi_week_to_month(year: int, week: int) -> tuple:
    """Maps an epidemiological (year, week) to the calendar (year, month) that
    contains the ISO week's Thursday. Some source workbooks report a week 53
    in years that Python's ISO calendar doesn't recognize as having one (their
    epi-week convention differs slightly from strict ISO 8601) -- rather than
    silently dropping that real data point, it's assigned to December of the
    reporting year."""
    try:
        d = date.fromisocalendar(int(year), int(week), 4)  # Thursday of that week
        return d.year, d.month
    except ValueError:
        if int(week) == 53:
            return int(year), 12
        raise


def _open_workbook(file_bytes: bytes):
    """Returns (ExcelFile, None) or (None, error_note)."""
    try:
        return pd.ExcelFile(io.BytesIO(file_bytes)), None
    except Exception as e:
        logger.warning("could not open uploaded workbook: %s", e)
        return None, "Could not open this file as an Excel workbook."


def _match_sheet_name(available_sheets: list, expected_name: str):
    """Case/whitespace-insensitive lookup. Returns (actual_name_or_None, note_or_None)."""
    normalized = {s.strip().lower(): s for s in available_sheets}
    actual = normalized.get(expected_name.strip().lower())
    if actual is None:
        return None, None
    note = None
    if actual != expected_name:
        note = f"Matched sheet '{actual}' to expected name '{expected_name}' (case/whitespace-insensitive match)."
    return actual, note


def _find_header_row(raw: pd.DataFrame, search_rows: int = 10):
    """Finds the row index whose first cell reads 'Morbidity Week'. Returns None if absent."""
    for i in range(min(search_rows, len(raw))):
        if str(raw.iloc[i, 0]).strip().lower() == "morbidity week":
            return i
    return None


def _extract_valid_year_columns(year_cols_raw: list, sheet_name: str):
    """Filters header-row values down to plausible year numbers. Returns (year_cols, notes)."""
    year_cols, notes = [], []
    for yc in year_cols_raw:
        try:
            y = int(float(yc))
            if float(yc) == y and 1900 <= y <= 2100:
                year_cols.append(yc)
            else:
                notes.append(f"Sheet '{sheet_name}': column header '{yc}' is out of a plausible year range, skipped.")
        except (ValueError, TypeError):
            notes.append(f"Sheet '{sheet_name}': column header '{yc}' isn't a valid year, skipped.")
    return year_cols, notes


def _extract_week_rows(raw: pd.DataFrame, header_row_idx: int, year_cols_raw: list) -> pd.DataFrame:
    """Returns only the rows below the header whose first cell is a week number 1-53
    (this is what naturally excludes TOTAL / GRAND TOTAL / verification rows,
    since their first cell isn't numeric)."""
    data = raw.iloc[header_row_idx + 1:].copy()
    data.columns = ["week"] + list(year_cols_raw)
    data["week_num"] = pd.to_numeric(data["week"], errors="coerce")
    numeric = data["week_num"].notna()
    if (numeric & ((data["week_num"] % 1 != 0) | ~data["week_num"].between(1, 53))).any():
        raise ValueError("Week numbers must be whole numbers from 1 to 53.")
    data = data[numeric]
    if data["week_num"].duplicated().any():
        raise ValueError("Duplicate week rows require source reconciliation.")
    return data


def _check_workbook_limits(raw: pd.DataFrame, total_cells: int):
    """Returns a safe error note and updated cell count when resource limits are exceeded."""
    if len(raw.index) > MAX_WORKSHEET_ROWS or len(raw.columns) > MAX_WORKSHEET_COLUMNS:
        return (
            f"Worksheet exceeds the {MAX_WORKSHEET_ROWS:,}-row or {MAX_WORKSHEET_COLUMNS}-column limit.",
            total_cells,
        )
    total_cells += len(raw.index) * len(raw.columns)
    if total_cells > MAX_WORKBOOK_CELLS:
        return f"Workbooks are limited to {MAX_WORKBOOK_CELLS:,} parsed cells.", total_cells
    return None, total_cells


def _cells_to_records(week_rows: pd.DataFrame, year_cols: list, disease_label: str, sheet_name: str):
    """Converts validated week x year cells into (year, month, disease, cases) records.
    Returns (records, skipped_count, notes)."""
    records, notes, skipped = [], [], 0
    for _, row in week_rows.iterrows():
        week = int(row["week_num"])
        for year_col in year_cols:
            val = row[year_col]
            if pd.isna(val):
                notes.append(f"Sheet '{sheet_name}', week {week}, year {year_col}: blank observation remains unknown, not zero; monthly coverage is unverified.")
                continue
            num_val = pd.to_numeric(val, errors="coerce")
            if pd.isna(num_val) or not np.isfinite(num_val) or num_val < 0 or num_val % 1:
                raise ValueError(f"Sheet '{sheet_name}', week {week}, year {year_col}: cases must be finite, nonnegative whole numbers.")
            yr, mo = epi_week_to_month(int(float(year_col)), week)
            records.append({"year": yr, "month": mo, "disease": disease_label, "cases": float(num_val)})
    return records, skipped, notes


def parse_surveillance_xlsx(file_bytes: bytes):
    """
    Parses a real DOH/PIDSR-style workbook and returns (monthly_df, parse_notes).

    monthly_df: long-format DataFrame (year, month, disease, cases) aggregated
        to monthly, or None if no recognized disease sheets were found.
    parse_notes: list of human-readable strings describing anything that went
        differently than expected -- always returned, even on success, so
        nothing is silently lost (fuzzy-matched sheet names, missing sheets,
        skipped cells, etc.)
    """
    notes = ["Weekly-to-monthly mapping is provisional: ISO Thursday; non-ISO week 53 maps to December. Official epidemiological calendar confirmation is pending.",
             "Population: unknown; case classification: unknown. Workbook format alone does not verify eligibility."]
    xl, open_error = _open_workbook(file_bytes)
    if open_error:
        return None, [open_error]

    if len(xl.sheet_names) > MAX_WORKBOOK_SHEETS:
        return None, [f"Workbooks are limited to {MAX_WORKBOOK_SHEETS} sheets."]

    all_records = []
    incomplete_diseases = set()
    total_skipped = 0
    total_cells = 0

    known_aliases = {name.strip().casefold(): (name, label) for name, label in REAL_SHEET_TO_DISEASE.items()}
    for actual_sheet in xl.sheet_names:
        known = known_aliases.get(actual_sheet.strip().casefold())
        disease_label = known[1] if known else actual_sheet.strip()
        if known and actual_sheet != known[0]:
            notes.append(
                f"Matched sheet '{actual_sheet}' to expected name '{known[0]}' "
                "(case/whitespace-insensitive match)."
            )
        raw = xl.parse(actual_sheet, header=None)
        limit_error, total_cells = _check_workbook_limits(raw, total_cells)
        if limit_error:
            return None, [f"Worksheet '{actual_sheet}': {limit_error}"]
        header_row_idx = _find_header_row(raw)
        if header_row_idx is None:
            notes.append(
                f"Sheet '{actual_sheet}' has no 'Morbidity Week' header row in its first 10 rows and was skipped."
            )
            continue

        year_cols_raw = raw.iloc[header_row_idx, 1:].tolist()
        year_cols, year_notes = _extract_valid_year_columns(year_cols_raw, actual_sheet)
        notes.extend(year_notes)

        week_rows = _extract_week_rows(raw, header_row_idx, year_cols_raw)
        absent = sorted(set(range(1, 53)) - set(week_rows["week_num"].astype(int)))
        if absent:
            incomplete_diseases.add(disease_label)
            notes.append(f"Sheet '{actual_sheet}': missing week rows {absent}; monthly coverage is incomplete.")
        if week_rows.loc[week_rows["week_num"] <= 52, year_cols].isna().any().any():
            incomplete_diseases.add(disease_label)
        records, skipped, cell_notes = _cells_to_records(week_rows, year_cols, disease_label, actual_sheet)
        all_records.extend(records)
        total_skipped += skipped
        notes.extend(cell_notes)

        logger.info("parsed sheet '%s' -> disease '%s': %d records, %d skipped cells",
                    actual_sheet, disease_label, len(records), skipped)

    if total_skipped:
        notes.append(f"{total_skipped} non-numeric cell(s) in the weekly data were skipped.")

    if not all_records:
        notes.append("No usable weekly data found in any worksheet.")
        return None, notes

    weekly_df = pd.DataFrame(all_records)
    monthly = weekly_df.groupby(["year", "month", "disease"], as_index=False)["cases"].sum()
    monthly["cases"] = monthly["cases"].astype(int)
    monthly["coverage_status"] = monthly["disease"].map(lambda d: "incomplete" if d in incomplete_diseases else "provisional week calendar; week 53 meaning unverified")
    monthly["population"] = "unknown"
    monthly["case_classification"] = "unknown"
    return monthly, notes
