"""Inspectable, persisted reports for every historically reported block."""
import csv
import html
import io
import json
import secrets

from .domain import LIMITATIONS, annual_history, now
from .forecast import METHOD_PENDING
from .forecasting.prototype_adapter import PROTOTYPE_DISCLAIMER


def build_report(store, user, code):
    if not user or not user.get('active'):
        raise PermissionError('Authentication required.')
    dataset = store.active()
    if not dataset:
        raise ValueError('No active dataset.')
    block = next((b for b in dataset['blocks'] if b['icd10_block'] == code), None)
    if not block:
        raise ValueError('Select a historically reported ICD-10 block.')
    forecast = store.latest_forecast(dataset['dataset_signature'], code) if block['eligible'] else None
    report = dict(report_id=secrets.token_hex(16), generated_at=now(), dataset_signature=dataset['dataset_signature'],
                  provenance=dataset['provenance'], source_file=dataset['source_file'], block=block,
                  annual_history=annual_history(dataset, code), historical_observations=[r for r in dataset['observations'] if r['icd10_block'] == code],
                  warnings=dataset['warnings'], source_annotations=store.notes(dataset['dataset_signature']), forecast=forecast,
                  forecast_explanation=(PROTOTYPE_DISCLAIMER if forecast.get('prototype') else 'Forecasted monthly consultations are estimates.') if forecast else METHOD_PENDING if block['eligible'] else block['reason'],
                  interpretation=LIMITATIONS, limitations=LIMITATIONS)
    with store.connect() as db:
        db.execute('INSERT INTO reports VALUES (?,?,?,?,?,?)', (report['report_id'], dataset['dataset_signature'], code, user['id'], json.dumps(report), now()))
        store.audit(user['id'], 'report_generation', report['report_id'], db)
        store.notify('report', 'Report generated', code, 'Reports', user_id=user['id'], record_id=report['report_id'], db=db)
    return report


def export_csv(report):
    output = io.StringIO(newline='')
    columns = ['dataset_signature', 'icd10_block', 'month', 'consultation_count', 'observation_status', 'forecast_label', 'prototype', 'forecast_note']
    writer = csv.DictWriter(output, fieldnames=columns)
    writer.writeheader()
    for row in report['historical_observations']:
        writer.writerow({**{k: row[k] for k in columns if k in row and k != 'month'}, 'month': f'{row["year"]}-{row["month_number"]:02}'})
    for row in (report.get('forecast') or {}).get('forecast_values', []):
        writer.writerow(dict(dataset_signature=report['dataset_signature'], icd10_block=report['block']['icd10_block'],
                             month=row['month'], consultation_count=row['consultation_count'], observation_status='forecast', forecast_label=report['forecast']['model_label'],
                             prototype=report['forecast']['prototype'], forecast_note=report['forecast_explanation']))
    return output.getvalue()


def export_html(report):
    from .charts import trend_figure
    rows = report['historical_observations']
    forecast = report.get('forecast')
    figure = trend_figure({'observations': rows}, report['block']['icd10_block'], forecast)
    esc = lambda value: html.escape(str(value))
    def table(records):
        if not records:
            return '<p>None recorded.</p>'
        keys = list(records[0])
        return '<table><thead><tr>' + ''.join('<th>' + esc(k) + '</th>' for k in keys) + '</tr></thead><tbody>' + ''.join(
            '<tr>' + ''.join('<td>' + ('Unknown / unavailable' if r.get(k) is None else esc(r.get(k))) + '</td>' for k in keys) + '</tr>' for r in records) + '</tbody></table>'
    return ('<!doctype html><html lang="en"><meta charset="utf-8"><title>Antipolo monthly consultation report</title>'
            '<style>body{font:14px Segoe UI,system-ui,sans-serif;max-width:1100px;margin:40px auto;padding:20px;color:#16334a}table{border-collapse:collapse;width:100%;font-size:12px}td,th{border:1px solid #ddd;padding:6px;text-align:left}pre{white-space:pre-wrap;overflow-wrap:anywhere}@media print{body{margin:0}}</style>'
            '<h1>' + esc(report['block']['icd10_block'] + ' · ' + report['block']['icd10_description']) + '</h1>'
            '<p>Generated ' + esc(report['generated_at']) + ' · Dataset ' + esc(report['dataset_signature']) + '</p>'
            '<h2>Source and provenance</h2><pre>' + esc(json.dumps(report['provenance'], indent=2, ensure_ascii=False)) + '</pre>'
            '<p>Source file: ' + esc(report['source_file']) + '</p><h2>Coverage and eligibility</h2><pre>' + esc(json.dumps(report['block'], indent=2)) + '</pre>'
            '<h2>Annual Top-5 history</h2>' + table(report['annual_history'])
            + '<h2>Historical monthly trend</h2>' + figure.to_html(full_html=False, include_plotlyjs=True)
            + '<h2>Data quality</h2><p>' + esc(' '.join(report['warnings'])) + '</p>' + table(report['source_annotations'])
            + '<h2>' + esc(forecast['model_label'] if forecast else 'Forecast') + '</h2><p>' + esc(report['forecast_explanation']) + '</p>' + table(forecast['forecast_values'] if forecast else [])
            + '<h2>Model performance</h2><pre>' + esc(json.dumps({k: forecast[k] for k in ('model_label', 'evaluation', 'warnings')} if forecast else {'status': METHOD_PENDING}, indent=2)) + '</pre>'
            + '<h2>Interpretation and limitations</h2><p>' + esc(report['limitations']) + '</p>'
            + '<h2>Monthly observations and availability</h2>' + table([{k: r[k] for k in ('year', 'month', 'consultation_count', 'observation_status')} for r in rows]) + '</html>')
