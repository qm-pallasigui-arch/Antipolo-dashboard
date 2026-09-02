"""Time-series shaping helpers shared by every model in modeling/."""

import pandas as pd

from dashboard.config import HOLDOUT_MONTHS


def get_monthly_series(df: pd.DataFrame, disease: str = "all") -> pd.Series:
    """Filters and returns a monthly total-case series, all months filled (0 if missing)."""
    dff = df.copy()
    if disease != "all":
        dff = dff[dff["disease"] == disease]
    return (
        dff.groupby("date")["cases"].sum()
        .asfreq("MS", fill_value=0).sort_index()
    )


def get_disease_series(df: pd.DataFrame, disease: str) -> pd.Series:
    """City-wide monthly series for one disease."""
    return get_monthly_series(df, disease=disease)


def train_test_split_series(series: pd.Series, holdout: int = HOLDOUT_MONTHS):
    """Fixed holdout split: everything except the last `holdout` months is training data."""
    if len(series) <= holdout:
        raise ValueError("Series is too short for the requested holdout window.")
    return series.iloc[:-holdout], series.iloc[-holdout:]
