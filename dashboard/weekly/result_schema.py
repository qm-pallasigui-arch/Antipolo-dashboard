"""Normalize older session results without changing predictions or source data."""

METRIC_FIELDS = frozenset(('mae', 'rmse', 'mape', 'mape_n', 'mape_median_actual', 'mape_p10_actual', 'n'))


def current_result(value):
    """Copy nested results, retaining only supported fields in metric records."""
    if isinstance(value, dict):
        is_metric = bool({'mae', 'rmse', 'mape', 'wape'}.intersection(value)) and not any(
            key in value for key in ('records', 'metadata', 'configuration'))
        return {key: current_result(item) for key, item in value.items()
                if not is_metric or key in METRIC_FIELDS}
    if isinstance(value, list):
        return [current_result(item) for item in value]
    return value
