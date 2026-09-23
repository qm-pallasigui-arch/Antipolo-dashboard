"""
Data-loading callback: turns an uploaded file (or nothing, on first load) into
the combined real+mock dataset. Training the hybrid pipeline is NOT done here
anymore -- see dashboard/callbacks/view_callbacks.py's `render_hybrid_section`,
which computes each disease lazily, on demand, the first time it's selected.
(An earlier version eagerly computed all 7 diseases here on every data load,
which is what caused the Render free-tier timeout: the whole page blocked on
work for 6 diseases nobody had asked to see yet.)

`load_data` was originally a single function with radon cyclomatic complexity
21 (grade D) -- the worst offender in the whole codebase. It handled base64
decoding, CSV parsing, XLSX parsing, validation, combining, and building a
human-readable status message, all inline with nested try/except and if/elif
chains. It's split below into one function per file-type branch, so
`load_data` itself is now just: decode -> dispatch by extension -> validate ->
combine -> build status. Each branch is independently testable.
"""

import base64
import io
from datetime import datetime, timezone

import pandas as pd
from dash import Input, Output, State, no_update
from dashboard.config import (
    DISEASES, MAX_CSV_ROWS, MAX_UPLOAD_BYTES, MAX_WORKBOOK_CELLS,
    MAX_WORKBOOK_SHEETS, MAX_WORKSHEET_COLUMNS, MAX_WORKSHEET_ROWS,
)

from dashboard.app_instance import app  # noqa: F401  (ensures `callback` binds to our app)
from dashboard.data.mock_data import generate_fallback_data
from dashboard.data.date_parser import normalize_surveillance_table
from dashboard.data.xlsx_parser import parse_surveillance_xlsx
from dashboard.data.validation import find_date_range_gap_notes, validate_and_clean_disease_df
from dashboard.data.combine import combine_real_and_mock
from dashboard.logging_config import get_logger

logger = get_logger(__name__)

UPLOAD_INFO_PREFIXES = (
    "No data-quality issues", "Matched sheet", "Used the supplied",
    "Parsed '", "Converted ISO", "Imported tabular", "Interpreted ", "Aggregated ",
)


class UploadRejectedError(ValueError):
    """A bounded, safe-to-display upload rejection reason."""


def _decode_upload(contents: str) -> bytes:
    try:
        _content_type, content_string = contents.split(",", 1)
        decoded = base64.b64decode(content_string, validate=True)
    except (ValueError, UnicodeError, base64.binascii.Error) as exc:
        raise UploadRejectedError("The uploaded file payload is not valid base64 data.") from exc
    if len(decoded) > MAX_UPLOAD_BYTES:
        raise UploadRejectedError(
            f"The uploaded file exceeds the {MAX_UPLOAD_BYTES // (1024 * 1024)} MB limit."
        )
    return decoded


def _load_csv(decoded: bytes, date_convention: str = "day-first"):
    """Returns (real_df, parse_notes, error_message). Exactly one of
    (real_df, error_message) is non-None."""
    df = pd.read_csv(io.StringIO(decoded.decode("utf-8")), nrows=MAX_CSV_ROWS + 1)
    if len(df) > MAX_CSV_ROWS:
        return None, [], f"CSV files are limited to {MAX_CSV_ROWS:,} rows."
    try:
        real_df, parse_notes = normalize_surveillance_table(df, date_convention)
    except ValueError as exc:
        return None, [], str(exc)
    real_df["source"] = "real"
    return real_df, parse_notes, None


def _load_tabular_xlsx(decoded: bytes, date_convention: str):
    """Try ordinary row-based sheets after the specialized PIDSR parser."""
    try:
        xl = pd.ExcelFile(io.BytesIO(decoded))
    except Exception:
        return None, [], "Could not open this file as an Excel workbook."
    if len(xl.sheet_names) > MAX_WORKBOOK_SHEETS:
        return None, [], f"Workbooks are limited to {MAX_WORKBOOK_SHEETS} sheets."

    errors = []
    total_cells = 0
    for sheet in xl.sheet_names:
        frame = xl.parse(sheet)
        if len(frame) > MAX_WORKSHEET_ROWS or len(frame.columns) > MAX_WORKSHEET_COLUMNS:
            errors.append(f"Sheet '{sheet}' exceeds the worksheet size limit.")
            continue
        total_cells += len(frame) * len(frame.columns)
        if total_cells > MAX_WORKBOOK_CELLS:
            return None, [], f"Workbooks are limited to {MAX_WORKBOOK_CELLS:,} parsed cells."
        try:
            normalized, notes = normalize_surveillance_table(frame, date_convention)
        except ValueError as exc:
            errors.append(f"Sheet '{sheet}': {exc}")
            continue
        if not normalized.empty:
            normalized["source"] = "real"
            return normalized, [f"Imported tabular worksheet '{sheet}'.", *notes], None
    message = "No tabular worksheet had usable disease, cases, and date columns."
    if errors:
        message += " " + " ".join(errors[:3])
    return None, errors, message


