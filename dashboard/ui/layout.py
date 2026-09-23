"""Page layout for the health-officer surveillance workflow."""

from dash import dcc, html

from dashboard.config import DISEASES, DATA_START_YEAR, DATA_END_YEAR, BASELINE_MAPE
from dashboard.styles import (
    FONT, TEXTC, S_TOPBAR, S_CARD, S_LABEL, S_DROP, S_CHART_TITLE, S_CHART_SUB,
)
from dashboard.ui.components import section


TAB_STYLE = {
    "padding": "12px 16px",
    "fontSize": "13px",
    "fontWeight": "500",
    "border": "none",
    "borderBottom": "2px solid transparent",
    "background": "white",
    "color": "#666",
}
TAB_SELECTED_STYLE = {
    **TAB_STYLE,
    "color": "#185FA5",
    "borderBottom": "2px solid #185FA5",
}


def _overview_tab() -> dcc.Tab:
    return dcc.Tab(
        label="Surveillance overview",
        value="overview",
        style=TAB_STYLE,
        selected_style=TAB_SELECTED_STYLE,
        children=[
            html.Div(id="global-data-source-banner"),
            html.Div([
                html.Div([
                    html.Label("Disease", style={**S_LABEL, "marginRight": "6px"}),
                    dcc.Dropdown(
                        id="f-disease",
                        options=[{"label": "All diseases", "value": "all"}]
                        + [{"label": disease, "value": disease} for disease in DISEASES],
                        value="all",
                        clearable=False,
                        style=S_DROP,
                    ),
                ], style={"display": "flex", "alignItems": "center", "gap": "6px"}),
            ], className="overview-filter-row"),

            html.Div(
                id="metric-row",
                style={"display": "flex", "gap": "10px", "flexWrap": "wrap",
                       "padding": "0 22px", "marginBottom": "18px"},
            ),

            section("Disease activity"),
            html.Div([
                html.P("Disease burden by year", style=S_CHART_TITLE),
                html.P("Annual cases stacked by disease type", style=S_CHART_SUB),
                dcc.Graph(id="chart-bar", config={"displayModeBar": False}, style={"height": "300px"}),
            ], style={**S_CARD, "margin": "0 22px 14px"}),

            html.Div([
                html.Div([
                    html.P("Disease share of total cases", style=S_CHART_TITLE),
                    html.P("Proportion of each reportable disease in the selected period", style=S_CHART_SUB),
                    dcc.Graph(id="chart-donut", config={"displayModeBar": False}, style={"height": "280px"}),
                ], style={**S_CARD, "flex": "1", "minWidth": "0"}),
                html.Div([
                    html.P("Monthly seasonal pattern", style=S_CHART_TITLE),
                    html.P("Case intensity by month and year; darker cells indicate more cases", style=S_CHART_SUB),
                    dcc.Graph(id="chart-heatmap", config={"displayModeBar": False}, style={"height": "280px"}),
                ], style={**S_CARD, "flex": "1", "minWidth": "0"}),
            ], className="two-column-grid"),
        ],
    )


