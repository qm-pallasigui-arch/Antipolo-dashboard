"""Shared chart theme and availability semantics for pages and reports."""
import plotly.graph_objects as go
from math import isfinite
from .components import FONT, STATUS_LABELS as LABELS


def trend_figure(dataset, code, forecast=None):
    rows = [r for r in dataset['observations'] if r['icd10_block'] == code]
    dates = [f'{r["year"]}-{r["month_number"]:02}-01' for r in rows]
    figure = go.Figure(go.Scatter(x=dates, y=[r['consultation_count'] for r in rows],
        mode='lines', connectgaps=False, name='Historical consultations', line={'color': '#17685f'}))
    for status, symbol, color in [('observed', 'circle', '#17685f'), ('observed_zero', 'diamond-open', '#17685f')]:
        selected = [(d, r) for d, r in zip(dates, rows) if r['observation_status'] == status]
        figure.add_trace(go.Scatter(x=[d for d, _ in selected], y=[r['consultation_count'] for _, r in selected],
            mode='markers', name=LABELS[status], marker={'symbol': symbol, 'color': color, 'size': 7}, hovertemplate='%{x|%b %Y}<br>%{y:,.0f} consultations<extra>' + LABELS[status] + '</extra>'))
    for status, color in [('city_report_unavailable', '#b8c4d4'), ('outside_annual_top5', '#e8c688')]:
        for year in range(2016, 2026):
            if any(r['year'] == year and r['observation_status'] == status for r in rows):
                figure.add_vrect(x0=f'{year}-01-01', x1=f'{year + 1}-01-01', fillcolor=color, opacity=.24, line_width=0, layer='below')
        figure.add_trace(go.Scatter(x=[None], y=[None], mode='markers', marker={'color': color, 'symbol': 'square'}, name='Months not reported · ' + LABELS[status]))
    if forecast:
        values = forecast['forecast_values']
        if has_intervals(values):
            x = [r['month'] + '-01' for r in values]
            figure.add_trace(go.Scatter(x=x, y=[r['upper'] for r in values], mode='lines', line={'width': 0}, showlegend=False, hoverinfo='skip'))
            figure.add_trace(go.Scatter(x=x, y=[r['lower'] for r in values], mode='lines', line={'width': 0}, fill='tonexty', fillcolor='rgba(185,103,35,0.18)', name='Prediction interval', hovertemplate='%{x|%b %Y}<br>Lower bound: %{y:,.1f}<extra>Prediction interval</extra>'))
        if len(forecast.get('baseline_forecast', [])) == len(values):
            figure.add_trace(go.Scatter(x=[r['month'] + '-01' for r in values], y=forecast['baseline_forecast'],
                mode='lines', name='Prophet baseline (prototype)', line={'color': '#627d98', 'dash': 'dot'}))
        figure.add_trace(go.Scatter(x=[r['month'] + '-01' for r in values], y=[r['consultation_count'] for r in values],
            mode='lines+markers', name='Estimated consultations', line={'color': '#b96723', 'dash': 'dash'}, hovertemplate='%{x|%b %Y}<br>%{y:,.1f} estimated consultations<extra></extra>'))
    figure.update_layout(template='plotly_white', xaxis_title='Month', yaxis_title='Consultations',
                         font={'family': FONT, 'size': 14, 'color': '#17324d'},
                         legend={'orientation': 'h', 'y': -0.3}, margin={'t': 24, 'b': 160, 'l': 90, 'r': 24}, height=500)
    figure.update_yaxes(automargin=True, tickformat=',.0f')
    figure.update_xaxes(automargin=True)
    return figure


def has_intervals(values):
    return bool(values) and all(isinstance(r.get(k), (int, float)) and isfinite(r[k]) for r in values for k in ('lower', 'upper', 'consultation_count')) and all(r['lower'] <= r['consultation_count'] <= r['upper'] for r in values)

