"""Executable provisional workflow derived from the supplied tuning script."""
import numpy as np
import pandas as pd
from .adapter import modeling_frame, observed_frame
from .prophet_model import generate_prophet_base
from .features import generate_residual_training_data
from .xgboost_residual import fit_xgboost_residual_model, predict_residuals
from .evaluation import evaluate_prototype
from .config import PROTOTYPE_NOTICE


def combine_forecast(base, correction, config):
    corrected = np.clip(correction, -config.correction_clip, config.correction_clip) * config.correction_weight
    baseline = np.maximum(base, 0.0)
    hybrid = np.maximum(baseline + corrected, 0.0)
    if not np.isfinite(hybrid).all():
        raise ValueError('Nonfinite hybrid forecast.')
    return baseline.tolist(), hybrid.tolist(), corrected.tolist()


def forecast_components(frame, dates, config):
    fitted, base = generate_prophet_base(frame, dates, config)
    features, targets, residuals = generate_residual_training_data(frame, fitted, config)
    corrector = fit_xgboost_residual_model(features, targets, config)
    correction = predict_residuals(corrector, residuals, dates, config)
    baseline, hybrid, applied = combine_forecast(base, correction, config)
    return dict(baseline=baseline, hybrid=hybrid, correction=applied, residual_training_rows=len(targets))


class PrototypeWorkflow:
    def __init__(self, config):
        self.config = config

    def __call__(self, observations, dates):
        frame = modeling_frame(observations)
        output = forecast_components(frame, dates, self.config)
        evaluation = evaluate_prototype(frame, self.config, forecast_components)
        last_observed = observed_frame(frame).actual_timestamp.max().strftime('%Y-%m-%d')
        observed_dates = observed_frame(frame).actual_timestamp
        short_history_warning = (['Yearly seasonality uses less than two years of calendar span; prototype decomposition may be unstable.']
            if self.config.prophet.get('yearly_seasonality') and observed_dates.max() < observed_dates.min() + pd.DateOffset(years=2) else [])
        return dict(base_model='Prophet', residual_model='XGBoost', correction_status='completed',
            base_forecast=output['baseline'], correction=output['correction'], evaluation=evaluation,
            warnings=[PROTOTYPE_NOTICE, 'Residual training uses in-sample Prophet errors. Lag features preserve real calendar gaps as missing values.',
                      f'Last observed training month: {last_observed}. Any trailing gap is bridged by model predictions, never source observations.',
                      'Residual clipping and weighting are provisional. No uncertainty intervals are estimated.']
                     + short_history_warning
                     + ([f'Evaluation unavailable: {evaluation.get("reason", "unknown")}'] if evaluation['status'] != 'completed' else []),
            pipeline_metadata={'residual_method': self.config.residual_method,
                               'residual_training_rows': output['residual_training_rows']})
