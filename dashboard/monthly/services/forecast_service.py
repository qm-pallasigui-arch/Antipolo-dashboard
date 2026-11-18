"""Fixed-architecture execution with descriptive data quality and explicit model outcomes."""
import secrets
import logging
import threading
import time

from ..repositories.batch_repository import BatchRepository, BatchInterrupted

from ..domain import DataError, now
from ..forecasting.config import MODEL_NAME, MODEL_VERSION, METHOD_PENDING, MethodologyPending, PROTOTYPE_NOTICE, CANDIDATE_BLOCKS
from ..forecasting.hybrid import HybridModel
from ..forecasting.pipeline import PrototypeWorkflow
from ..forecasting.errors import ForecastComponentError
from ..data_quality import coverage_summary
from ..repositories.forecast_repository import ForecastRepository
from ..repositories.ranking_repository import RankingRepository
from ..store import require_admin
from .ranking_service import rank_forecasts


class ModelFailure(RuntimeError):
    def __init__(self, message, status='forecast_failed'):
        super().__init__(message)
        self.status = status


class ForecastService:
    def __init__(self, store, model=None):
        self.store = store
        self.model = model or HybridModel(PrototypeWorkflow(store.model_config) if store.is_prototype else None)
        self.repository = ForecastRepository(store)

    @property
    def configured(self):
        return self.store.is_prototype and self.model.workflow is not None

    def generate_forecast(self, user, block_id, horizon=12):
        return self.run(user, block_id, horizon)

    def run(self, user, code, horizon=12, *, group_id=None, batch=None):
        require_admin(user)
        if isinstance(horizon, bool) or not isinstance(horizon, int) or horizon != 12:
            raise DataError('The finalized forecast horizon is twelve months.')
        dataset = self.store.active()
        if not dataset:
            raise DataError('Activate a validated monthly dataset first.')
        if batch and dataset['dataset_signature'] != batch['signature']:
            raise BatchInterrupted('Dataset changed during forecasting. Generate forecasts again.')
        rows = [r for r in dataset['observations'] if r['icd10_block'] == code]
        if code not in CANDIDATE_BLOCKS:
            raise DataError('Unknown study block.')
        data_quality = coverage_summary(rows)
        if not self.configured:
            raise MethodologyPending(METHOD_PENDING)
        y, m = max((r['year'], r['month_number']) for r in dataset['observations'])
        dates = [f'{(y * 12 + m + i) // 12:04}-{(y * 12 + m + i) % 12 + 1:02}-01' for i in range(12)]
        cutoff = max((f'{r["year"]}-{r["month_number"]:02}' for r in rows if r['consultation_count'] is not None), default=None)
        result = dict(forecast_run_id=secrets.token_hex(16), forecast_run_group_id=group_id or secrets.token_hex(16),
            dataset_id=dataset['dataset_id'], dataset_signature=dataset['dataset_signature'], icd10_block=code,
            training_cutoff=cutoff, forecast_origin=f'{y}-{m:02}', forecast_created_at=now(), generated_at=now(),
            forecast_horizon_months=12, horizon_months=12, forecast_status='running', status='running', model_status='running',
            model_label=MODEL_NAME + ' (Prototype)', model_name=MODEL_NAME, model_version=MODEL_VERSION,
            prototype=True, is_prototype=True, methodology_status='provisional',
            configuration=self.store.model_config.snapshot(), configuration_signature=self.store.model_config.signature,
            data_quality=data_quality, n_observations=data_quality['reported_month_count'], warnings=[PROTOTYPE_NOTICE])
        self.repository.save(result, batch=batch)
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
            result.update(forecast_status='hybrid_completed', status='hybrid_completed', model_status='hybrid_completed',
                          projected_total=sum(v['consultation_count'] for v in result['forecast_values']))
            self.repository.save(result, batch=batch)
        except BatchInterrupted:
            raise
        except Exception as exc:
            logging.getLogger(__name__).exception('Forecast failed: group=%s block=%s', result['forecast_run_group_id'], code)
            status = exc.status if isinstance(exc, ForecastComponentError) else 'forecast_failed'
            result.update(forecast_status=status, status=status, model_status=status,
                          error=f'{status}: ' + (str(exc) if isinstance(exc, ForecastComponentError) else 'Forecast failed. Check server logs using the batch reference.') + ' No substitute algorithm was used.')
            result.pop('forecast_values', None)
            result.pop('selected_output', None)
            self.repository.save(result, batch=batch)
            self.store.notify('forecast', 'Prototype forecast failed', result['error'], 'Forecasting', role='admin', severity='error', record_id=result['forecast_run_id'])
            raise ModelFailure(result['error'], status) from exc
        self.store.notify('forecast', 'Prototype forecast completed', f'{MODEL_NAME} completed for {code}. {PROTOTYPE_NOTICE}', 'Forecasting', record_id=result['forecast_run_id'])
        return result

    def submit(self, user):
        require_admin(user)
        if not self.configured:
            raise MethodologyPending(METHOD_PENDING)
        dataset = self.store.active()
        if not dataset:
            raise DataError('Activate a validated monthly dataset first.')
        batch = BatchRepository(self.store).claim(dataset['dataset_signature'], queued=True, actor_id=user['id'])
        self.store.audit(user['id'], 'forecast_queued', batch['id'])
        return batch

    def run_all(self, user, *, batch=None):
        require_admin(user)
        if not self.configured:
            raise MethodologyPending(METHOD_PENDING)
        dataset = self.store.active()
        if not dataset:
            raise DataError('Activate a validated monthly dataset first.')
        batches = BatchRepository(self.store)
        batch = batch or batches.claim(dataset['dataset_signature'])
        stopped = threading.Event()
        def heartbeat():
            while not stopped.wait(20):
                try:
                    batches.update(batch)
                except Exception:
                    logging.getLogger(__name__).exception('Forecast heartbeat stopped: %s', batch['id'])
                    return
        worker = threading.Thread(target=heartbeat, daemon=True)
        worker.start()
        try:
            result = self._run_all(user, batch)
            return result
        except Exception:
            logging.getLogger(__name__).exception('Forecast batch failed: %s', batch['id'])
            try:
                batches.update(batch, status='failed', current=None, finished=time.time(),
                               error='Batch could not finish. Check server logs using the batch reference, then retry.')
            except BatchInterrupted:
                pass
            raise
        finally:
            stopped.set()
            worker.join(timeout=2)

    def _run_all(self, user, batch):
        require_admin(user)
        if not self.configured:
            raise MethodologyPending(METHOD_PENDING)
        dataset = self.store.active()
        if not dataset:
            raise DataError('Activate a validated monthly dataset first.')
        group_id, results, failures = batch['id'], [], []
        batches = BatchRepository(self.store)
        statuses = {}
        for code in CANDIDATE_BLOCKS:
            active = self.store.active()
            if not active or active['dataset_signature'] != batch['signature']:
                raise DataError('Dataset changed during forecasting. Start a new forecast group.')
            batches.update(batch, current=code)
            try:
                results.append(self.run(user, code, group_id=group_id, batch=batch))
                statuses[code] = results[-1]['forecast_status']
            except ModelFailure as exc:
                failures.append(code)
                statuses[code] = exc.status
            batches.update(batch, completed=len(results) + len(failures), successes=len(results),
                           failures={key: value for key, value in statuses.items() if key in failures})
        ranking = rank_forecasts(results, dataset['dataset_signature'], group_id)
        ranking.update(is_prototype=True, methodology_status='provisional', configuration_signature=self.store.model_config.signature)
        ranking['failed_blocks'] = failures
        ranking['attempted_blocks'] = list(CANDIDATE_BLOCKS)
        ranking['model_statuses'] = statuses
        if failures:
            ranking['warnings'].append('Some block forecasts failed; this ranking is incomplete.')
        RankingRepository(self.store).save(ranking, batch=batch, finish_batch=True)
        self.store.notify('forecast', 'Prototype projected rankings prepared', f'{len(results)} valid blocks ranked. {PROTOTYPE_NOTICE}', 'Forecasting', record_id=ranking['ranking_run_id'])
        return ranking
