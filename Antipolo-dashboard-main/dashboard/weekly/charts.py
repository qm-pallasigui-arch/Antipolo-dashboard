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
    # Trace names are deliberately short. Under hovermode 'x unified' Plotly
    # allocates width per trace and ellipsises anything longer, which made every
    # label unreadable in a narrow chart. The full description of each group
    # already sits in prose below the chart in ui.render, so nothing is lost.
    # hovertemplate is set on every trace because Plotly's default prints raw
    # float precision: a forecast is an expected count, and "33.55735" is not a
    # number of cases. Reported counts are whole people; forecasts and the band
    # are genuinely fractional, so they keep one decimal.
    fig = go.Figure(go.Scatter(x=labels, y=[actual[p] if p not in excluded_keys else None for p in ordered],
                              name='Reported', mode='lines+markers', connectgaps=False,
                              line={'color': '#66758b'}, hovertemplate='%{y:,.0f}'))
    if excluded:
        fig.add_trace(go.Scatter(x=[f"{r['year']}-W{r['morbidity_week']:02d}" for r in excluded],
                                 y=[actual.get((r['year'], r['morbidity_week'])) for r in excluded], mode='markers',
                                 marker={'symbol': 'circle-open', 'size': 10, 'color': '#b66c0a'}, name='Excluded',
                                 hovertemplate='%{y:,.0f}'))
    points = (result or {}).get('forecast_index', [])[:horizon]
    future = [f"{p['year']}-W{p['morbidity_week']:02d}" if p['year'] else f"Week +{p['horizon_week']}" for p in points]
    if result:
        band = result.get('range')
        if band:
            # Lower bound exists only to give fill='tonexty' something to fill
            # against. showlegend=False hides it from the legend but not from the
            # unified hover, so without hoverinfo it surfaced as an unnamed
            # "trace" row showing a bare number that means nothing.
            fig.add_trace(go.Scatter(x=future, y=band['lower'][:horizon], mode='lines', line={'width': 0},
                                     showlegend=False, hoverinfo='skip'))
            fig.add_trace(go.Scatter(x=future, y=band['upper'][:horizon], mode='lines', line={'width': 0}, fill='tonexty',
                                     fillcolor='rgba(21,130,125,.15)', name='Forecast range',
                                     hovertemplate='%{y:,.1f}'))
        for model, label, color in [('hybrid', 'Hybrid', '#15827d'), ('sarima', 'SARIMA-only', '#7660a7')]:
            if result.get(model):
                fig.add_trace(go.Scatter(x=future, y=result[model][:horizon], name=label,
                                         line={'color': color, 'width': 3 if model == 'hybrid' else 2},
                                         hovertemplate='%{y:,.1f}', meta={'model': model}))
    if future and ((result or {}).get('hybrid') or (result or {}).get('sarima')):
        fig.update_layout(title=f'Next {len(future)} weeks · weekly forecast')
        fig.update_xaxes(range=[max(-.5, len(labels) - 13.5), len(labels) + len(future) - .5])
    fig.update_layout(template='plotly_white', xaxis_title='Reporting year / morbidity week', yaxis_title='Weekly cases',
                      legend={'orientation': 'h', 'y': -0.3}, margin={'l': 40, 'r': 20, 't': 25, 'b': 100}, hovermode='x unified')
    fig.update_xaxes(type='category', categoryorder='array', categoryarray=list(dict.fromkeys(labels + future)))
    return fig


