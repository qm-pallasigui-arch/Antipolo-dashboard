import plotly.graph_objects as go


def forecast_chart(active, disease, result, horizon):
    rows = [r for r in active['records'] if r['disease'] == disease]
    actual = {(r['year'], r['morbidity_week']): r['case_count'] for r in rows}
    for gap in active['quality']['missing_weeks']:
        if gap['disease'] == disease:
            actual[(gap['year'], gap['morbidity_week'])] = None
    ordered = sorted(actual)
    labels = [f'{y}-W{w:02d}' for y, w in ordered]
    excluded = [r for r in active['quality']['excluded_from_training'] if r['disease'] == disease]
    excluded_keys = {(r['year'], r['morbidity_week']) for r in excluded}
    fig = go.Figure(go.Scatter(x=labels, y=[actual[p] if p not in excluded_keys else None for p in ordered],
                              name='Reported: complete', mode='lines+markers', connectgaps=False, line={'color': '#66758b'}))
    if excluded:
        fig.add_trace(go.Scatter(x=[f"{r['year']}-W{r['morbidity_week']:02d}" for r in excluded],
                                 y=[actual.get((r['year'], r['morbidity_week'])) for r in excluded], mode='markers',
                                 marker={'symbol': 'circle-open', 'size': 10, 'color': '#b66c0a'}, name='Excluded: reporting incomplete/unknown'))
    points = (result or {}).get('forecast_index', [])[:horizon]
    future = [f"{p['year']}-W{p['morbidity_week']:02d}" if p['year'] else f"Week +{p['horizon_week']}" for p in points]
    if result:
        band = result.get('range')
        if band:
            fig.add_trace(go.Scatter(x=future, y=band['lower'][:horizon], mode='lines', line={'width': 0}, showlegend=False))
            fig.add_trace(go.Scatter(x=future, y=band['upper'][:horizon], mode='lines', line={'width': 0}, fill='tonexty',
                                     fillcolor='rgba(21,130,125,.15)', name='Forecast uncertainty range (provisional)'))
        for model, label, color in [('hybrid', 'Hybrid SARIMA–NNAR (primary)', '#15827d'), ('sarima', 'SARIMA-only comparison', '#7660a7')]:
            if result.get(model):
                fig.add_trace(go.Scatter(x=future, y=result[model][:horizon], name=label, line={'color': color, 'width': 3 if model == 'hybrid' else 2}))
    if future and ((result or {}).get('hybrid') or (result or {}).get('sarima')):
        fig.update_layout(title=f'Next {len(future)} weeks · weekly forecast')
        fig.update_xaxes(range=[max(-.5, len(labels) - 13.5), len(labels) + len(future) - .5])
    fig.update_layout(template='plotly_white', xaxis_title='Reporting year / morbidity week', yaxis_title='Weekly cases',
                      legend={'orientation': 'h', 'y': -0.3}, margin={'l': 40, 'r': 20, 't': 25, 'b': 100}, hovermode='x unified')
    fig.update_xaxes(type='category', categoryorder='array', categoryarray=list(dict.fromkeys(labels + future)))
    return fig


