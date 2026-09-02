"""Combines validated real data with synthetic mock backfill for any tracked
disease the real upload didn't cover."""

import pandas as pd

from dashboard.config import DISEASES
from dashboard.data.mock_data import generate_fallback_data


def combine_real_and_mock(real_df: pd.DataFrame) -> pd.DataFrame:
    """Any tracked disease absent from the uploaded real data is backfilled with
    synthetic mock data (clearly flagged via the 'source' column) so all 7
    diseases remain forecastable even from a partial real upload."""
    real_diseases = set(real_df["disease"].unique())
    missing = [d for d in DISEASES if d not in real_diseases]

    parts = [real_df[["year", "month", "disease", "cases", "source"]]]
    if missing:
        mock_full = generate_fallback_data()
        mock_part = mock_full[mock_full["disease"].isin(missing)][["year", "month", "disease", "cases", "source"]]
        parts.append(mock_part)

    combined = pd.concat(parts, ignore_index=True)
    combined["date"] = pd.to_datetime(
        combined["year"].astype(str) + "-" + combined["month"].astype(str).str.zfill(2) + "-01"
    )
    return combined
