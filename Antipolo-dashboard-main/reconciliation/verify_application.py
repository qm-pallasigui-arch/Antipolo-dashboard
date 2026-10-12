from pathlib import Path
import json,hashlib
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import app
from dashboard.modeling.serialization import deserialize_pipeline_result
from dashboard.callbacks.view_callbacks import _build_model_diagnostics,_build_forecast_export,_build_hybrid_metric_cards
from dashboard.charts.figures import fig_hybrid_forecast,fig_backtest,fig_residual_diag
from plotly.utils import PlotlyJSONEncoder
client=app.server.test_client()
checks={}
for route in ['/','/healthz','/_dash-layout','/_dash-dependencies']:
 response=client.get(route);assert response.status_code==200,(route,response.status_code)
 checks[route]={'status':response.status_code,'bytes':len(response.data)}
results=json.loads(Path('reconciliation/revised-evaluation.json').read_text())
for row in results['results']:
 if row['dataset']!='all_age':continue
 raw=row['result'];r=deserialize_pipeline_result(raw)
 _build_model_diagnostics(r);_build_hybrid_metric_cards(r)
 export=_build_forecast_export(raw,row['disease'])
 assert len(export)==132 and export['test_hybrid'].notna().sum()==12
 assert export['nnar_forecast'].notna().sum()==12
 assert set(export.population)=={'all-age'}
 export.to_csv('reconciliation/export-'+row['disease'].lower()+'.csv',index=False)
 figures=[fig_hybrid_forecast(r,[2016,2025]),fig_backtest(r),fig_residual_diag(r)]
 checks[row['disease']]={'csv_rows':len(export),'forecast_rows':int(export['nnar_forecast'].notna().sum()),'plot_trace_names':[[t.name for t in fig.data] for fig in figures]}
 Path('reconciliation/figures-'+row['disease'].lower()+'.json').write_text(json.dumps([f.to_plotly_json() for f in figures],cls=PlotlyJSONEncoder),encoding='utf-8')
Path('reconciliation/application-verification.json').write_text(json.dumps(checks,indent=2),encoding='utf-8')
print('PASS: HTTP routes, real-data components, three CSV exports and plot trace binding; browser visual rendering not verified.')
