"""Population boundaries are enforced before any temporal aggregation."""


def ensure_separate_population(frame):
    """Require independent datasets for distinct populations/case definitions."""
    for column in ("population", "case_classification", "source"):
        if column in frame:
            values = frame[column].fillna("unknown").astype(str).str.strip().str.casefold()
            values = values.replace("", "unknown")
            if values.nunique() > 1:
                raise ValueError(
                    f"Mixed {column} values are not allowed in one evaluation. "
                    "Upload each population, case classification, and source separately."
                )


def provenance_label(frame):
    parts = []
    for column, label in (("population", "Population"), ("case_classification", "Case classification")):
        values = frame[column].dropna().astype(str).unique() if column in frame else []
        parts.append(f"{label}: {', '.join(values) if len(values) else 'unknown'}")
    return "; ".join(parts)
