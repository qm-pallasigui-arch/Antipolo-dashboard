import json


class RankingRepository:
    def __init__(self, store):
        self.store = store

    def save(self, ranking, batch=None, *, finish_batch=False):
        with self.store.connect() as db:
            if batch is not None:
                from .batch_repository import BatchRepository
                db.execute('BEGIN IMMEDIATE')
                BatchRepository(self.store).check(db, batch, require_dataset=True)
            db.execute('INSERT INTO rankings(id,signature,payload,created_at) VALUES (?,?,?,?)',
                       (ranking['ranking_run_id'], ranking['dataset_signature'], json.dumps(ranking, allow_nan=False), ranking['generated_at']))
            if finish_batch:
                # Publishing a ranking and closing its batch must be atomic with cancellation.
                import time
                repo = BatchRepository(self.store)
                current = repo.check(db, batch, require_dataset=True)
                current.update(status='failed' if not ranking['rankings'] else 'partial' if ranking['failed_blocks'] else 'completed',
                               current=None, finished=time.time())
                repo._write(db, current)

    def latest(self, signature):
        with self.store.connect() as db:
            rows = db.execute('SELECT payload FROM rankings WHERE signature=? ORDER BY created_at DESC', (signature,)).fetchall()
        for row in rows:
            result = json.loads(row[0])
            if (result.get('is_prototype') is self.store.is_prototype
                    and result.get('methodology_status') == ('provisional' if self.store.is_prototype else 'approved')
                    and (not self.store.is_prototype or result.get('configuration_signature') == self.store.model_config.signature)):
                from .batch_repository import BatchRepository
                batch = BatchRepository(self.store).latest(signature)
                if batch and batch['id'] != result.get('forecast_run_group_id'):
                    result = dict(result)
                    result['warnings'] = [*result.get('warnings', []),
                        f"These rankings belong to an earlier batch. The latest batch is {batch['status']}; its results have not replaced this ranking."]
                return result
        return None
