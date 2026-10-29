"""Independent verification and report generation from saved prediction arrays."""
from pathlib import Path
import json,math
import numpy as np
original=json.loads(Path('reconciliation/original-evaluation.json').read_text(encoding='utf-8'))
revised=json.loads(Path('reconciliation/revised-evaluation.json').read_text(encoding='utf-8'))
assert len(original['results'])==10 and len(revised['results'])==10, 'Wait for complete evaluations'
checks=[]
def score(a,p):
 a=np.asarray(a,float);p=np.asarray(p,float);e=np.abs(a-p);nonzero=a!=0
 return dict(mae=float(e.mean()),rmse=float(np.sqrt(np.mean((a-p)**2))),mape=float(100*np.mean(e[nonzero]/np.abs(a[nonzero]))) if nonzero.any() else None,wape=float(100*e.sum()/np.abs(a).sum()) if np.abs(a).sum() else None)
def verify_metrics(actual,pred,reported):
 expected=score(actual,pred)
 for key,value in expected.items():
  assert value is None and reported[key] is None or value is not None and math.isclose(value,reported[key],rel_tol=1e-10,abs_tol=1e-10),(key,value,reported[key])
for version,data in [('original',original),('revised',revised)]:
 for row in data['results']:
  assert 'result' in row,row
  r=row['result']; actual=r['test_actual']['values']
  for key,metric in [('test_hybrid','metrics'),('test_sarima_only','sarima_only_metrics')]:
   assert r[key]['index']==r['test_actual']['index']
   verify_metrics(actual,r[key]['values'],r[metric])
  naive=r['series']['values'][-24:-12]
  verify_metrics(actual,naive,r['baseline_metrics'])
  chosen='test_hybrid' if r['selected_model']=='hybrid' else 'test_sarima_only'
  verify_metrics(actual,r[chosen]['values'],r['final_metrics'])
  if version=='revised':
   assert r['selected_model']=='hybrid'
   assert r['final_forecast']==r['hybrid_forecast']
   assert np.allclose(r['final_forecast']['values'],np.maximum(0,np.array(r['raw_sarima_forecast']['values'])+r['nnar_forecast']['values']))
   ident=r['model_identification']
   for report,end in zip(ident['folds']+[ident['evaluation'],ident['production']],['2022-12','2023-12','2024-12','2025-12']):
    assert report['training_end'].startswith(end)
    assert len(report['candidates'])==12
    assert report['selected']['converged']
    assert report['selected']['order']==report['best_sarima_benchmark']['order']
    assert report['selected']['seasonal_order']==report['best_sarima_benchmark']['seasonal_order']
   errors=[]
   for fold in r['rolling_evaluation']:
    for method in ['hybrid','sarima_only','seasonal_naive']:
     verify_metrics(fold['actual'],fold[method],fold[method+'_metrics'])
    errors.extend(np.abs(np.array(fold['actual'])-fold['hybrid']))
   errors.extend(np.abs(np.array(actual)-r['test_hybrid']['values']))
   radius=max(errors)
   assert np.allclose(r['ci_upper']['values'],np.array(r['final_forecast']['values'])+radius)
   assert np.allclose(r['ci_lower']['values'],np.maximum(0,np.array(r['final_forecast']['values'])-radius))
   if row['dataset']=='all_age':assert r['provenance']['population']=='all-age'
  checks.append({'version':version,'dataset':row['dataset'],'disease':row['disease'],'verified':True})
