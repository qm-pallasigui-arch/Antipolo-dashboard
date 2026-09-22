"""
The page layout, as a `build_layout()` function rather than a bare
module-level `app.layout = ...` assignment. That matters for two reasons:
  1. It can be unit-tested (call it, assert on the returned tree) without
     also constructing a live Dash app / registering callbacks.
  2. Nothing runs at import time -- app.py decides when to build it.
"""

from dash import dcc, html

from dashboard.config import DISEASES, DATA_START_YEAR, DATA_END_YEAR, BASELINE_MAPE
from dashboard.styles import (
    FONT, TEXTC, S_TOPBAR, S_CARD, S_LABEL, S_DROP, S_CHART_TITLE, S_CHART_SUB,
)
from dashboard.ui.components import section


def build_layout() -> html.Div:
    return html.Div([

        dcc.Store(id="store-data", storage_type="session"),
        dcc.Store(id="store-hybrid", storage_type="session"),
        dcc.Store(id="store-upload-summary", storage_type="session"),

        # Top bar
        html.Div([
            html.Div([
                html.Span("\U0001F6E1 ", style={"fontSize": "17px"}),
                html.Div([
                    html.P("Disease Surveillance \u2014 Hybrid Forecast",
                           style={"fontWeight": "500", "fontSize": "14px", "color": TEXTC, "margin": "0"}),
                    html.P("Antipolo City \u00b7 Region 4-A \u00b7 City-wide (DOH-PIDSR) + DepEd-context mock \u00b7 SARIMA + NNAR hybrid",
                           style={"fontSize": "11px", "color": "#888", "margin": "0"}),
                ]),
            ], style={"display": "flex", "alignItems": "center", "gap": "10px"}),
            html.Div([
                html.Span(f"Baseline MAPE: {BASELINE_MAPE}%", style={
                    "fontSize": "11px", "padding": "3px 10px", "background": "#E6F1FB",
                    "color": "#185FA5", "borderRadius": "6px", "marginRight": "10px",
                }),
                dcc.Upload(
                    id="upload-csv",
                    children=html.Div([
                        html.Span("\U0001F4C2 ", style={"fontSize": "13px"}),
                        html.Span("Upload CSV or DOH/PIDSR Excel", style={"fontSize": "12px", "color": "#185FA5"}),
                    ]),
                    style={"border": "1px dashed #378ADD", "borderRadius": "6px", "padding": "5px 12px",
                          "cursor": "pointer", "background": "#F0F7FF"},
                    accept=".csv,.xlsx",
                ),
                html.Div(id="upload-status", style={"fontSize": "11px", "color": "#888", "marginLeft": "10px", "maxWidth": "480px"}),
            ], style={"display": "flex", "alignItems": "center"}),
        ], style=S_TOPBAR),

        section("Upload summary"),
        html.Div(
            id="upload-summary-content",
            children=html.P(
                "Preparing data summary…",
                style={"fontSize": "12px", "color": "#888", "margin": "0"},
            ),
            style={**S_CARD, "margin": "0 22px 18px"},
        ),

        # General filters (aggregate charts only)
        html.Div([
            html.Div([
                html.Label("Year range", style={**S_LABEL, "marginRight": "6px"}),
                dcc.RangeSlider(
                    id="f-year", min=DATA_START_YEAR, max=DATA_END_YEAR, step=1,
                    value=[DATA_START_YEAR, DATA_END_YEAR],
                    marks={y: {"label": str(y), "style": {"fontSize": "10px", "color": "#888"}}
                           for y in range(DATA_START_YEAR, DATA_END_YEAR + 1, 2)},
                    tooltip={"placement": "bottom", "always_visible": False},
                ),
            ], style={"flex": "2", "minWidth": "260px"}),
            html.Div([
                html.Label("Disease (aggregate charts)", style={**S_LABEL, "marginRight": "6px"}),
                dcc.Dropdown(
                    id="f-disease",
                    options=[{"label": "All diseases", "value": "all"}] + [{"label": d, "value": d} for d in DISEASES],
                    value="all", clearable=False, style=S_DROP,
                ),
            ], style={"display": "flex", "alignItems": "center", "gap": "6px"}),
        ], style={"display": "flex", "gap": "24px", "padding": "0 22px", "marginBottom": "10px",
                  "flexWrap": "wrap", "alignItems": "flex-end"}),

        html.Div(id="metric-row", style={"display": "flex", "gap": "10px", "flexWrap": "wrap",
                                          "padding": "0 22px", "marginBottom": "18px"}),

        # ---- Hybrid forecast section --------------------------------------
        html.Div([
            section("Hybrid forecast \u2014 SARIMA + NNAR (per disease)"),
            html.Div([
                html.Label("Disease to forecast", style={**S_LABEL, "marginRight": "6px"}),
                dcc.Dropdown(
                    id="f-hybrid-disease",
                    options=[{"label": d, "value": d} for d in DISEASES],
                    value=DISEASES[0], clearable=False, style=S_DROP,
                ),
                html.Span("\u2753 not computed yet \u00b7 \u2713 clean fit \u00b7 \u26a0 has model notes \u00b7 \u274c failed",
                          style={"fontSize": "10px", "color": "#aaa", "marginLeft": "10px"}),
            ], style={"padding": "0 22px", "marginBottom": "10px", "display": "flex", "alignItems": "center"}),
        ]),

        html.Div(id="hybrid-metric-row", style={"display": "flex", "gap": "10px", "flexWrap": "wrap",
                                                 "padding": "0 22px", "marginBottom": "8px"}),
        html.Div(id="hybrid-warnings-panel", style={"padding": "0 22px", "marginBottom": "14px"}),

        html.Div([
            html.P("Observed history + 12-month-ahead forecast", style=S_CHART_TITLE),
            html.P("Green dotted = SARIMA-only \u00b7 Pink dotted = Hybrid (SARIMA + NNAR) \u00b7 Thick orange = final "
                   "forecast (whichever of the two won the backtest) \u00b7 Shaded = 95% CI",
                   style=S_CHART_SUB),
            dcc.Graph(id="chart-hybrid-forecast", config={"displayModeBar": True,
                      "modeBarButtonsToRemove": ["select2d", "lasso2d", "autoScale2d"]}, style={"height": "320px"}),
        ], style={**S_CARD, "margin": "0 22px 14px"}),

        html.Div([
            html.Div([
                html.P("Backtest \u2014 last 12 held-out months", style=S_CHART_TITLE),
                html.P("Actual vs. SARIMA-only vs. Hybrid (this is what the MAPE cards above are computed from)",
                       style=S_CHART_SUB),
                dcc.Graph(id="chart-backtest", config={"displayModeBar": False}, style={"height": "240px"}),
            ], style={**S_CARD, "flex": "1"}),
            html.Div([
                html.P("Residual diagnostics", style=S_CHART_TITLE),
                html.P("SARIMA residuals (gray) vs. the non-linear pattern NNAR learned from them (purple)",
                       style=S_CHART_SUB),
                dcc.Graph(id="chart-residual", config={"displayModeBar": False}, style={"height": "200px"}),
            ], style={**S_CARD, "flex": "1"}),
        ], style={"display": "flex", "gap": "14px", "padding": "0 22px", "marginBottom": "14px"}),

        html.Div([
            html.P("Seasonal decomposition (additive, period = 12 months)", style=S_CHART_TITLE),
            html.P("Full 120-month history for the selected disease \u00b7 Observed \u2192 Trend \u2192 Seasonal \u2192 Residual",
                   style=S_CHART_SUB),
            dcc.Graph(id="chart-decomp", config={"displayModeBar": False}, style={"height": "440px"}),
        ], style={**S_CARD, "margin": "0 22px 14px"}),

        # ---- Aggregate views -----------------------------------------------
        section("Cross-disease breakdown (uses the general filters above)"),
        html.Div([
            html.Div([
                html.P("Disease share of total cases", style=S_CHART_TITLE),
                html.P("Proportion of each reportable disease \u00b7 filtered period", style=S_CHART_SUB),
                dcc.Graph(id="chart-donut", config={"displayModeBar": False}, style={"height": "260px"}),
            ], style={**S_CARD, "flex": "1"}),
            html.Div([
                html.P("Monthly seasonal heatmap", style=S_CHART_TITLE),
                html.P("Case intensity by month and year \u00b7 darker = more cases", style=S_CHART_SUB),
                dcc.Graph(id="chart-heatmap", config={"displayModeBar": False}, style={"height": "280px"}),
            ], style={**S_CARD, "flex": "1"}),
        ], style={"display": "flex", "gap": "14px", "padding": "0 22px", "marginBottom": "14px"}),

        html.Div([
            html.P("Disease burden by year", style=S_CHART_TITLE),
            html.P("Annual cases stacked by disease type", style=S_CHART_SUB),
            dcc.Graph(id="chart-bar", config={"displayModeBar": False}, style={"height": "260px"}),
        ], style={**S_CARD, "margin": "0 22px 14px"}),

        section("Raw data preview"),
        html.Div([
            html.P("Annual totals by disease \u2014 filtered view", style=S_CHART_TITLE),
            html.P("Based on active general filters above \u00b7 upload a CSV or DOH/PIDSR Excel workbook to replace mock data",
                   style=S_CHART_SUB),
            html.Div(id="data-table"),
        ], style={**S_CARD, "margin": "0 22px 14px"}),

        html.Div([
            html.P(
                "\u26a0  City-wide surveillance, no school-level breakdown. Diseases without an uploaded real source "
                "are backfilled with synthetic mock data (120 months, Jan 2016\u2013Dec 2025) so all 7 tracked diseases "
                "stay forecastable \u2014 each is labeled \"Real (DOH-PIDSR)\" or \"Synthetic mock\" in the hybrid "
                "section above. Uploading a real DOH/PIDSR Excel workbook (weekly cases per disease sheet) converts "
                "weeks to months using the ISO week's Thursday; a reported week 53 that isn't a true ISO week for that "
                "year is assigned to December rather than dropped. COVID-19 closure years (2020\u20132022) are treated "
                "as a structural break in the mock data. Each disease's hybrid model is trained lazily, on demand \u2014 "
                "only when you select it in the dropdown above, not all 7 at once \u2014 and then cached for the rest "
                "of this session (SARIMA fit on all-but-last 12 months, NNAR trained on its residuals, backtested "
                "against those 12 held-out months); switching disease the first time will take a few seconds while "
                "it fits, and instantly after that. Uploading a new file clears the cache, since a forecast fit on "
                "the old data shouldn't be shown once new data replaces it. The year-range slider only crops the "
                "displayed window, it does not retrain the models. Because the NNAR step can only add value if "
                "SARIMA's residuals still contain non-linear structure, the pipeline backtests both SARIMA-only and "
                "Hybrid on the held-out 12 months and automatically ships whichever performed better \u2014 shown as "
                "\"Final model\" above \u2014 rather than assuming the hybrid always wins.",
                style={"fontSize": "11px", "color": "#888", "lineHeight": "1.7", "margin": "0"}
            )
        ], style={"background": "#F7F7F5", "borderRadius": "8px", "padding": "12px 16px", "margin": "0 22px 30px"}),

    ], style={"fontFamily": FONT, "maxWidth": "1180px", "margin": "0 auto", "background": "#F5F5F3", "minHeight": "100vh"})
