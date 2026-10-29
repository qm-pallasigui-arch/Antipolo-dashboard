"""Read-only local database inventory. Never outputs account or source payloads."""
import json
import sqlite3
from pathlib import Path

root = Path(__file__).resolve().parents[1]
path = root / '.monthly' / 'state.sqlite3'
output = root / 'docs' / 'reconciliation-20261029' / 'database-inventory.json'
result = {'database': '.monthly/state.sqlite3', 'mode': 'read_only', 'exists': path.exists()}
if path.exists():
    db = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)
    try:
        names = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        result['tables'] = []
        for name in names:
            quoted = '"' + name.replace('"', '""') + '"'
            columns = [dict(name=r[1], type=r[2]) for r in db.execute(f'PRAGMA table_info({quoted})')]
            result['tables'].append({'name': name, 'columns': columns, 'rows': db.execute(f'SELECT count(*) FROM {quoted}').fetchone()[0]})
        if 'forecasts' in names:
            result['forecast_status_counts'] = dict(db.execute('SELECT status,count(*) FROM forecasts GROUP BY status'))
    finally:
        db.close()
output.write_text(json.dumps(result, indent=2), encoding='utf-8')
print('Read-only database schema/count inventory saved; no records changed.')
