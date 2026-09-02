"""All Plotly figure builders. Every chart is generated from live data -- nothing hardcoded."""

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from dashboard.config import DISEASES, DISEASE_COLORS
from dashboard.styles import FONT, TEXTC, GRIDC, PLOTBG, COVID_START, COVID_END


def base_layout(height=280, margin=None):
    m = margin or dict(l=48, r=16, t=8, b=40)
    return dict(
        height=height, plot_bgcolor=PLOTBG, paper_bgcolor=PLOTBG,
        font=dict(family=FONT, color=TEXTC, size=11), margin=m,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, font=dict(size=10)),
        hovermode="x unified",
    )


def fig_hybrid_forecast(result: dict, year_range):
    """Observed history (cropped to the slider range) + SARIMA-only vs Hybrid forecast, with CI band."""
    series = result["series"]
    yr_min, yr_max = year_range
    mask = (series.index.year >= yr_min) & (series.index.year <= yr_max)
    hist = series[mask]

    fig = go.Figure()
    fig.add_vrect(
        x0=COVID_START, x1=COVID_END, fillcolor="rgba(136,135,128,0.10)",
        layer="below", line_width=0, annotation_text="COVID-19 closure",
        annotation_position="top left", annotation_font_size=9, annotation_font_color="#999",
    )

    ci_lo, ci_hi = result["ci_lower"], result["ci_upper"]
    x_band = list(ci_hi.index) + list(ci_lo.index[::-1])
    y_band = list(ci_hi.values) + list(ci_lo.values[::-1])
    fig.add_trace(go.Scatter(
        x=x_band, y=y_band, fill="toself", fillcolor="rgba(216,90,48,0.12)",
        line=dict(color="rgba(0,0,0,0)"), name="95% CI (SARIMA)", hoverinfo="skip",
    ))

    fig.add_trace(go.Scatter(
        x=hist.index, y=hist.values, name="Observed",
        line=dict(color="#378ADD", width=1.8), mode="lines",
    ))
    fig.add_trace(go.Scatter(
        x=result["sarima_forecast"].index, y=result["sarima_forecast"].values,
        name="SARIMA-only forecast", line=dict(color="#1D9E75", width=1.5, dash="dot"), mode="lines",
    ))
    fig.add_trace(go.Scatter(
        x=result["hybrid_forecast"].index, y=result["hybrid_forecast"].values,
        name="Hybrid forecast (SARIMA + NNAR)", line=dict(color="#D4537E", width=1.5, dash="dot"), mode="lines",
    ))
    final_label = "Final forecast (auto-selected: hybrid)" if result["selected_model"] == "hybrid" \
        else "Final forecast (auto-selected: SARIMA-only)"
    fig.add_trace(go.Scatter(
        x=result["final_forecast"].index, y=result["final_forecast"].values,
        name=final_label, line=dict(color="#D85A30", width=2.6), mode="lines",
    ))

    fig.update_layout(**base_layout(320))
    fig.update_xaxes(showgrid=False, linecolor=GRIDC)
    fig.update_yaxes(gridcolor=GRIDC, zeroline=False, title_text="Cases / month")
    return fig


def fig_backtest(result: dict):
    """Held-out 12 months: actual vs SARIMA-only vs Hybrid."""
    test = result["test_actual"]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=test.index, y=test.values, name="Actual",
        line=dict(color="#333333", width=2), mode="lines+markers",
    ))
    fig.add_trace(go.Scatter(
        x=result["test_sarima_only"].index, y=result["test_sarima_only"].values,
        name="SARIMA-only", line=dict(color="#1D9E75", width=1.5, dash="dot"), mode="lines",
    ))
    fig.add_trace(go.Scatter(
        x=result["test_hybrid"].index, y=result["test_hybrid"].values,
        name="Hybrid", line=dict(color="#D85A30", width=2), mode="lines",
    ))
    fig.update_layout(**base_layout(240))
    fig.update_xaxes(showgrid=False, linecolor=GRIDC)
    fig.update_yaxes(gridcolor=GRIDC, zeroline=False, title_text="Cases / month")
    return fig


