"""
Guardrail applied to ANY uploaded long-format data (CSV or parsed XLSX) before
it enters the modeling pipeline. Split into one function per check so each
rule is independently testable.
"""

import numpy as np
import pandas as pd


def _normalize_disease_names(df: pd.DataFrame) -> tuple:
    """Validate arbitrary disease labels and canonicalize repeated spellings.

    The built-in diseases are sample data, not an upload whitelist. Labels are
    trimmed, internal whitespace is collapsed, and case-only variants use the
    first spelling seen in the upload. Blank or excessively long labels are
    rejected with an explicit note rather than disappearing silently.
    """
    notes = []
    df = df.copy()
    missing = df["disease"].isna()
    labels = df["disease"].fillna("").astype(str).str.replace(r"\s+", " ", regex=True).str.strip()
    invalid = missing | labels.eq("") | labels.str.len().gt(200)
    if invalid.any():
        raise ValueError("Blank or invalid disease name; labels must be 1-200 characters.")

    df = df.loc[~invalid].copy()
    labels = labels.loc[~invalid]
    keys = labels.str.casefold()
    canonical = {}
    normalized = []
    for key, label in zip(keys, labels):
        canonical.setdefault(key, label)
        normalized.append(canonical[key])
    df["disease"] = normalized
    return df, notes


def _coerce_numeric_cases(df: pd.DataFrame) -> tuple:
    """Reject invalid counts; never fabricate zeros or round observations."""
    df = df.copy()
    df["cases"] = pd.to_numeric(df["cases"], errors="coerce")
    invalid = ~np.isfinite(df["cases"]) | (df["cases"] < 0) | (df["cases"] % 1 != 0)
    if invalid.any():
        raise ValueError("Cases must be finite, nonnegative whole numbers; correct invalid observations before upload.")
    return df, []


def _validate_month_year_ranges(df: pd.DataFrame) -> tuple:
    """Reject invalid calendar fields before any count aggregation."""
    notes = []
    df = df.copy()
    df["month"] = pd.to_numeric(df["month"], errors="coerce")
    df["year"] = pd.to_numeric(df["year"], errors="coerce")

    bad_month = ~df["month"].between(1, 12) | (df["month"] % 1 != 0)
    bad_year = ~df["year"].between(1900, 2100) | (df["year"] % 1 != 0)
    n_bad = int((bad_month | bad_year).sum())
    if n_bad:
        raise ValueError("Invalid month or year: require whole month 1-12 and year 1900-2100.")

    return df[~(bad_month | bad_year)], notes


def _discard_duplicate_observations(df: pd.DataFrame) -> tuple:
    """Reject duplicate monthly observations without choosing a source."""
    notes = []
    duplicate_mask = df.duplicated(subset=["year", "month", "disease"], keep=False)
    n_duplicates = int(duplicate_mask.sum())
    if n_duplicates:
        raise ValueError("Duplicate year/month/disease observations require source reconciliation; no row was chosen or summed.")
    return df, notes


def find_date_range_gap_notes(df: pd.DataFrame) -> list[str]:
    """Report absent calendar months inside each real disease's observed span.

    This intentionally operates independently of duplicate detection: duplicate
    observations and missing months are different data-quality problems. A row
    whose case count is zero is still an observed month and is not a gap.
    """
    notes = []
    real_df = df[df.get("source", "real") == "real"] if "source" in df.columns else df
    for disease, disease_df in real_df.groupby("disease", sort=False):
        observed = pd.PeriodIndex.from_fields(
            year=disease_df["year"].astype(int),
            month=disease_df["month"].astype(int),
            freq="M",
        ).unique()
        if observed.empty:
            continue
        expected = pd.period_range(observed.min(), observed.max(), freq="M")
        missing_count = len(expected.difference(observed))
        if missing_count:
            notes.append(
                f"{disease}: missing data for {missing_count} month(s) between "
                f"{observed.min()} and {observed.max()}."
            )
    return notes


def validate_and_clean_disease_df(df: pd.DataFrame) -> tuple:
    """
    Runs the full validation chain: disease-label validation -> numeric coercion ->
    range checks. Returns (cleaned_df, validation_notes) -- notes are always
    returned, even when nothing needed fixing, so callers can show
    "no issues found" rather than an empty/ambiguous list.
    """
    all_notes = []

    df, notes = _normalize_disease_names(df)
    all_notes.extend(notes)
    if df.empty:
        all_notes.append("No rows had a usable disease name after validation.")
        return df, all_notes

    df, notes = _coerce_numeric_cases(df)
    all_notes.extend(notes)

    df, notes = _validate_month_year_ranges(df)
    all_notes.extend(notes)

    df, notes = _discard_duplicate_observations(df)
    all_notes.extend(notes)

    df["cases"] = df["cases"].round().astype(int)
    df["year"] = df["year"].astype(int)
    df["month"] = df["month"].astype(int)

    if not all_notes:
        all_notes.append("No data-quality issues found in the uploaded data.")

    return df.reset_index(drop=True), all_notes
