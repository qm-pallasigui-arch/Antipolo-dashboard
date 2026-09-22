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

import pandas as pd
from dash import Input, Output, State, no_update
from dashboard.config import MAX_CSV_ROWS, MAX_UPLOAD_BYTES

from dashboard.app_instance import app  # noqa: F401  (ensures `callback` binds to our app)
from dashboard.data.mock_data import generate_fallback_data
from dashboard.data.xlsx_parser import parse_surveillance_xlsx
from dashboard.data.validation import validate_and_clean_disease_df
from dashboard.data.combine import combine_real_and_mock
from dashboard.logging_config import get_logger

logger = get_logger(__name__)


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


def _load_csv(decoded: bytes):
    """Returns (real_df, parse_notes, error_message). Exactly one of
    (real_df, error_message) is non-None."""
    df = pd.read_csv(io.StringIO(decoded.decode("utf-8")), nrows=MAX_CSV_ROWS + 1)
    if len(df) > MAX_CSV_ROWS:
        return None, [], f"CSV files are limited to {MAX_CSV_ROWS:,} rows."
    df.columns = df.columns.astype(str).str.strip().str.lower()
    required = {"year", "month", "disease", "cases"}
    missing = required - set(df.columns)
    if missing:
        return None, [], f"Missing columns: {', '.join(missing)}. Required: year, month, disease, cases."
    real_df = df[["year", "month", "disease", "cases"]].copy()
    real_df["source"] = "real"
    return real_df, [], None


def _load_xlsx(decoded: bytes):
    """Returns (real_df, parse_notes, error_message)."""
    real_df, parse_notes = parse_surveillance_xlsx(decoded)
    if real_df is None or real_df.empty:
        msg = " ".join(parse_notes) if parse_notes else "No usable data found in this workbook."
        return None, parse_notes, msg
    real_df["source"] = "real"
    return real_df, parse_notes, None


def _build_success_status(filename: str, real_df: pd.DataFrame, combined: pd.DataFrame, all_notes: list) -> str:
    n_real = real_df["disease"].nunique()
    n_mock = combined.loc[combined["source"] == "mock", "disease"].nunique()

    header = (f"\u2705 {filename}: {n_real} real disease(s), {len(real_df):,} rows loaded"
              + (f", {n_mock} disease(s) backfilled with mock data" if n_mock else ""))

    issue_notes = [n for n in all_notes if not n.startswith("No data-quality issues") and not n.startswith("Matched sheet")]
    info_notes = [n for n in all_notes if n.startswith("Matched sheet")]

    status = header
    if issue_notes:
        status += "  \u26a0 " + " | ".join(issue_notes)
    if info_notes:
        status += "  \u2139 " + " | ".join(info_notes)
    return status


@app.callback(
    Output("store-data", "data"),
    Output("upload-status", "children"),
    Input("upload-csv", "contents"),
    State("upload-csv", "filename"),
    State("store-data", "data"),
    prevent_initial_call=False,
)
def load_data(contents, filename, existing_store):
    if contents is None:
        # No new upload triggered this run (e.g. a page refresh). Don't clobber
        # data that already survived in this browser session -- only fall back
        # to fresh mock data if there's truly nothing there yet.
        if existing_store:
            return no_update, "\U0001F504 Restored previously loaded data from this browser session (refresh-safe)."
        logger.info("no existing session data -- generating fresh mock dataset")
        df = generate_fallback_data()
        return df.to_json(date_format="iso", orient="split"), "\U0001F4CA Using pre-loaded synthetic city-wide mock data"

    try:
        decoded = _decode_upload(contents)
        fname = (filename or "").lower()

        if fname.endswith(".xlsx"):
            real_df, parse_notes, error = _load_xlsx(decoded)
        elif fname.endswith(".csv"):
            real_df, parse_notes, error = _load_csv(decoded)
        else:
            return no_update, f"\u274c Unsupported file type for '{filename}'. Please upload a .csv or .xlsx file."

        if error:
            logger.warning("upload rejected for '%s': %s", filename, error)
            return no_update, f"\u274c {error}"

        real_df, validation_notes = validate_and_clean_disease_df(real_df)
        real_df["source"] = "real"
        all_notes = parse_notes + validation_notes

        if real_df.empty:
            return no_update, "\u274c No valid rows remained after validation. " + " ".join(all_notes)

        combined = combine_real_and_mock(real_df)
        status = _build_success_status(filename, real_df, combined, all_notes)
        logger.info("loaded '%s': %s", filename, status)
        return combined.to_json(date_format="iso", orient="split"), status

    except UploadRejectedError as e:
        logger.warning("upload rejected for '%s': %s", filename, e)
        return no_update, f"\u274c {e}"
    except UnicodeDecodeError:
        logger.exception("unexpected error reading '%s'", filename)
        return no_update, "\u274c This file doesn't look like a valid CSV -- check that it's saved as plain text, not a different encoding or file format."
    except pd.errors.EmptyDataError:
        logger.exception("unexpected error reading '%s'", filename)
        return no_update, "\u274c This file appears to be empty."
    except Exception:
        logger.exception("unexpected error reading '%s'", filename)
        return no_update, "\u274c Something went wrong reading this file. Please check the format and try again."
