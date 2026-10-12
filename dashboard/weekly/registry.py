"""Durable, versioned selections and performance; never serialized fitted models."""
import json
import os
from pathlib import Path
import sqlite3
from contextlib import contextmanager

from dashboard.weekly.data import digest


def canonical(value):
    """JSON/browser round trips turn 1.0 into 1; those are identical inputs."""
    if isinstance(value, dict):
        return {key: canonical(item) for key, item in value.items()}
    if isinstance(value, list):
        return [canonical(item) for item in value]
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def scope(dataset, disease, configuration, version):
    # Re-upload timestamps and confirmation audit events are not model inputs.
    metadata = {k: v for k, v in dataset['metadata'].items()
                if k not in ('uploaded_at', 'confirmed_at', 'date_extracted')}
    return digest(canonical({'records': [r for r in dataset['records'] if r['disease'] == disease],
                   'metadata': metadata, 'disease': disease,
                   'configuration': configuration, 'model_version': version}))


def compatibility(dataset, disease, configuration, version):
    fields = ('population', 'case_classification', 'location', 'source_system', 'dataset_type',
              'frequency', 'reporting_status', 'approved_diseases', 'weekly_protocol')
    records = [{key: row.get(key) for key in ('year', 'morbidity_week', 'case_count', *fields)}
               for row in dataset['records'] if row['disease'] == disease]
    return canonical({'disease': disease, 'model_version': version, 'configuration': configuration,
                      'metadata': {key: dataset['metadata'].get(key) for key in fields},
                      'year_lengths': dataset['metadata'].get('year_lengths', {}), 'records': records})


def operational_selection(dataset, disease, configuration, version):
    """Reuse a historical lock for strictly appended data, never corrected history."""
    exact = load(scope(dataset, disease, configuration, version))
    if exact:
        return exact
    current = compatibility(dataset, disease, configuration, version)
    with connection() as db:
        rows = db.execute('SELECT payload FROM selections ORDER BY rowid DESC').fetchall()
    for row in rows:
        selected = json.loads(row[0])
        previous = selected.get('compatibility')
        if not previous or any(current[k] != previous[k] for k in ('disease', 'model_version', 'configuration', 'metadata')):
            continue
        n = len(previous['records'])
        if (len(current['records']) > n and current['records'][:n] == previous['records']
                and all(current['year_lengths'].get(y) == length for y, length in previous['year_lengths'].items())):
            return selected
    return None


@contextmanager
def connection():
    path = Path(os.environ.get('WEEKLY_MODEL_STORE', '.weekly-models/registry.sqlite3'))
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=30)
    try:
        with db:
            db.execute('CREATE TABLE IF NOT EXISTS selections (scope TEXT PRIMARY KEY, payload TEXT NOT NULL)')
            yield db
    finally:
        db.close()


def load(key):
    with connection() as db:
        row = db.execute('SELECT payload FROM selections WHERE scope = ?', (key,)).fetchone()
    return json.loads(row[0]) if row else None


def save(key, selection):
    payload = json.dumps(selection, allow_nan=False)
    with connection() as db:
        db.execute('INSERT INTO selections VALUES (?, ?) ON CONFLICT(scope) DO UPDATE SET payload=excluded.payload',
                   (key, payload))
