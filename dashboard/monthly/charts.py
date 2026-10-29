"""Shared chart theme and availability semantics for pages and reports."""
import plotly.graph_objects as go
from .components import FONT, STATUS_LABELS as LABELS


def trend_figure(dataset, code, forecast=None):
    rows = [r for r in dataset['observations'] if r['icd10_block'] == code]
    dates = [f'{r["year"]}-{r["month_number"]:02}-01' for r in rows]
    figure = go.Figure(go.Scatter(x=dates, y=[r['consultation_count'] for r in rows],
        mode='lines', connectgaps=False, name='Historical consultations', line={'color': '#17685f'}))
    for status, symbol, color in [('observed', 'circle', '#17685f'), ('observed_zero', 'diamond-open', '#17685f')]:
        selected = [(d, r) for d, r in zip(dates, rows) if r['observation_status'] == status]
        figure.add_trace(go.Scatter(x=[d for d, _ in selected], y=[r['consultation_count'] for _, r in selected],
            mode='markers', name=LABELS[status], marker={'symbol': symbol, 'color': color, 'size': 7}))
    for status, color in [('city_report_unavailable', '#b8c4d4'), ('outside_annual_top5', '#e8c688')]:
        for year in range(2016, 2026):
            if any(r['year'] == year and r['observation_status'] == status for r in rows):
                figure.add_vrect(x0=f'{year}-01-01', x1=f'{year + 1}-01-01', fillcolor=color, opacity=.24, line_width=0, layer='below')
        figure.add_trace(go.Scatter(x=[None], y=[None], mode='markers', marker={'color': color, 'symbol': 'square'}, name=LABELS[status]))
    if forecast:
        values = forecast['forecast_values']
        if len(forecast.get('baseline_forecast', [])) == len(values):
            figure.add_trace(go.Scatter(x=[r['month'] + '-01' for r in values], y=forecast['baseline_forecast'],
                mode='lines', name='Prophet baseline (prototype)', line={'color': '#627d98', 'dash': 'dot'}))
        figure.add_trace(go.Scatter(x=[r['month'] + '-01' for r in values], y=[r['consultation_count'] for r in values],
            mode='lines+markers', name=forecast.get('model_label', 'Forecasted consultations'), line={'color': '#b96723', 'dash': 'dash'}))
    figure.update_layout(template='plotly_white', xaxis_title='Month', yaxis_title='Monthly consultation count',
                         font={'family': FONT, 'size': 12, 'color': '#17324d'},
                         legend={'orientation': 'h', 'y': -0.25}, margin={'t': 20, 'b': 120, 'l': 60, 'r': 20}, height=420)
    return figure

