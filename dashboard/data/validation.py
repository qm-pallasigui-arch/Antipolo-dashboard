"""
Guardrail applied to ANY uploaded long-format data (CSV or parsed XLSX) before
it enters the modeling pipeline. Split into one function per check so each
rule is independently testable.
"""

import pandas as pd

from dashboard.config import DISEASES


def _filter_known_diseases(df: pd.DataFrame) -> tuple:
    """Case/whitespace-insensitive whitelist match, auto-corrected to the
    canonical spelling. Returns (filtered_df, notes)."""
    notes = []
    canonical = {d.strip().lower(): d for d in DISEASES}
    df = df.copy()
    df["_disease_key"] = df["disease"].astype(str).str.strip().str.lower()
    matched_mask = df["_disease_key"].isin(canonical)

    if (~matched_mask).any():
        bad_names = df.loc[~matched_mask, "disease"].value_counts()
        detail = "; ".join(f"'{name}' ({count} row(s))" for name, count in bad_names.items())
        notes.append(
            f"Ignored unrecognized disease name(s): {detail}. Tracked diseases are: {', '.join(DISEASES)}."
        )

    df = df[matched_mask].copy()
    df["disease"] = df["_disease_key"].map(canonical)
    return df.drop(columns=["_disease_key"]), notes


def _coerce_numeric_cases(df: pd.DataFrame) -> tuple:
    """Drops non-numeric 'cases' values, clips negative ones to 0. Returns (df, notes)."""
    notes = []
    df = df.copy()
    df["cases"] = pd.to_numeric(df["cases"], errors="coerce")

    n_bad = int(df["cases"].isna().sum())
    if n_bad:
        notes.append(f"Dropped {n_bad} row(s) with a non-numeric 'cases' value.")
    df = df.dropna(subset=["cases"])

    n_negative = int((df["cases"] < 0).sum())
    if n_negative:
        notes.append(f"Clipped {n_negative} negative 'cases' value(s) to 0.")
        df["cases"] = df["cases"].clip(lower=0)

    return df, notes


def _validate_month_year_ranges(df: pd.DataFrame) -> tuple:
    """Drops rows with month outside 1-12 or year outside a plausible range. Returns (df, notes)."""
    notes = []
    df = df.copy()
    df["month"] = pd.to_numeric(df["month"], errors="coerce")
    df["year"] = pd.to_numeric(df["year"], errors="coerce")

    bad_month = ~df["month"].between(1, 12)
    bad_year = ~df["year"].between(1900, 2100)
    n_bad = int((bad_month | bad_year).sum())
    if n_bad:
        notes.append(f"Dropped {n_bad} row(s) with an invalid month (must be 1-12) or implausible year.")

    return df[~(bad_month | bad_year)], notes


def validate_and_clean_disease_df(df: pd.DataFrame) -> tuple:
    """
    Runs the full validation chain: disease whitelist -> numeric coercion ->
    range checks. Returns (cleaned_df, validation_notes) -- notes are always
    returned, even when nothing needed fixing, so callers can show
    "no issues found" rather than an empty/ambiguous list.
    """
    all_notes = []

    df, notes = _filter_known_diseases(df)
    all_notes.extend(notes)
    if df.empty:
        all_notes.append("No rows matched a tracked disease name after validation.")
        return df, all_notes

    df, notes = _coerce_numeric_cases(df)
    all_notes.extend(notes)

    df, notes = _validate_month_year_ranges(df)
    all_notes.extend(notes)

    df["cases"] = df["cases"].round().astype(int)
    df["year"] = df["year"].astype(int)
    df["month"] = df["month"].astype(int)

    if not all_notes:
        all_notes.append("No data-quality issues found in the uploaded data.")

    return df.reset_index(drop=True), all_notes
