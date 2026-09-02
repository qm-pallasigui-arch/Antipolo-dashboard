"""
Synthetic mock data generator.

Deliberately isolated in its own module: this is a demo/fallback fixture, not
part of the real ingestion path. Nothing in modeling/ or callbacks/ should
need to know *how* mock data is generated -- they only ever see it already
merged into a real-shaped DataFrame via data.combine.combine_real_and_mock().
"""

import numpy as np
import pandas as pd

from dashboard.config import (
    DATA_START_YEAR, DATA_END_YEAR, DISEASES, DISEASE_WEIGHTS, SEASONAL_WEIGHTS,
)


def generate_fallback_data() -> pd.DataFrame:
    """Generates realistic mock monthly case data, Jan 2016 - Dec 2025 (120 months),
    city-wide (no school-level split). COVID closure (2020-2022) reduces cases ~65%."""
    np.random.seed(2025)
    records = []

    for year in range(DATA_START_YEAR, DATA_END_YEAR + 1):
        for month in range(1, 13):
            covid_factor = 0.32 if 2020 <= year <= 2022 else 1.0
            base_total = int(
                np.random.normal(110, 18) *
                SEASONAL_WEIGHTS[month - 1] *
                covid_factor
            )
            base_total = max(base_total, 5)

            for d_idx, disease in enumerate(DISEASES):
                raw = base_total * DISEASE_WEIGHTS[d_idx] * np.random.uniform(0.75, 1.30)
                cases = max(int(round(raw)), 0)
                if cases > 0:
                    records.append({
                        "year": year, "month": month,
                        "disease": disease, "cases": cases, "source": "mock",
                    })

    df = pd.DataFrame(records)
    df["date"] = pd.to_datetime(
        df["year"].astype(str) + "-" + df["month"].astype(str).str.zfill(2) + "-01"
    )
    return df
