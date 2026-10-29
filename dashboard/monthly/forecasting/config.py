"""Central provisional settings. These are not approved Chapter 3 parameters."""
from dataclasses import asdict, dataclass, field
import hashlib
import json
import os
from pathlib import Path

MODEL_NAME = 'Prophet + XGBoost'
MODEL_VERSION = '2'
FORECAST_HORIZON_MONTHS = 12
CANDIDATE_BLOCKS = ('A00-A09', 'A15-A19', 'A80-A89', 'B00-B09', 'B25-B34', 'B85-B89', 'B90-B94')
METHOD_PENDING = ('Final thesis results require approved Chapter 3 methodology. '
                  'Provisional prototype forecasting is available when PROTOTYPE_MODE=true.')
PROTOTYPE_NOTICE = 'PROTOTYPE — provisional settings; not final thesis analytical results.'
RANKING_SCOPE = 'The Projected Top Five is limited to forecastable ICD-10 blocks represented in the supplied 2016–2025 DOH Top-Five dataset.'
READINESS_STATUSES = ('not_assessed', 'ready', 'not_ready', 'methodology_configuration_required')
FORECAST_STATUSES = ('running', 'hybrid_completed', 'prophet_only_fallback',
                    'xgboost_insufficient_history', 'xgboost_failed', 'prophet_failed', 'forecast_failed')


class MethodologyPending(ValueError):
    pass


@dataclass(frozen=True)
class PrototypeModelConfig:
    configuration_name: str = 'PROVISIONAL_MODEL_CONFIG'
    seed: int = 12345
    threads: int = 1
    lags: int = 12
    min_observations: int = 17
    min_residual_rows: int = 5
    residual_method: str = 'in_sample'
    evaluation_split: str = 'last_reported_year'
    mase_season_months: int = 12
    gap_handling: str = 'actual_dates_native_missing_lags'
    correction_clip: float = 1.0
    correction_weight: float = 0.1
    prophet: dict = field(default_factory=lambda: dict(yearly_seasonality=True,
        weekly_seasonality=False, daily_seasonality=False, seasonality_mode='additive', uncertainty_samples=0))
    xgboost: dict = field(default_factory=lambda: dict(max_depth=6, learning_rate=0.3,
        n_estimators=1000, subsample=0.9, colsample_bytree=0.9, reg_alpha=1.0, reg_lambda=1.0))

    def __post_init__(self):
        import math
        for name in ('seed', 'threads', 'lags', 'min_observations', 'min_residual_rows', 'mase_season_months'):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < (0 if name == 'seed' else 1):
                raise ValueError(f'Invalid prototype setting: {name}')
        for name in ('correction_clip', 'correction_weight'):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
                raise ValueError(f'Invalid prototype setting: {name}')
        if self.residual_method != 'in_sample' or self.evaluation_split != 'last_reported_year':
            raise ValueError('This prototype implements in-sample residuals and a generic last-reported-year split only.')
        if self.gap_handling != 'actual_dates_native_missing_lags':
            raise ValueError('Unsupported gap handling setting.')
        if self.prophet.get('uncertainty_samples') != 0:
            raise ValueError('Uncertainty intervals are not implemented in this prototype.')
        if 'n_jobs' in self.xgboost or 'random_state' in self.xgboost:
            raise ValueError('Configure CPU threads and seed through the dedicated settings.')

    def snapshot(self):
        return asdict(self)

    @property
    def signature(self):
        return hashlib.sha256(json.dumps(self.snapshot(), sort_keys=True, allow_nan=False).encode()).hexdigest()


def prototype_mode():
    value = os.environ.get('PROTOTYPE_MODE', 'true').lower()
    if value not in ('true', 'false'):
        raise ValueError('PROTOTYPE_MODE must be true or false.')
    return value == 'true'


def load_prototype_config():
    path = os.environ.get('PROTOTYPE_CONFIG_PATH')
    return PrototypeModelConfig(**json.loads(Path(path).read_text(encoding='utf-8'))) if path else PrototypeModelConfig()
