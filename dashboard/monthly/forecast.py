"""Replaceable research pipeline. No model is approved or registered by default."""
import json
import math
import secrets
from typing import Protocol

from .domain import DataError, OBSERVED, evaluate_forecast_eligibility, now
from .store import require_admin

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


class ModelEngine(Protocol):
    """A researcher-approved implementation owns every unresolved method choice.

    prepare_series receives all 120 calendar months, including classified nulls.
    Evaluation must return a JSON-safe mapping with evaluation_method,
    evaluation_period, metric_results (horizons 1,3,6,12), warnings, and
    selection_reason. No production implementation is supplied in this revision.
    """
    identifier: str

    def prepare_series(self, observations): ...
    def fit_candidate_model(self, series): ...
    def evaluate_candidate_model(self, candidates, series): ...
    def compare_candidate_models(self, evaluation): ...
    def select_supported_model(self, comparison): ...
    def refit_selected_model(self, selected, series): ...
    def generate_forecast(self, fitted, horizon): ...


class ForecastService:
    def __init__(self, store, registry=None):
        self.store = store
        self.registry = registry or {}

    def run(self, user, code, horizon, engine_id=None):
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
                      engine_identifier=engine.identifier, forecast_status='running', warnings=[])
        self._save(result)
        run_metadata = dict(result)
        self.store.audit(user['id'], 'forecast_execution', run_id)
        try:
            series = engine.prepare_series(observations)
            candidates = engine.fit_candidate_model(series)
            evaluation = engine.evaluate_candidate_model(candidates, series)
            comparison = engine.compare_candidate_models(evaluation)
            selected = engine.select_supported_model(comparison)
            fitted = engine.refit_selected_model(selected, series)
            values = engine.generate_forecast(fitted, horizon)
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
            for key in ('evaluation_method', 'evaluation_period', 'metric_results', 'selection_reason'):
                if key not in evaluation:
                    raise ValueError(f'Engine evaluation is missing {key}.')
            if not {str(k) for k in evaluation['metric_results']} >= {'1', '3', '6', '12'}:
                raise ValueError('Evaluation must report horizons 1, 3, 6 and 12 (unavailable metrics may be null).')
            result.update(candidate_models=list(candidates), selected_model=str(selected),
                          evaluation_method=evaluation['evaluation_method'], evaluation_period=evaluation['evaluation_period'],
                          metric_results=evaluation['metric_results'], model_selection_reason=evaluation['selection_reason'],
                          forecast_values=forecast_values, forecast_status='completed', warnings=evaluation.get('warnings', []))
            # Validate serialization before replacing the persisted running record.
            json.dumps(result, allow_nan=False)
            self._save(result)
            self.store.notify('forecast', 'Forecast completed', f'{code}: {horizon} months ahead.', 'Forecasting', record_id=run_id)
            return result
        except Exception as exc:
            result = run_metadata
            result.update(forecast_status='failed', error='Forecast run failed; previous valid results are preserved.')
            self._save(result)
            self.store.notify('forecast', 'Forecast run failed', result['error'], 'Forecasting', role='admin', record_id=run_id, severity='error')
            raise ModelFailure(result['error']) from exc

    def _save(self, result):
        with self.store.connect() as db:
            db.execute('INSERT OR REPLACE INTO forecasts VALUES (?,?,?,?,?,?)', (result['forecast_run_id'],
                result['dataset_signature'], result['icd10_block'], result['forecast_status'], json.dumps(result, allow_nan=False), result['forecast_created_at']))
