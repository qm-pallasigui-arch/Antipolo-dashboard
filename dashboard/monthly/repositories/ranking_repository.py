import json


class RankingRepository:
    def __init__(self, store):
        self.store = store

    def save(self, ranking):
        with self.store.connect() as db:
            db.execute('INSERT INTO rankings(id,signature,payload,created_at) VALUES (?,?,?,?)',
                       (ranking['ranking_run_id'], ranking['dataset_signature'], json.dumps(ranking, allow_nan=False), ranking['generated_at']))

    def latest(self, signature):
        with self.store.connect() as db:
            rows = db.execute('SELECT payload FROM rankings WHERE signature=? ORDER BY created_at DESC', (signature,))
            for row in rows:
                result = json.loads(row[0])
                if (result.get('is_prototype') is self.store.is_prototype
                        and result.get('methodology_status') == ('provisional' if self.store.is_prototype else 'approved')
                        and (not self.store.is_prototype or result.get('configuration_signature') == self.store.model_config.signature)):
                    return result
        return None
