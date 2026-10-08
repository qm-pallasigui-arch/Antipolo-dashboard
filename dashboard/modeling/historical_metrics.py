"""Compatibility scoring for the archived monthly selection protocol only."""
import numpy as np

from dashboard.modeling.metrics import compute_metrics as current_metrics


def compute_metrics(actual, predicted):
    metrics = current_metrics(actual, predicted)
    actual = np.asarray(actual, dtype=float)
    predicted = np.asarray(predicted, dtype=float)
    total = float(np.abs(actual).sum())
    metrics['wape'] = float(np.abs(actual - predicted).sum() / total * 100) if total else None
    return metrics