def _load_xlsx(decoded: bytes, date_convention: str = "day-first"):
    """Returns (real_df, parse_notes, error_message)."""
    real_df, parse_notes = parse_surveillance_xlsx(decoded)
    if real_df is None or real_df.empty:
        tabular_df, tabular_notes, tabular_error = _load_tabular_xlsx(decoded, date_convention)
        if tabular_df is None or tabular_df.empty:
            msg = tabular_error or "No usable data found in this workbook."
            return None, parse_notes + tabular_notes, msg
        return tabular_df, tabular_notes, None
    real_df["source"] = "real"
    return real_df, parse_notes, None


def _build_success_status(filename: str, real_df: pd.DataFrame, combined: pd.DataFrame, all_notes: list) -> str:
    n_real = real_df["disease"].nunique()
    n_mock = combined.loc[combined["source"] == "mock", "disease"].nunique()

    header = (f"\u2705 {filename}: {n_real} real disease(s), {len(real_df):,} rows loaded"
              + (f", {n_mock} disease(s) backfilled with mock data" if n_mock else ""))

    issue_notes = [n for n in all_notes if not n.startswith(UPLOAD_INFO_PREFIXES)]
    info_notes = [n for n in all_notes if n.startswith(UPLOAD_INFO_PREFIXES)]

    status = header
    if issue_notes:
        status += "  \u26a0 " + " | ".join(issue_notes)
    if info_notes:
        status += "  \u2139 " + " | ".join(info_notes)
    return status


def _build_upload_summary(
    filename: str,
    real_df: pd.DataFrame,
    combined: pd.DataFrame,
    all_notes: list,
    *,
    uploaded: bool = True,
) -> dict:
    """Build the persisted, JSON-safe description of the data now in use.

    Real-disease metrics deliberately describe only rows actually supplied by
    the user, before mock backfill. This section verifies the upload rather than
    overstating what the file contained. Missing diseases describe their final
    generated mock series so every configured disease still has a visible row.
    """
    diseases = []
    real_names = set(real_df["disease"].unique()) if not real_df.empty else set()
    for disease in DISEASES:
        source = "real" if disease in real_names else "mock"
        source_df = real_df if source == "real" else combined
        disease_df = source_df[source_df["disease"] == disease]
        diseases.append({
            "name": disease,
            "source": source,
            "row_count": int(len(disease_df)),
            "year_min": int(disease_df["year"].min()) if not disease_df.empty else None,
            "year_max": int(disease_df["year"].max()) if not disease_df.empty else None,
        })

    # Overall coverage follows the same upload-verification rule as real rows.
    coverage_df = real_df if not real_df.empty else combined
    preview_df = coverage_df[["year", "month", "disease", "cases", "source"]].head(10)
    preview = [
        {
            "year": int(row.year),
            "month": int(row.month),
            "disease": str(row.disease),
            "cases": int(row.cases),
            "source": str(row.source),
        }
        for row in preview_df.itertuples(index=False)
    ]
    return {
        "success": True,
        "uploaded": uploaded,
        "filename": filename,
        "loaded_at": datetime.now(timezone.utc).isoformat(),
        "year_min": int(coverage_df["year"].min()) if not coverage_df.empty else None,
        "year_max": int(coverage_df["year"].max()) if not coverage_df.empty else None,
        "diseases": diseases,
        "warnings": list(all_notes),
        "preview": preview,
    }


def _build_failure_summary(filename: str, message: str) -> dict:
    return {
        "success": False,
        "uploaded": True,
        "filename": filename,
        "loaded_at": datetime.now(timezone.utc).isoformat(),
        "year_min": None,
        "year_max": None,
        "diseases": [],
        "warnings": [message],
        "preview": [],
    }