def _forecast_tab() -> dcc.Tab:
    return dcc.Tab(
        label="Forecasts",
        value="forecasts",
        style=TAB_STYLE,
        selected_style=TAB_SELECTED_STYLE,
        children=[
            section("12-month disease outlook"),
            html.Div([
                html.Label("Disease", style={**S_LABEL, "marginRight": "6px"}),
                dcc.Dropdown(
                    id="f-hybrid-disease",
                    options=[{"label": disease, "value": disease} for disease in DISEASES],
                    value=DISEASES[0],
                    clearable=False,
                    style=S_DROP,
                ),
                html.Span(
                    "❓ not computed · ✓ ready · ⚠ notes · ❌ failed",
                    style={"fontSize": "10px", "color": "#888"},
                ),
                html.Div(id="forecast-data-source-badge"),
            ], className="forecast-filter-row"),

            html.Div(
                id="hybrid-metric-row",
                style={"display": "flex", "gap": "10px", "flexWrap": "wrap",
                       "padding": "0 22px", "marginBottom": "8px"},
            ),
            html.Div(id="hybrid-warnings-panel", style={"padding": "0 22px", "marginBottom": "14px"}),
            html.Div([
                html.Button(
                    "Download forecast CSV",
                    id="download-forecast-button",
                    n_clicks=0,
                    disabled=True,
                    title="Compute this disease forecast before downloading.",
                    className="download-button",
                ),
                html.Span(
                    "Use the camera icon on the chart toolbar to download a PNG.",
                    style={"fontSize": "10px", "color": "#777"},
                ),
                dcc.Download(id="download-forecast-csv"),
            ], className="forecast-download-row"),

            html.Div([
                html.P("Observed history and 12-month outlook", style=S_CHART_TITLE),
                html.P(
                    "The orange line is the selected forecast; the shaded area shows its 95% uncertainty range.",
                    style=S_CHART_SUB,
                ),
                dcc.Graph(
                    id="chart-hybrid-forecast",
                    config={"displayModeBar": True,
                            "displaylogo": False,
                            "toImageButtonOptions": {"format": "png", "filename": "antipolo-disease-forecast",
                                                     "scale": 2},
                            "modeBarButtonsToRemove": ["select2d", "lasso2d", "autoScale2d"]},
                    style={"height": "360px"},
                ),
            ], style={**S_CARD, "margin": "0 22px 14px"}),

            html.Details([
                html.Summary(
                    "Technical model details",
                    style={"cursor": "pointer", "fontSize": "13px", "fontWeight": "600", "color": TEXTC},
                ),
                html.P(
                    f"Backtesting, residual diagnostics, and seasonal decomposition. "
                    f"The reference MAPE is {BASELINE_MAPE}%.",
                    style={**S_CHART_SUB, "marginTop": "8px"},
                ),
                html.Div([
                    html.Div([
                        html.P("Backtest — last 12 held-out months", style=S_CHART_TITLE),
                        html.P("Actual cases compared with the candidate forecasts", style=S_CHART_SUB),
                        dcc.Graph(id="chart-backtest", config={"displayModeBar": False}, style={"height": "250px"}),
                    ], style={**S_CARD, "flex": "1", "minWidth": "0"}),
                    html.Div([
                        html.P("Residual diagnostics", style=S_CHART_TITLE),
                        html.P("Remaining forecast error and the non-linear pattern learned by NNAR", style=S_CHART_SUB),
                        dcc.Graph(id="chart-residual", config={"displayModeBar": False}, style={"height": "250px"}),
                    ], style={**S_CARD, "flex": "1", "minWidth": "0"}),
                ], className="technical-grid"),
                html.Div([
                    html.P("Seasonal decomposition", style=S_CHART_TITLE),
                    html.P("Observed cases separated into trend, seasonal, and residual components", style=S_CHART_SUB),
                    dcc.Graph(id="chart-decomp", config={"displayModeBar": False}, style={"height": "440px"}),
                ], style={**S_CARD, "marginTop": "14px"}),
            ], className="technical-details"),
        ],
    )


