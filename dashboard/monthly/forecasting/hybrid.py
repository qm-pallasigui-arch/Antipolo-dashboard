"""Fixed hybrid composition. An approved training workflow must be supplied explicitly."""
import math
from .config import MODEL_NAME, MODEL_VERSION, METHOD_PENDING, MethodologyPending
from .errors import ForecastComponentError


class HybridModel:
    identifier = 'prophet_xgboost'

    def __init__(self, workflow=None):
        self.workflow = workflow

    def generate(self, observations, dates):
        if self.workflow is None:
            raise MethodologyPending(METHOD_PENDING)
        # The workflow owns approved chronological folds, features and fitting settings.
        result = self.workflow(observations, dates)
        if result.get('base_model') != 'Prophet' or result.get('residual_model') != 'XGBoost':
            raise ValueError('Only the finalized Prophet + XGBoost architecture is accepted.')
        if result.get('correction_status') != 'completed':
            raise ForecastComponentError('xgboost_failed', 'XGBoost correction did not complete; no hybrid forecast is available.')
        base, correction = result['base_forecast'], result['correction']
        if len(base) != len(dates) or len(correction) != len(dates):
            raise ValueError('Both model components must cover every forecast month.')
        if not all(not isinstance(v, bool) and isinstance(v, (float, int)) and math.isfinite(v) for v in [*base, *correction]):
            raise ValueError('Both model components must return finite numeric values.')
        values = [max(0.0, a + b) for a, b in zip(base, correction)]
        if not all(math.isfinite(v) for v in values):
            raise ValueError('Combined forecast is nonfinite.')
        return dict(model_label=MODEL_NAME, model_name=MODEL_NAME, model_version=MODEL_VERSION,
                    selected_output={'forecast': values},
                    baseline_forecast=base,
                    model_metadata={'base_model': 'Prophet', 'corrector': 'XGBoost', 'corrector_applied': True},
                    pipeline_metadata=result.get('pipeline_metadata', {}),
                    evaluation=result.get('evaluation', {}), warnings=result.get('warnings', []))