Path('reconciliation/numerical-verification.json').write_text(json.dumps(checks,indent=2),encoding='utf-8')
lines=['# Model evaluation - 27 September 2026','','Freshly executed original-working-tree and revised-model runs are separate below. All-age records are not ages 5-19 confirmed-case evidence. No eligible age-specific extract was supplied. Synthetic results are separate demonstrations, never pooled with real observations.','','The revised hybrid is mandatory even where it loses. The revised hybrid is worse than its SARIMA-only benchmark for Leptospirosis and Measles-Rubella; it also loses to seasonal naive for those two categories. Dengue only narrowly beats seasonal naive. No general superiority is established.','','## Artifacts and reproduction','','- `reconciliation/original-evaluation.json`: fresh baseline arrays/metrics from initial uncommitted working tree, prior to edits.','- `reconciliation/revised-evaluation.json`: current arrays, every SARIMA candidate, ADF/ACF/PACF, neural settings, warnings, rolling folds, holdout and production.','- `reconciliation/revised-evaluation-initial.json`: intermediate revised run retained; not the final result.','- `reconciliation/evaluate.py`: current evaluator; `python -m reconciliation.evaluate reconciliation/revised-evaluation.json`.','- `reconciliation/verify_evaluation.py`: independent array arithmetic, alignment, component sum, split boundaries, and error-band verification.','- `reconciliation/numerical-verification.json`: actual verification outcomes.','- Initial code/data are recoverable in baseline ZIP. `reconciliation/reproduce_baseline.py` reconstructs the original evaluation against an extracted snapshot; that added wrapper was not separately rerun. Do not run historical evidence scripts against revised imports and overwrite old outputs.','','All ten series have 120 months, January2016-December2025. Earlier diagnostic evaluations are2023 and2024; final holdout2025; production2026. Search runs within each training window. Prior human exposure to2025 means algorithmic exclusion does not establish a pristine confirmatory holdout. A future prospective validation should be considered by the adviser.','','## Preserved historical reported values','','These are prior handoff findings, not revised output: Dengue25.17%, Leptospirosis67.08%, category then called Measles162.58% selected-model WAPE; naive34.90%,55.86%,50.00%. Fresh baseline results below independently reproduce their rounded values.']
for version,data in [('Original implementation',original),('Revised mandatory hybrid',revised)]:
 for dataset in ['all_age','synthetic']:
  lines+=['',f'## {version}: {dataset}','','| Disease | Method | MAE | RMSE | MAPE % | WAPE % | Nonzero MAPE months |','|---|---|---:|---:|---:|---:|---:|']
  for row in data['results']:
   if row['dataset']!=dataset:continue
   r=row['result']
   for method,key in [('Hybrid','metrics'),('SARIMA-only','sarima_only_metrics'),('Seasonal naive','baseline_metrics')]:
    m=r[key]
    lines.append(f"| {row['disease']} | {method}{' (primary)' if (method=='Hybrid' and r['selected_model']=='hybrid') or (method=='SARIMA-only' and r['selected_model']=='sarima_only') else ''} | {m['mae']:.4f} | {m['rmse']:.4f} | {m['mape']:.4f} | {m['wape']:.4f} | {m['mape_n']}/{m['n']} |")
lines+=['','## Selected revised configurations','','Each disease/window performs its own12-candidate search. AIC and residual diagnostics are training diagnostics, not accuracy claims.','','| Dataset | Disease | 2023 fold | 2024 fold | 2025 holdout | Full-history production |','|---|---|---|---|---|---|']
for row in revised['results']:
 r=row['result'];i=r['model_identification']
 config=lambda d:f"{tuple(d['selected']['order'])}{tuple(d['selected']['seasonal_order'])}"
 lines.append('| '+' | '.join([row['dataset'],row['disease']]+[config(d) for d in i['folds']+[i['evaluation'],i['production']]])+' |')
lines+=['','## Interpretation and formulas','','MAE is mean absolute error; RMSE is square root of mean squared error; MAPE averages absolute relative error only for nonzero actuals; WAPE divides total absolute error by total absolute actuals. Percentage metrics multiply by100. Undefined denominator returns null, never a perfect score. All methods use identical holdout dates.','','The hybrid adds the untruncated SARIMA mean and neural residual prediction before clipping to zero. SARIMA-only is separately clipped. Its independent benchmark uses the best valid AIC candidate, even if another candidate is needed for a feasible neural component. No neural rejection occurred in these40 evaluated/production windows, so the benchmark and hybrid base orders coincide.','','Revised runs include hybrid_success and hybrid_with_warnings; inspect warnings and per-candidate rejections rather than interpreting success as adequate model fit. Finite NNAR results with a convergence warning remain explicitly warned results, not evidence of convergence. The residual autocorrelation warnings and particularly large Measles-Rubella error require critical review, not post-hoc tuning on2025.','','The shaded range uses the largest of36 prior absolute hybrid errors. It is descriptive, uses holdout errors after scoring, and is not a calibrated95% prediction interval.','','Original and revised code use different SARIMA identification and residual initialization policies. The before/after comparison evaluates the full authorized change; it does not isolate a causal benefit of mandatory architecture. Original fitted environments are recorded in both JSONs and environment-freeze.txt. Repository pins were not reinstalled or validated.']
Path('docs/archive/MODEL_EVALUATION.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(f'PASS: {len(checks)} version/dataset/series evaluations independently verified; report written.')
