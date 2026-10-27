"""Translate experimental inference into the dashboard's model-independent contract."""
from ..domain import OBSERVED

PROTOTYPE_DISCLAIMER = (
    'This forecast is generated using the current prototype model and is intended for '
    'system-development and testing purposes. The final thesis forecasting methodology '
    'is still under evaluation.'
)
EVALUATION_DISCLAIMER = (
    'Evaluation metric shown is part of the prototype implementation and may change '
    'after final forecasting methodology is approved.'
)


class PrototypeForecastAdapter:
    identifier = 'prototype'
    is_prototype = True

    def __init__(self, inference=None):
        self.inference = inference

    def generate(self, observations, horizon):
        # TODO THESIS-METHOD:
        # This forecasting implementation is for prototype/dashboard integration only.
        # The final thesis forecasting algorithm, candidate models, evaluation design,
        # and model-selection rule are not yet approved.
        inference = self.inference
        if inference is None:
            try:
                from .icd_inference import forecast_series
            except ImportError as exc:
                raise RuntimeError('Prototype engine unavailable: install the supplied icd_forecast module and its dependencies.') from exc
            inference = forecast_series
        rows = sorted((r for r in observations if r['observation_status'] in OBSERVED),
                      key=lambda r: (r['year'], r['month_number']))
        values = [r['consultation_count'] for r in rows]
        raw = inference(values, h=horizon)
        result = self.normalize(raw, len(values), horizon)
        result['warnings'].append(
            'Prototype input uses reported months in chronological order, omitting unavailable '
            '2020/2022 months without imputation. This compresses calendar gaps; final treatment is not approved.')
        return result

    @staticmethod
    def normalize(raw, n_observations, horizon):
        if raw['n_obs'] != n_observations or raw['h'] != horizon:
            raise ValueError('Prototype output does not match the supplied series or horizon.')
        hybrid = raw.get('hybrid') or {}
        applied = bool(hybrid and hybrid.get('lambda', 0) != 0
                       and not hybrid.get('abstained', True) and not hybrid.get('reason'))
        values = (hybrid if applied else raw['prophet'])['forecast']
        warnings = [PROTOTYPE_DISCLAIMER, EVALUATION_DISCLAIMER]
        if hybrid and not applied:
            warnings.append('Residual correction not applied in this prototype run.')
        if hybrid.get('reason'):
            warnings.append('Residual corrector failed; the base prototype forecast was retained.')
        learners = {'rf': 'Random Forest', 'nnar': 'NNAR', 'lgbm': 'LightGBM', 'svm': 'SVM'}
        return dict(prototype=True, is_prototype=True, model_label='Prototype Forecast',
                    n_observations=n_observations, horizon_months=horizon,
                    selected_output={'forecast': values},
                    model_metadata=dict(engine='prototype', base_model='Prophet',
                                        corrector=learners.get(hybrid.get('learner'), hybrid.get('learner')),
                                        corrector_applied=applied),
                    evaluation={'prototype_cv_mae': hybrid.get('cv_mae') if applied else hybrid.get('cv_mae_nocorr')},
                    warnings=warnings)
