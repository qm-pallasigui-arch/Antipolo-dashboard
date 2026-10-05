from pathlib import Path
import json,sys,platform,importlib.metadata,hashlib
import pandas as pd
from dashboard.data.mock_data import generate_fallback_data
from dashboard.modeling.pipeline import run_hybrid_pipeline
from dashboard.modeling.serialization import serialize_pipeline_result
out={'code_sha256':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in Path('dashboard').rglob('*.py')},'python':platform.python_version(),'versions':{x:importlib.metadata.version(x) for x in ['numpy','pandas','scipy','statsmodels','scikit-learn','dash','plotly','pytest']},'results':[]}
real=pd.read_csv('reconciliation/source-monthly-independent.csv')
real['date']=pd.to_datetime(dict(year=real.year,month=real.month,day=1))
real['source']='real'
real['population']='all-age'
real['case_classification']='unknown'
real['source_dataset']='Antipolo_Disease_Surveillance_2016-2025.xlsx; SHA256 c8e90c7e040e0c5e5b4676bbe6e26485e6921054d89f684f4f3768ae43cb73ff'
real['coverage_status']='provisional week calendar; week 53 meaning unverified'

for kind,df in [('all_age',real),('synthetic',generate_fallback_data())]:
 for disease in df.disease.unique():
  try:
   r=run_hybrid_pipeline(df,disease)
   row={'dataset':kind,'disease':disease,'result':serialize_pipeline_result(r)}
   print(kind,disease,r['final_metrics'],flush=True)
  except Exception as e:
   row={'dataset':kind,'disease':disease,'error':str(e),'status':getattr(e,'status','error'),'diagnostics':getattr(e,'diagnostics',{})}
   print(row,flush=True)
  out['results'].append(row)
  Path(sys.argv[1]).write_text(json.dumps(out,indent=2,default=str))