def _data_tab() -> dcc.Tab:
    return dcc.Tab(
        label="Data & quality",
        value="data-quality",
        style=TAB_STYLE,
        selected_style=TAB_SELECTED_STYLE,
        children=[
            section("Data source"),
            html.Div([
                html.Div([
                    html.P("Update surveillance data", style=S_CHART_TITLE),
                    html.P("Upload a validated CSV or DOH/PIDSR Excel workbook.", style=S_CHART_SUB),
                ]),
                dcc.Upload(
                    id="upload-csv",
                    children=html.Div([
                        html.Span("📂 ", style={"fontSize": "13px"}),
                        html.Span("Upload data", style={"fontSize": "12px", "color": "#185FA5"}),
                    ]),
                    style={"border": "1px dashed #378ADD", "borderRadius": "6px", "padding": "8px 14px",
                           "cursor": "pointer", "background": "#F0F7FF"},
                    accept=".csv,.xlsx",
                ),
                html.Div([
                    html.Label("Ambiguous date convention", style={**S_LABEL, "marginBottom": "4px"}),
                    dcc.Dropdown(
                        id="date-convention",
                        options=[
                            {"label": "Day first (DD/MM/YYYY)", "value": "day-first"},
                            {"label": "Month first (MM/DD/YYYY)", "value": "month-first"},
                            {"label": "Year first (YYYY/MM/DD)", "value": "year-first"},
                        ],
                        value="day-first",
                        clearable=False,
                        searchable=False,
                        style={**S_DROP, "width": "220px"},
                    ),
                ]),
                html.Div(id="upload-status", style={"fontSize": "11px", "color": "#666", "maxWidth": "480px"}),
            ], className="upload-card", style=S_CARD),

            section("Upload summary"),
            html.Div(
                id="upload-summary-content",
                children=html.P("Preparing data summary…", style={"fontSize": "12px", "color": "#888", "margin": "0"}),
                style={**S_CARD, "margin": "0 22px 18px"},
            ),

            section("Data table"),
            html.Div([
                html.P("Annual totals by disease", style=S_CHART_TITLE),
                html.P("Uses the reporting period and disease filters from the overview.", style=S_CHART_SUB),
                html.Div(id="data-table"),
            ], style={**S_CARD, "margin": "0 22px 14px"}),

            html.Details([
                html.Summary(
                    "Methodology and data limitations",
                    style={"cursor": "pointer", "fontSize": "12px", "fontWeight": "600", "color": TEXTC},
                ),
                html.P(
                    "This is city-wide surveillance with no school-level breakdown. Diseases without an uploaded "
                    "real source are backfilled with synthetic monthly data and labeled accordingly. Uploaded weekly "
                    "data is converted to months using the ISO week's Thursday. The 2020–2022 period is treated as a "
                    "structural break in mock data. Forecast models are trained on demand, cached for the session, and "
                    "recomputed after a new upload. The reporting-period control changes the displayed window but does "
                    "not retrain the model. The final forecast is whichever candidate performed better on the held-out "
                    "12-month backtest.",
                    style={"fontSize": "11px", "color": "#666", "lineHeight": "1.7", "margin": "10px 0 0"},
                ),
            ], className="methodology-details"),
        ],
    )


def build_layout() -> html.Div:
    return html.Div([
        dcc.Store(id="store-data", storage_type="session"),
        dcc.Store(id="store-hybrid", storage_type="session"),
        dcc.Store(id="store-upload-summary", storage_type="session"),

        html.Div([
            html.Div([
                html.Span("🛡 ", style={"fontSize": "17px"}),
                html.Div([
                    html.P("Antipolo City Disease Surveillance",
                           style={"fontWeight": "600", "fontSize": "15px", "color": TEXTC, "margin": "0"}),
                    html.P("City-wide monitoring and 12-month disease outlook",
                           style={"fontSize": "11px", "color": "#777", "margin": "0"}),
                ]),
            ], style={"display": "flex", "alignItems": "center", "gap": "10px"}),
            html.Span("DOH-PIDSR · Region 4-A", className="scope-badge"),
        ], style=S_TOPBAR, className="topbar"),

        html.Div([
            html.Div([
                html.Label("Reporting period", style=S_LABEL),
                dcc.RangeSlider(
                    id="f-year",
                    min=DATA_START_YEAR,
                    max=DATA_END_YEAR,
                    step=1,
                    value=[DATA_START_YEAR, DATA_END_YEAR],
                    marks={year: {"label": str(year), "style": {"fontSize": "10px", "color": "#777"}}
                           for year in range(DATA_START_YEAR, DATA_END_YEAR + 1, 2)},
                    tooltip={"placement": "bottom", "always_visible": False},
                    allow_direct_input=False,
                ),
                html.P("Applies to overview metrics, the data table, and the history shown with forecasts.",
                       style={"fontSize": "10px", "color": "#888", "margin": "5px 0 0"}),
            ], style={"width": "100%"}),
        ], className="reporting-period-card"),

        dcc.Tabs(
            id="dashboard-tabs",
            className="dashboard-tabs",
            value="overview",
            children=[_overview_tab(), _forecast_tab(), _data_tab()],
            style={"padding": "0 22px", "background": "white", "borderBottom": "1px solid rgba(0,0,0,0.08)"},
            colors={"border": "transparent", "primary": "#185FA5", "background": "white"},
        ),
    ], style={"fontFamily": FONT, "maxWidth": "1180px", "margin": "0 auto",
              "background": "#F5F5F3", "minHeight": "100vh"})
