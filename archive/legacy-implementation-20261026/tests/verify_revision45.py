"""Manual full-protocol verification on synthetic data; never research evidence."""
import json
from pathlib import Path
import sys
import time
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dashboard.weekly.data import validate
from dashboard.weekly.model import run
from dashboard.weekly.protocol import exploratory_configuration

if __name__ == '__main__':
    rng = np.random.default_rng(42)
    rows = [{'disease': 'Synthetic verification', 'year': 2020 + i // 52, 'morbidity_week': i % 52 + 1,
             'case_count': int(max(0, round(30 + 9 * np.sin(2 * np.pi * i / 52) + rng.normal(0, 3))))} for i in range(312)]
    data = validate(pd.DataFrame(rows), {'dataset_type': 'synthetic', 'reporting_status': 'complete',
                    'year_lengths': {str(y): 52 for y in range(2020, 2028)},
                    'provenance': 'Seeded synthetic verification only; invented calendar for fixture'})
    start = time.monotonic()
    result = run(data, 'Synthetic verification', exploratory_configuration())
    out = ROOT / 'evidence' / 'revision45'
    out.mkdir(exist_ok=True)
    (out / 'synthetic-full-protocol.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps({'seconds': time.monotonic() - start, 'hybrid_status': result['hybrid_status'],
                     'sarima_status': result['sarima_status'], 'metrics': result['metrics'],
                     'horizon_metrics': result.get('horizon_metrics'), 'failure_reason': result.get('failure_reason')}, indent=2), flush=True)
    assert len(result.get('sarima') or []) == 52
    assert len(result['diagnostics']['candidates']) == 16
    assert result['context'] == 'Synthetic / Demo Data'
