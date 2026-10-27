"""
(De)serialization for pipeline results so they survive round-tripping through
dcc.Store, which only holds JSON -- pandas Series with a DatetimeIndex aren't
JSON-native, so every Series field is converted to a plain {index, values}
dict and back.
"""

import pandas as pd

_RESULT_SERIES_KEYS = [
    "series", "sarima_fitted", "residuals", "nnar_fitted", "sarima_forecast",
    "hybrid_forecast", "final_forecast", "ci_lower", "ci_upper", "test_actual",
    "test_sarima_only", "test_hybrid", "test_seasonal_naive", "raw_sarima_forecast", "nnar_forecast",
]
_RESULT_SCALAR_KEYS = [
    "status", "provenance", "model_identification", "rolling_evaluation",
    "metrics", "sarima_only_metrics", "final_metrics", "selected_model",
    "baseline_metrics", "selection_metrics", "data_source", "model_tier",
    "interval_method", "evaluation_window", "selection_folds", "warnings_log",
    "selection_metric", "selection_threshold", "selection_tiers", "evaluation_tier",
]


def _series_to_dict(s: pd.Series) -> dict:
    return {
        "index": [str(i) for i in s.index],
        "values": [None if pd.isna(v) else float(v) for v in s.values],
        "name": s.name,
    }


def _dict_to_series(d: dict) -> pd.Series:
    return pd.Series(d["values"], index=pd.to_datetime(d["index"]), name=d.get("name"))


def serialize_pipeline_result(result: dict) -> dict:
    out = {k: _series_to_dict(result[k]) for k in _RESULT_SERIES_KEYS if k in result}
    for k in _RESULT_SCALAR_KEYS:
        out[k] = result.get(k)
    return out


def deserialize_pipeline_result(d: dict) -> dict:
    out = {k: _dict_to_series(d[k]) for k in _RESULT_SERIES_KEYS if k in d}
    for k in _RESULT_SCALAR_KEYS:
        out[k] = d.get(k)
    return out
