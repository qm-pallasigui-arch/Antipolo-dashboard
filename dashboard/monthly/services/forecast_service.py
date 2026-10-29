"""Fixed-architecture execution with explicit readiness and failure states."""
import secrets

from ..domain import DataError, now
from ..forecasting.config import MODEL_NAME, MODEL_VERSION, METHOD_PENDING, MethodologyPending, PROTOTYPE_NOTICE
from ..forecasting.hybrid import HybridModel
from ..forecasting.pipeline import PrototypeWorkflow
from ..forecasting.errors import ForecastComponentError
from ..forecasting.readiness import assess
from ..repositories.forecast_repository import ForecastRepository
from ..repositories.ranking_repository import RankingRepository
from ..store import require_admin
from .ranking_service import rank_forecasts


class NotEligible(DataError):
    pass


class ModelFailure(RuntimeError):
    pass


class ForecastService:
    def __init__(self, store, model=None):
        self.store = store
        self.model = model or HybridModel(PrototypeWorkflow(store.model_config) if store.is_prototype else None)
        self.repository = ForecastRepository(store)

    @property
    def configured(self):
        return self.store.is_prototype and self.store.readiness_policy is not None and self.model.workflow is not None

    def generate_forecast(self, user, block_id, horizon=12):
        return self.run(user, block_id, horizon)

    def run(self, user, code, horizon=12, *, group_id=None):
        require_admin(user)
        if isinstance(horizon, bool) or not isinstance(horizon, int) or horizon != 12:
            raise DataError('The finalized forecast horizon is twelve months.')
        dataset = self.store.active()
        if not dataset:
            raise DataError('Activate a validated monthly dataset first.')
        rows = [r for r in dataset['observations'] if r['icd10_block'] == code]
        readiness = assess(rows, self.store.readiness_policy)
        if not self.configured:
            raise MethodologyPending(METHOD_PENDING)
        if not readiness['eligible']:
            raise NotEligible(readiness['reason'])
        y, m = max((r['year'], r['month_number']) for r in dataset['observations'])
        dates = [f'{(y * 12 + m + i) // 12:04}-{(y * 12 + m + i) % 12 + 1:02}-01' for i in range(12)]
        cutoff = max(f'{r["year"]}-{r["month_number"]:02}' for r in rows if r['consultation_count'] is not None)
        result = dict(forecast_run_id=secrets.token_hex(16), forecast_run_group_id=group_id or secrets.token_hex(16),
            dataset_id=dataset['dataset_id'], dataset_signature=dataset['dataset_signature'], icd10_block=code,
            training_cutoff=cutoff, forecast_origin=f'{y}-{m:02}', forecast_created_at=now(), generated_at=now(),
            forecast_horizon_months=12, horizon_months=12, forecast_status='running', status='running',
            model_label=MODEL_NAME + ' (Prototype)', model_name=MODEL_NAME, model_version=MODEL_VERSION,
            prototype=True, is_prototype=True, methodology_status='provisional',
            configuration=self.store.model_config.snapshot(), configuration_signature=self.store.model_config.signature,
            readiness=readiness, n_observations=readiness['reported_month_count'], warnings=[PROTOTYPE_NOTICE])
        self.repository.save(result)
        self.store.audit(user['id'], 'forecast_execution', result['forecast_run_id'])
        try:
            output = self.model.generate(rows, dates)
            result.update(output)
            result['model_label'] = MODEL_NAME + ' (Prototype)'
            result['warnings'] = list(dict.fromkeys([PROTOTYPE_NOTICE, *result['warnings']]))
            result['forecast_values'] = [dict(month=date[:7], consultation_count=value, observation_status='forecast', horizon_months=i)
                for i, (date, value) in enumerate(zip(dates, output['selected_output']['forecast']), 1)]
            if len(result['forecast_values']) != 12:
                raise ValueError('A complete twelve-month forecast is required.')
            result.update(forecast_status='hybrid_completed', status='hybrid_completed', model_status='prototype_available',
                          projected_total=sum(v['consultation_count'] for v in result['forecast_values']))
            self.repository.save(result)
        except Exception as exc:
            status = exc.status if isinstance(exc, ForecastComponentError) else 'forecast_failed'
            result.update(forecast_status=status, status=status, model_status=status,
                          error=f'{status}: Hybrid forecasting failed. No substitute algorithm was used.')
            result.pop('forecast_values', None)
            result.pop('selected_output', None)
            self.repository.save(result)
            self.store.notify('forecast', 'Prototype forecast failed', result['error'], 'Forecasting', role='admin', severity='error')
            raise ModelFailure(result['error']) from exc
        self.store.notify('forecast', 'Prototype forecast completed', f'{MODEL_NAME} completed for {code}. {PROTOTYPE_NOTICE}', 'Forecasting', record_id=result['forecast_run_id'])
        return result

    def run_all(self, user):
        require_admin(user)
        if not self.configured:
            raise MethodologyPending(METHOD_PENDING)
        dataset = self.store.active()
        if not dataset:
            raise DataError('Activate a validated monthly dataset first.')
        group_id, results, failures = secrets.token_hex(16), [], []
        for block in dataset['blocks']:
            if not block['eligible']:
                continue
            if self.store.active()['dataset_signature'] != dataset['dataset_signature']:
                raise DataError('Dataset changed during forecasting. Start a new forecast group.')
            try:
                results.append(self.run(user, block['icd10_block'], group_id=group_id))
            except ModelFailure:
                failures.append(block['icd10_block'])
        ranking = rank_forecasts(results, dataset['dataset_signature'], group_id)
        ranking.update(is_prototype=True, methodology_status='provisional', configuration_signature=self.store.model_config.signature)
        ranking['failed_blocks'] = failures
        ranking['excluded_blocks'] = [b['icd10_block'] for b in dataset['blocks'] if not b['eligible']]
        if failures:
            ranking['warnings'].append('Some block forecasts failed; this ranking is incomplete.')
        RankingRepository(self.store).save(ranking)
        self.store.notify('forecast', 'Prototype projected rankings prepared', f'{len(results)} valid blocks ranked. {PROTOTYPE_NOTICE}', 'Forecasting', record_id=ranking['ranking_run_id'])
        return ranking
