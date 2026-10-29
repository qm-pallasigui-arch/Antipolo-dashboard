import json
from ..forecasting.config import MODEL_NAME, MODEL_VERSION


def is_current(result):
    return (result.get('model_name') == MODEL_NAME and result.get('model_version') == MODEL_VERSION
            and result.get('forecast_status') == 'hybrid_completed'
            and ((result.get('is_prototype') is True and result.get('methodology_status') == 'provisional')
                 or (result.get('is_prototype') is False and result.get('methodology_status') == 'approved'))
            and result.get('model_metadata', {}).get('corrector') == 'XGBoost'
            and result.get('model_metadata', {}).get('corrector_applied') is True)


class ForecastRepository:
    def __init__(self, store):
        self.store = store

    def save(self, result):
        payload = json.dumps(result, allow_nan=False)
        with self.store.connect() as db:
            db.execute('''INSERT INTO forecasts(id,signature,block,status,payload,created_at) VALUES (?,?,?,?,?,?)
                ON CONFLICT(id) DO UPDATE SET status=excluded.status,payload=excluded.payload''',
                (result['forecast_run_id'], result['dataset_signature'], result['icd10_block'],
                 result['forecast_status'], payload, result['forecast_created_at']))
            if is_current(result):
                db.execute('DELETE FROM forecast_values WHERE forecast_run_id=?', (result['forecast_run_id'],))
                baseline = result.get('baseline_forecast', [None] * len(result['forecast_values']))
                db.executemany('INSERT INTO forecast_values VALUES (?,?,?,?)',
                    [(result['forecast_run_id'], row['month'], row['consultation_count'], base)
                     for row, base in zip(result['forecast_values'], baseline)])

    def completed(self, signature, *, final_only=False):
        with self.store.connect() as db:
            rows = db.execute("SELECT payload FROM forecasts WHERE signature=? AND status='hybrid_completed' ORDER BY created_at DESC", (signature,)).fetchall()
        mode = False if final_only else self.store.is_prototype
        return [result for row in rows if is_current(result := json.loads(row[0]))
                and result['is_prototype'] is mode
                and (not mode or result.get('configuration_signature') == self.store.model_config.signature)]

    def latest(self, signature, block):
        with self.store.connect() as db:
            rows = db.execute("SELECT payload FROM forecasts WHERE signature=? AND block=? AND status='hybrid_completed' ORDER BY created_at DESC", (signature, block))
            for row in rows:
                result = json.loads(row[0])
                mode = self.store.is_prototype
                if (is_current(result) and result['is_prototype'] is mode
                        and (not mode or result.get('configuration_signature') == self.store.model_config.signature)):
                    return result
        return None