def _append_gap_notes(validation_notes: list, real_df: pd.DataFrame) -> list:
    gap_notes = find_date_range_gap_notes(real_df)
    if not gap_notes:
        return validation_notes
    clean_message = "No data-quality issues found in the uploaded data."
    return [note for note in validation_notes if note != clean_message] + gap_notes


@app.callback(
    Output("store-data", "data"),
    Output("upload-status", "children"),
    Output("store-upload-summary", "data"),
    Input("upload-csv", "contents"),
    State("upload-csv", "filename"),
    State("store-data", "data"),
    State("store-upload-summary", "data"),
    State("date-convention", "value"),
    prevent_initial_call=False,
)
def load_data(contents, filename, existing_store, existing_summary=None, date_convention="day-first"):
    if contents is None:
        # No new upload triggered this run (e.g. a page refresh). Don't clobber
        # data that already survived in this browser session -- only fall back
        # to fresh mock data if there's truly nothing there yet.
        if existing_store:
            if existing_summary:
                return no_update, "\U0001F504 Restored previously loaded data from this browser session (refresh-safe).", no_update
            try:
                restored = pd.read_json(io.StringIO(existing_store), orient="split")
                if "source" not in restored.columns:
                    restored["source"] = "real"
                restored_real = restored[restored["source"] == "real"].copy()
                summary = _build_upload_summary(
                    "Restored session data",
                    restored_real,
                    restored,
                    ["Upload summary was regenerated from the restored session data."],
                    uploaded=not restored_real.empty,
                )
            except Exception:
                logger.exception("could not regenerate upload summary from session data")
                summary = no_update
            return no_update, "\U0001F504 Restored previously loaded data from this browser session (refresh-safe).", summary
        logger.info("no existing session data -- generating fresh mock dataset")
        df = generate_fallback_data()
        summary = _build_upload_summary(
            "Built-in synthetic dataset",
            df.iloc[0:0].copy(),
            df,
            ["No upload yet; all tracked diseases use synthetic mock data."],
            uploaded=False,
        )
        return df.to_json(date_format="iso", orient="split"), "\U0001F4CA Using pre-loaded synthetic city-wide mock data", summary

    try:
        decoded = _decode_upload(contents)
        fname = (filename or "").lower()

        if fname.endswith(".xlsx"):
            real_df, parse_notes, error = _load_xlsx(decoded, date_convention)
        elif fname.endswith(".csv"):
            real_df, parse_notes, error = _load_csv(decoded, date_convention)
        else:
            message = f"Unsupported file type for '{filename}'. Please upload a .csv or .xlsx file."
            return no_update, f"\u274c {message}", _build_failure_summary(filename, message)

        if error:
            logger.warning("upload rejected for '%s': %s", filename, error)
            return no_update, f"\u274c {error}", _build_failure_summary(filename, error)

        real_df, validation_notes = validate_and_clean_disease_df(real_df)
        real_df["source"] = "real"
        validation_notes = _append_gap_notes(validation_notes, real_df)
        all_notes = parse_notes + validation_notes

        if real_df.empty:
            message = "No valid rows remained after validation. " + " ".join(all_notes)
            return no_update, "\u274c " + message, _build_failure_summary(filename, message)

        combined = combine_real_and_mock(real_df)
        status = _build_success_status(filename, real_df, combined, all_notes)
        summary = _build_upload_summary(filename, real_df, combined, all_notes)
        logger.info("loaded '%s': %s", filename, status)
        return combined.to_json(date_format="iso", orient="split"), status, summary

    except UploadRejectedError as e:
        logger.warning("upload rejected for '%s': %s", filename, e)
        return no_update, f"\u274c {e}", _build_failure_summary(filename, str(e))
    except UnicodeDecodeError:
        logger.exception("unexpected error reading '%s'", filename)
        message = "This file doesn't look like a valid CSV -- check that it's saved as plain text, not a different encoding or file format."
        return no_update, "\u274c " + message, _build_failure_summary(filename, message)
    except pd.errors.EmptyDataError:
        logger.exception("unexpected error reading '%s'", filename)
        message = "This file appears to be empty."
        return no_update, "\u274c " + message, _build_failure_summary(filename, message)
    except Exception:
        logger.exception("unexpected error reading '%s'", filename)
        message = "Something went wrong reading this file. Please check the format and try again."
        return no_update, "\u274c " + message, _build_failure_summary(filename, message)
