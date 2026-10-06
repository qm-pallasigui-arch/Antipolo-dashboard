"""Read-only modeling investigation. Run: python -m evidence.investigate"""
import hashlib
import json
from pathlib import Path
import platform
import importlib.metadata

import numpy as np

from dashboard.callbacks.data_callbacks import _load_xlsx
from dashboard.data.validation import validate_and_clean_disease_df
from dashboard.data.combine import prepare_uploaded_data
from dashboard.data.mock_data import generate_fallback_data
from dashboard.modeling.pipeline import run_hybrid_pipeline, _run_backtest_leg
from dashboard.modeling.sarima import run_arima
from dashboard.modeling.nnar import run_nnar
from dashboard.config import HYBRID_MIN_WAPE_GAIN_PP


def wape(actual, predicted):
    a, p = np.asarray(actual), np.asarray(predicted)
    return float(100 * np.abs(a-p).sum()/np.abs(a).sum()) if np.abs(a).sum() else None


def main():
    path = Path(r'C:/Users/redlo/Downloads/Antipolo_Disease_Surveillance_2016-2025.xlsx')
    raw = path.read_bytes()
    real, notes, error = _load_xlsx(raw)
    assert error is None, error
    real, validation = validate_and_clean_disease_df(real)
    real = prepare_uploaded_data(real)
    real.to_csv('evidence/real-monthly.csv', index=False)
    output = {'source': str(path), 'sha256': hashlib.sha256(raw).hexdigest(),
              'parse_notes': notes + validation, 'default_threshold': HYBRID_MIN_WAPE_GAIN_PP,
              'python': platform.python_version(),
              'versions': {p: importlib.metadata.version(p) for p in ['numpy','pandas','scipy','statsmodels','scikit-learn']},
              'sample': [], 'real': []}
    for kind, frame in [('sample', generate_fallback_data()), ('real', real)]:
        for disease in frame.disease.unique():
            r = run_hybrid_pipeline(frame, disease)
            s = r['series']
            train, actual = s.iloc[:-12], s.iloc[-12:]
            selected = r['test_hybrid'] if r['selected_model'] == 'hybrid' else r['test_sarima_only']
            naive = train.iloc[-12:].to_numpy()
            assert np.isclose(wape(actual, selected), r['final_metrics']['wape'])
            assert np.isclose(wape(actual, naive), r['baseline_metrics']['wape'])
            sm = r['selection_metrics']
            gain = sm['sarima_only']['wape'] - sm['hybrid']['wape']
            row = dict(disease=disease, months=len(s), start=str(s.index.min().date()),
                       end=str(s.index.max().date()), selected=r['selected_model'],
                       selected_wape=r['final_metrics']['wape'], naive_wape=r['baseline_metrics']['wape'],
                       sarima_wape=r['sarima_only_metrics']['wape'], hybrid_wape=r['metrics']['wape'],
                       selection_metrics=sm, gain_pp=gain,
                       sensitivity={str(t): 'hybrid' if gain >= t and gain > 0 else 'sarima_only' for t in [0,0.5,1.0,2.0]},
                       evaluation_tier=r['evaluation_tier'], selection_tiers=r['selection_tiers'],
                       warnings=r['warnings_log'], actual=actual.tolist(), naive=naive.tolist(),
                       selected_prediction=selected.tolist(), yearly_totals=s.groupby(s.index.year).sum().to_dict())
            if kind == 'sample':
                fitted, fc, _, _, tier, _ = run_arima(train, forecast_steps=12)
                nnfit, nnfc, _ = run_nnar((train-fitted).dropna(), forecast_steps=12, forecast_index=fc.index)
                # Exclude 24 initialization months; compare both training fits on identical dates.
                idx = train.index[24:].intersection(nnfit.index)
                row['train_sarima_wape'] = wape(train.loc[idx], fitted.loc[idx].clip(lower=0))
                row['train_hybrid_wape'] = wape(train.loc[idx], (fitted.loc[idx]+nnfit.loc[idx]).clip(lower=0))
                row['holdout_nnar_mean_abs_adjustment'] = float(nnfc.abs().mean())
                row['window_checks'] = []
                for months in [36,60,108]:
                    leg = _run_backtest_leg(s.iloc[-(months+12):],12)
                    row['window_checks'].append(dict(train_months=months, sarima=leg['sarima_only_metrics']['wape'],
                                                    hybrid=leg['metrics']['wape'], naive=leg['seasonal_naive_metrics']['wape'], tier=leg['tier']))
                row['earlier_windows'] = []
                for end in [96,108]:
                    leg = _run_backtest_leg(s.iloc[:end],12)
                    row['earlier_windows'].append(dict(year=int(leg['test'].index[0].year),
                        sarima=leg['sarima_only_metrics']['wape'],hybrid=leg['metrics']['wape'],naive=leg['seasonal_naive_metrics']['wape']))
                row['lag12_corr'] = float(s.autocorr(12))
            output[kind].append(row)
            Path('evidence/investigation.json').write_text(json.dumps(output,indent=2), encoding='utf-8')
            print(f"{kind}: {disease}: selected={row['selected']} WAPE={row['selected_wape']:.4f}; naive={row['naive_wape']:.4f}",flush=True)
    assert HYBRID_MIN_WAPE_GAIN_PP == 1.0


if __name__ == '__main__':
    main()
