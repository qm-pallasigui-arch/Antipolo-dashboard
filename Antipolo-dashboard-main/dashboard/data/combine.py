"""Finalizes a validated upload for storage by adding its monthly date."""

import pandas as pd

def prepare_uploaded_data(real_df: pd.DataFrame) -> pd.DataFrame:
    """Add a canonical date without mixing sample rows into an upload."""
    from dashboard.data.provenance import ensure_separate_population
    ensure_separate_population(real_df)
    combined = real_df.copy()
    for column in ("population", "case_classification", "source_dataset"):
        if column not in combined:
            combined[column] = "unknown"
    combined["date"] = pd.to_datetime(
        combined["year"].astype(str) + "-" + combined["month"].astype(str).str.zfill(2) + "-01"
    )
    return combined


# Compatibility for code importing the pre-generalization helper name.
combine_real_and_mock = prepare_uploaded_data
