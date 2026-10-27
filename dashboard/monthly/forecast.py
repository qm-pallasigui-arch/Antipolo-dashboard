"""Eligibility-gated forecast service. The default engine is PROTOTYPE ONLY."""
import json
import math
import secrets
from typing import Protocol

from .domain import DataError, OBSERVED, evaluate_forecast_eligibility, now
from .store import require_admin
from .forecasting.prototype_adapter import PrototypeForecastAdapter, PROTOTYPE_DISCLAIMER

METHOD_PENDING = '[TO FINALIZE: forecasting methodology]'
# TODO THESIS-METHOD: finalize candidate models and hybrid/ensemble design.
# TODO THESIS-METHOD: finalize selection rule, metrics and chronological validation.
# TODO THESIS-METHOD: finalize treatment of 2020/2022 during model fitting.
# TODO THESIS-METHOD: finalize uncertainty interval method.


class NotEligible(DataError):
    pass


class MethodologyPending(DataError):
    pass


class ModelFailure(RuntimeError):
    pass


class ForecastAdapter(Protocol):
    """Model-independent replacement boundary, including evaluation and metadata."""
    identifier: str
    is_prototype: bool

    def generate(self, observations, horizon): ...


class ForecastService:
    def __init__(self, store, registry=None):
        self.store = store
        self.registry = {'prototype': PrototypeForecastAdapter()} if registry is None else registry

    def generate_forecast(self, user, block_id, horizon=12, engine_id=None):
        return self.run(user, block_id, horizon, engine_id)

    def run(self, user, code, horizon, engine_id=None):
        # TODO THESIS-METHOD:
        # This forecasting implementation is for prototype/dashboard integration only.
        # The final thesis forecasting algorithm, candidate models, evaluation design,
        # and model-selection rule are not yet approved.
        require_admin(user)
        if isinstance(horizon, bool) or not isinstance(horizon, int) or not 1 <= horizon <= 12:
            raise DataError('Forecast horizon must be an integer from 1 to 12 months.')
        dataset = self.store.active()
        if not dataset:
            raise DataError('Activate a validated monthly dataset first.')
        observations = [r for r in dataset['observations'] if r['icd10_block'] == code]
        eligibility = evaluate_forecast_eligibility(observations)
        if not eligibility['eligible']:
            raise NotEligible(eligibility['reason'])
        if engine_id is None and len(self.registry) == 1:
            engine_id = next(iter(self.registry))
        engine = self.registry.get(engine_id)
        if engine is None:
            raise MethodologyPending(METHOD_PENDING + ' — no approved model engine is installed.')
        run_id = secrets.token_hex(16)
        cutoff = max(f'{r["year"]}-{r["month_number"]:02}' for r in observations if r['observation_status'] in OBSERVED)
        result = dict(forecast_run_id=run_id, dataset_signature=dataset['dataset_signature'], icd10_block=code,
                      training_cutoff=cutoff, forecast_created_at=now(), forecast_horizon_months=horizon,
                      engine_identifier=engine.identifier, forecast_status='running', warnings=[],
                      prototype=bool(getattr(engine, 'is_prototype', False)),
                      is_prototype=bool(getattr(engine, 'is_prototype', False)))
        result.update(model_label='Prototype Forecast' if result['prototype'] else 'Forecast',
                      status='running', n_observations=eligibility['reported_month_count'],
                      horizon_months=horizon,
                      warnings=[PROTOTYPE_DISCLAIMER] if result['prototype'] else [])
        self._save(result)
        run_metadata = dict(result)
        self.store.audit(user['id'], 'forecast_execution', run_id)
        try:
            normalized = engine.generate(observations, horizon)
            values = normalized['selected_output']['forecast']
            result.update({k: normalized[k] for k in (
                'model_label', 'n_observations', 'horizon_months', 'selected_output',
                'model_metadata', 'evaluation', 'warnings')})
            if len(values) != horizon:
                raise ValueError('Engine returned an incorrect horizon.')
            forecast_values = []
            y, m = map(int, cutoff.split('-'))
            for ahead, value in enumerate(values, 1):
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
                    raise ValueError('Engine returned an invalid forecasted consultation count.')
                offset = y * 12 + m - 1 + ahead
                forecast_values.append(dict(month=f'{offset // 12}-{offset % 12 + 1:02}', consultation_count=value,
                                            observation_status='forecast', horizon_months=ahead))
            result.update(forecast_values=forecast_values, forecast_status='completed', status='completed',
                          model_status='prototype_available' if result['prototype'] else 'final_available')
            # Validate serialization before replacing the persisted running record.
            json.dumps(result, allow_nan=False)
            self._save(result)
            label = 'Prototype forecast' if result['prototype'] else 'Forecast'
            self.store.notify('forecast', label + ' completed', f'{label} completed for {code}.', 'Forecasting', record_id=run_id)
            return result
        except Exception as exc:
            result = run_metadata
            label = 'Prototype forecast' if result['prototype'] else 'Forecast'
            detail = ' Prototype engine unavailable: install icd_forecast and its dependencies.' if isinstance(exc.__cause__, ImportError) else ''
            result.update(forecast_status='failed', status='failed', model_status='failed',
                          error=f'{label} generation failed for {code}. Previous valid results are preserved.' + detail)
            self._save(result)
            self.store.notify('forecast', label + ' generation failed', result['error'], 'Forecasting', role='admin', record_id=run_id, severity='error')
            raise ModelFailure(result['error']) from exc

    def _save(self, result):
        with self.store.connect() as db:
            db.execute('INSERT OR REPLACE INTO forecasts VALUES (?,?,?,?,?,?)', (result['forecast_run_id'],
                result['dataset_signature'], result['icd10_block'], result['forecast_status'], json.dumps(result, allow_nan=False), result['forecast_created_at']))
