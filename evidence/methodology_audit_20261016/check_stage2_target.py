"""Exercise the real stage2 function with cheap, perfect mocked forecasts.

AST loading avoids optional plotting dependencies and runs the unchanged
function bodies from the search script. No real disease data or fits are used.
"""
import ast
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import mean_squared_error

root = Path(__file__).resolve().parents[2]
source = ast.parse((root / 'SARIMANNAR/residual_search.py').read_text(encoding='utf-8'))
namespace = {'np': np, 'mean_squared_error': mean_squared_error,
             'log': lambda message: None, 'fit_baseline_one': None}
for node in source.body:
    if isinstance(node, ast.FunctionDef) and node.name in ('stage2', '_window_score', 'recurse'):
        exec(compile(ast.Module(body=[node], type_ignores=[]), 'residual_search.py', 'exec'), namespace)
namespace['_run_pool'] = lambda fn, jobs, n, label: [
    {'_base_val': [100.0, 100.0]} for job in jobs]
namespace['fit_nnar'] = lambda *args: (lambda rows: np.zeros(len(rows)))
config = {'nnar': {'validation_n': 2, 'validation_windows': 1,
                   'lags': [1], 'hidden': [1]}, 'sarima': {'maxiter': 1}}
train = pd.Series([100.0] * 8, index=pd.date_range('2020-01-01', periods=8, freq='W'))
candidate = {'order': [0, 0, 0], 'seasonal': [0, 0, 0, 0], '_resid': [0.0] * 8}
result = namespace['stage2']([candidate], train, config, 1)[0]
evidence = {'fixture': 'actual cases=100; SARIMA forecast=100; residual correction=0',
            'reported_baseline_rmse': result['baseline_val_rmse'],
            'reported_hybrid_rmse': result['hybrid_val_rmse'],
            'correct_case_forecast_rmse': 0.0,
            'wrong_target_reproduced': result['hybrid_val_rmse'] != 0.0}
print(json.dumps(evidence, indent=2))
assert evidence['wrong_target_reproduced'], 'The audited target defect is no longer reproduced.'
