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
    "test_sarima_only", "test_hybrid",
]
_RESULT_SCALAR_KEYS = [
    "metrics", "sarima_only_metrics", "final_metrics", "selected_model",
    "data_source", "model_tier", "warnings_log",
]


def _series_to_dict(s: pd.Series) -> dict:
    return {
        "index": [str(i) for i in s.index],
        "values": [None if pd.isna(v) else float(v) for v in s.values],
    }


def _dict_to_series(d: dict) -> pd.Series:
    return pd.Series(d["values"], index=pd.to_datetime(d["index"]))


def serialize_pipeline_result(result: dict) -> dict:
    out = {k: _series_to_dict(result[k]) for k in _RESULT_SERIES_KEYS}
    for k in _RESULT_SCALAR_KEYS:
        out[k] = result[k]
    return out


def deserialize_pipeline_result(d: dict) -> dict:
    out = {k: _dict_to_series(d[k]) for k in _RESULT_SERIES_KEYS}
    for k in _RESULT_SCALAR_KEYS:
        out[k] = d[k]
    return out
