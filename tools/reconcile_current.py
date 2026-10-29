"""One-time current-source reconciliation; all edits stay in the workspace."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def edit(name, transform):
    path = ROOT / name
    path.write_text(transform(path.read_text(encoding='utf-8')), encoding='utf-8')


def domain(text):
    start = text.index('def evaluate_forecast_eligibility(')
    end = text.index('\ndef canonical_columns', start)
    text = text[:start] + '''def evaluate_forecast_eligibility(block_data):
    return assess(block_data)

''' + text[end:]
    text = text.replace('import pandas as pd', 'import pandas as pd\nfrom .forecasting.config import CANDIDATE_BLOCKS\nfrom .forecasting.readiness import assess, refresh_dataset')
    text = text.replace("    return value\n\n\ndef integer", "    if value not in CANDIDATE_BLOCKS:\n        raise DataError(f'Block is outside the seven-block study pool: {value}')\n    return value\n\n\ndef integer")
    text = text.replace('not outbreak confirmation or future Top-5 rankings.', 'not outbreak confirmation. Projected rankings cover eligible represented blocks only.')
    text = text.replace('    return dataset\n\n\ndef parse_upload', '    return refresh_dataset(dataset)\n\n\ndef parse_upload')
    return text


def store(text):
    text = text.replace('from .domain import DataError, now, parse_upload', 'from .domain import DataError, now, parse_upload\nfrom .forecasting.readiness import refresh_dataset\nfrom .repositories.forecast_repository import ForecastRepository')
    text = text.replace('def __init__(self, path=None):', 'def __init__(self, path=None, readiness_policy=None):\n        self.readiness_policy = readiness_policy')
    text = text.replace("                CREATE TABLE IF NOT EXISTS reports", "                CREATE TABLE IF NOT EXISTS rankings(id TEXT PRIMARY KEY, signature TEXT, payload TEXT, created_at TEXT);\n                CREATE TABLE IF NOT EXISTS reports")
    text = text.replace('return json.loads(row[0]) if row else None', 'return refresh_dataset(json.loads(row[0]), self.readiness_policy) if row else None')
    text = text.replace("dataset = parse_upload(raw, Path(filename).name)", "dataset = refresh_dataset(parse_upload(raw, Path(filename).name), self.readiness_policy)")
    text = text.replace("dataset = json.loads(row[0])", "dataset = refresh_dataset(json.loads(row[0]), self.readiness_policy)")
    start = text.index('    def latest_forecast(')
    end = text.index('\n\ndef require_admin', start)
    text = text[:start] + '''    def latest_forecast(self, signature, block):
        return ForecastRepository(self).latest(signature, block)
''' + text[end:]
    return text.replace('Not eligible for forecasting', 'Forecast readiness pending or not met')


def views(text):
    text = text.replace('from .forecasting.prototype_adapter import EVALUATION_DISCLAIMER', 'from .repositories.ranking_repository import RankingRepository')
    text = text.replace('Review model selection, evaluation evidence and limitations.', 'Review hybrid model evaluation evidence and limitations.')
    text = text.replace('Forecast eligibility', 'Forecast readiness').replace('Not eligible for forecasting', 'Not ready for forecasting')
    text = text.replace('Based on reporting coverage', 'Based on the approved readiness policy')
    text = text.replace('A block must appear in all eight available annual Top-5 reports and contain 96 reported monthly observations to qualify for primary forecasting. Explicit zeros count.', 'All seven ICD-10 blocks enter readiness assessment. Coverage is descriptive; approved readiness thresholds have not yet been configured. Explicit zeros are observations.')
    text = text.replace('The prototype adapter supports 1–12 monthly forecasts when its inference dependencies are installed. The final thesis engine remains unimplemented.', 'The finalized architecture combines Prophet forecasts with XGBoost residual corrections over twelve future calendar months. Execution awaits approved methodology settings.')
    text = text.replace('TODO THESIS-METHOD: models; ensemble design; selection rule; metrics; chronological validation; treatment of 2020/2022 in fitting; uncertainty intervals.', 'Pending: readiness thresholds; chronological residual-training folds; features; tuning; evaluation metrics and splits; gap treatment; uncertainty intervals.')
    text = text.replace("latest = next(r for r in reversed(dataset['observations']) if r['icd10_block'] == code and r['consultation_count'] is not None)", "latest = next((r for r in reversed(dataset['observations']) if r['icd10_block'] == code and r['consultation_count'] is not None), None)")
    text = text.replace("return [*heading, block_summary(block, latest),", "return [*heading, ranking_view(store, dataset), block_summary(block, latest),")
    text = text.replace("'required_top5_year_count', 'reported_month_count', 'eligible', 'reason'", "'reported_month_count', 'readiness_status', 'reason'")
    text = text.replace("return [*heading, *summary, section('Primary forecast unavailable'", "return [*heading, ranking_view(store, dataset), *summary, section('Forecast unavailable'")
    text = text.replace('No prototype forecast available', 'No hybrid forecast available')
    text = text.replace('An administrator can generate a prototype forecast from this active dataset once the prototype dependencies are installed.', 'An administrator can generate forecasts once the approved methodology is configured.')
    text = text.replace('The service supports 1–12 monthly forecasts. Final thesis methodology remains open.', 'The model family is finalized as Prophet + XGBoost; the forecast horizon is twelve months.')
    start = text.index("        return [*heading, *summary, section('Prototype Mode'")
    end = text.index("    return [*heading, *summary, section('What your report includes'", start)
    text = text[:start] + '''        return [*heading, *summary, section('Prophet + XGBoost', [
            *forecast_warnings(forecast),
            disclosure('Chronological evaluation and run details', [html.Pre(json.dumps(details, indent=2))]),
            *([] if forecast else [message(METHOD_PENDING, 'warning')])])]
''' + text[end:]
    text += '''

def ranking_view(store, dataset):
    ranking = RankingRepository(store).latest(dataset['dataset_signature'])
    if not ranking:
        return section('Projected Top Five', [html.P('No comparable twelve-month forecast group is available.')])
    return section('Projected Top Five', [table(ranking['top_five']),
        *[message(w, 'warning') for w in ranking['warnings']],
        disclosure('All projected totals', [table(ranking['rankings']), html.P(ranking['tie_rule'])]),
        html.P('Ranking covers forecastable represented blocks only; it is not a citywide ranking of every disease.')])
'''
    return text


def reports(text):
    text = text.replace('from .forecasting.prototype_adapter import PROTOTYPE_DISCLAIMER', 'from .repositories.ranking_repository import RankingRepository')
    text = text.replace("(PROTOTYPE_DISCLAIMER if forecast.get('prototype') else 'Forecasted monthly consultations are estimates.')", "'Forecasted monthly consultations are estimates.'")
    text = text.replace("interpretation=LIMITATIONS, limitations=LIMITATIONS)", "interpretation=LIMITATIONS, limitations=LIMITATIONS,\n                  projected_ranking=RankingRepository(store).latest(dataset['dataset_signature']))")
    text = text.replace("+ '<h2>Interpretation and limitations</h2>'", "+ '<h2>Projected Top Five</h2>' + table((report.get('projected_ranking') or {}).get('top_five', []))\n            + '<h2>Interpretation and limitations</h2>'")
    return text


def ui(text):
    text = text.replace("options=[{'label': f'{n} month(s)', 'value': n} for n in range(1, 13)]", "options=[{'label': '12 months', 'value': 12}]")
    text = text.replace('Generate Prototype Forecast', 'Generate forecasts and rankings')
    text = text.replace("not block['eligible'] or not service.registry", "not service.configured")
    text = text.replace('result = service.generate_forecast(user, code, horizon)', 'result = service.run_all(user)')
    text = text.replace("text = f'{result[\"model_label\"]} completed for {code}.'", "text = f'{len(result[\"rankings\"])} valid blocks ranked over twelve months.'")
    return text


edit('dashboard/monthly/domain.py', domain)
edit('dashboard/monthly/store.py', store)
edit('dashboard/monthly/views.py', views)
edit('dashboard/monthly/reports.py', reports)
edit('dashboard/monthly/ui.py', ui)
edit('dashboard/monthly/forecasting/__init__.py', lambda _: '"""Final Prophet + XGBoost architecture; methodology settings are explicit."""\n')