def fig_residual_diag(result: dict):
    """SARIMA residuals vs what the NNAR learned to fit on them (non-linear leftover pattern)."""
    resid = result["residuals"]
    nnar_fit = result["nnar_fitted"]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=resid.index, y=resid.values, name="SARIMA residuals",
        line=dict(color="#AAAAAA", width=1.2), mode="lines",
    ))
    if len(nnar_fit) > 0:
        fig.add_trace(go.Scatter(
            x=nnar_fit.index, y=nnar_fit.values, name="NNAR fitted (non-linear pattern)",
            line=dict(color="#7F77DD", width=1.8), mode="lines",
        ))
    fig.add_hline(y=0, line_color="rgba(0,0,0,0.18)", line_width=1)
    fig.update_layout(**base_layout(200))
    fig.update_xaxes(showgrid=False, linecolor=GRIDC)
    fig.update_yaxes(gridcolor=GRIDC, zeroline=False, title_text="Residual")
    return fig


def fig_decomposition(decomp):
    panels = [
        ("Observed", decomp.observed, "#378ADD"),
        ("Trend", decomp.trend, "#1D9E75"),
        ("Seasonal", decomp.seasonal, "#EF9F27"),
        ("Residual", decomp.resid, "#D85A30"),
    ]
    fig = make_subplots(rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.04,
                        subplot_titles=[p[0] for p in panels])
    for i, (label, data, color) in enumerate(panels, 1):
        fig.add_trace(
            go.Scatter(x=data.index, y=data.values, line=dict(color=color, width=1.5),
                      name=label, showlegend=False),
            row=i, col=1,
        )
        fig.update_yaxes(gridcolor=GRIDC, zeroline=False, tickfont=dict(size=9), row=i, col=1)
    fig.update_layout(
        height=440, plot_bgcolor=PLOTBG, paper_bgcolor=PLOTBG,
        font=dict(family=FONT, color=TEXTC, size=10),
        margin=dict(l=48, r=16, t=32, b=32), showlegend=False,
    )
    fig.update_xaxes(showgrid=False, linecolor=GRIDC)
    return fig


def fig_disease_bar(df):
    annual = df.groupby(["year", "disease"])["cases"].sum().reset_index()
    fig = go.Figure()
    for disease in DISEASES:
        sub = annual[annual["disease"] == disease]
        fig.add_trace(go.Bar(
            x=sub["year"], y=sub["cases"], name=disease,
            marker_color=DISEASE_COLORS.get(disease, "#888"), marker_cornerradius=2,
        ))
    layout = base_layout(260)
    layout["legend"] = dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, font=dict(size=9))
    layout["barmode"] = "stack"
    fig.update_layout(**layout)
    fig.update_xaxes(showgrid=False, dtick=1)
    fig.update_yaxes(gridcolor=GRIDC, zeroline=False, title_text="Total cases")
    return fig


def fig_seasonal_heatmap(df):
    pivot = (
        df.groupby(["year", "month"])["cases"].sum().reset_index()
        .pivot(index="month", columns="year", values="cases").fillna(0)
    )
    month_labels = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    fig = go.Figure(go.Heatmap(
        z=pivot.values, x=[str(c) for c in pivot.columns], y=[month_labels[m-1] for m in pivot.index],
        colorscale="Blues", colorbar=dict(title="Cases", thickness=12, len=0.8),
        hovertemplate="Year: %{x}<br>Month: %{y}<br>Cases: %{z}<extra></extra>",
    ))
    fig.update_layout(**base_layout(280, margin=dict(l=48, r=60, t=8, b=40)))
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=False)
    return fig


def fig_donut(df):
    totals = df.groupby("disease")["cases"].sum().reindex(DISEASES).fillna(0)
    fig = go.Figure(go.Pie(
        labels=totals.index.tolist(), values=totals.values.tolist(), hole=0.60,
        marker=dict(colors=[DISEASE_COLORS[d] for d in totals.index], line=dict(color="white", width=2)),
        textinfo="none",
        hovertemplate="<b>%{label}</b><br>Cases: %{value:,}<br>Share: %{percent}<extra></extra>",
    ))
    fig.update_layout(**base_layout(260, margin=dict(l=8, r=8, t=8, b=8)))
    return fig


def summary_cards(df):
    total = int(df["cases"].sum())
    annual = df.groupby("year")["cases"].sum()
    peak_year = int(annual.idxmax())
    peak_val = int(annual.max())
    top_disease = df.groupby("disease")["cases"].sum().idxmax()
    top_pct = int(df.groupby("disease")["cases"].sum().max() / df["cases"].sum() * 100)
    years_covered = f"{df['year'].min()}\u2013{df['year'].max()}"
    return total, peak_year, peak_val, top_disease, top_pct, years_covered
