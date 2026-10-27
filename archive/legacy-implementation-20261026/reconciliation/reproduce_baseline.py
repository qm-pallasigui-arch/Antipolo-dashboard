"""Re-run the preserved original working tree in the recorded environment.

Extract reconciliation/baseline.zip into a NEW directory first, then run:
python reconciliation/reproduce_baseline.py <extracted-directory> <output-json>
No current implementation modules are imported; output must be outside snapshot.
"""
from pathlib import Path
import sys,os,json,platform,importlib.metadata
snapshot=Path(sys.argv[1]).resolve()
output=Path(sys.argv[2]).resolve()
if not (snapshot/'dashboard/modeling/pipeline.py').is_file():
 raise SystemExit('Expected an extracted baseline snapshot directory.')
if snapshot==output or snapshot in output.parents:
 raise SystemExit('Write new output outside the preserved baseline directory.')
sys.path.insert(0,str(snapshot))
os.chdir(snapshot)
import pandas as pd
from dashboard.data.mock_data import generate_fallback_data
from dashboard.modeling.pipeline import run_hybrid_pipeline
from dashboard.modeling.serialization import serialize_pipeline_result
out={'python':platform.python_version(),'versions':{x:importlib.metadata.version(x) for x in ['numpy','pandas','scipy','statsmodels','scikit-learn','dash','plotly','pytest']},'results':[]}
real=pd.read_csv('evidence/real-monthly.csv',parse_dates=['date'])
for kind,df in [('all_age',real),('synthetic',generate_fallback_data())]:
 for disease in df.disease.unique():
  r=run_hybrid_pipeline(df,disease)
  out['results'].append({'dataset':kind,'disease':disease,'result':serialize_pipeline_result(r)})
  output.write_text(json.dumps(out,indent=2,default=str),encoding='utf-8')
  print(kind,disease,r['final_metrics'],flush=True)
