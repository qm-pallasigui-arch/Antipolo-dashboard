"""
Callbacks that render the dashboard from whatever is currently in session
storage: the per-disease dropdown status icons, the hybrid forecast section,
and the cross-disease aggregate section.

LAZY COMPUTATION: `render_hybrid_section` computes a disease's SARIMA+NNAR fit
ON DEMAND -- only the disease currently selected in the dropdown, the first
time it's selected -- and caches the result in `store-hybrid`, keyed by
disease name. An earlier version eagerly fit all 7 diseases in a separate
`compute_hybrid` callback every time data loaded; on Render's free tier that
single request took 100x longer than expected (throttled shared CPU) and hit
gunicorn's worker timeout mid-fit. Fitting only what's actually being looked
at removes that failure mode entirely, regardless of hosting tier, and also
means the FIRST chart appears after ~1 disease's fit time instead of ~7.

Cache invalidation: `store-hybrid` also carries a `_signature` field (a hash
of the current dataset). If the dataset changes (new upload), the signature
no longer matches and the whole cache is discarded before recomputing --
otherwise a forecast fit on the OLD dataset could keep being shown after a
new file was uploaded.

`update_hybrid_section`/`render_hybrid_section` was originally a single
90-line function (radon cyclomatic complexity 13, grade C) mixing three
concerns: figuring out which "empty state" to show (no data / disease errored
/ cache unreadable), building the metric cards, and building the warnings
panel. Those are three small helpers, and the callback itself is a short
sequence of "check -> check -> compute-if-needed -> build -> return".
"""

import hashlib
import io

import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, State, html, dash_table

from dashboard.app_instance import app  # noqa: F401
from dashboard.config import DISEASES, BASELINE_MAPE, HOLDOUT_MONTHS, FORECAST_MONTHS
from dashboard.styles import FONT, TEXTC, PLOTBG
from dashboard.ui.components import metric
from dashboard.modeling.pipeline import run_hybrid_pipeline
from dashboard.modeling.serialization import serialize_pipeline_result, deserialize_pipeline_result
from dashboard.modeling.sarima import run_decomposition
from dashboard.charts.figures import (
    fig_hybrid_forecast, fig_backtest, fig_residual_diag, fig_decomposition,
    fig_donut, fig_seasonal_heatmap, fig_disease_bar, summary_cards,
)
from dashboard.logging_config import get_logger

logger = get_logger(__name__)

ERROR_PANEL_STYLE = {"background": "#FBEAEA", "color": "#A32D2D", "borderRadius": "8px",
                     "padding": "10px 14px", "fontSize": "12px"}
CACHE_SIGNATURE_KEY = "_signature"


def _empty_figure() -> go.Figure:
    fig = go.Figure()
    fig.update_layout(plot_bgcolor=PLOTBG, paper_bgcolor=PLOTBG, font=dict(family=FONT))
    return fig


def _placeholder_figure(title: str, height: int = 300) -> go.Figure:
    return go.Figure().update_layout(
        title=title, plot_bgcolor=PLOTBG, paper_bgcolor=PLOTBG,
        font=dict(family=FONT, color="#888", size=12), height=height,
    )


def _hybrid_not_ready_response(title: str):
    """Shape for the 'nothing to show yet' case -- not an error, just no data."""
    return [], [], _placeholder_figure(title), _empty_figure(), _empty_figure(), _empty_figure()


def _hybrid_error_response(placeholder_title: str, message: str):
    """Shared shape for every 'can't show this disease' case: empty metric
    row, a red error panel, one placeholder chart, and three blank charts."""
    error_panel = html.Div(message, style=ERROR_PANEL_STYLE)
    return [], error_panel, _placeholder_figure(placeholder_title), _empty_figure(), _empty_figure(), _empty_figure()


def _data_signature(store_json: str) -> str:
    """Stable fingerprint of the current dataset. Used to detect a new upload
    and invalidate any previously cached hybrid results, so the dashboard
    never mixes a forecast fit on the OLD dataset with a newly uploaded one."""
    return hashlib.sha256(store_json.encode("utf-8")).hexdigest()


def _get_or_compute_disease(cache: dict, df: pd.DataFrame, disease: str) -> dict:
    """Returns the cached serialized result for `disease` if present;
    otherwise fits it right now. This is the actual laziness: only the
    disease currently on screen is ever computed, not all 7 up front."""
    if disease in cache:
        return cache[disease]
    try:
        r = run_hybrid_pipeline(df, disease, holdout=HOLDOUT_MONTHS, forecast_steps=FORECAST_MONTHS)
        cache[disease] = serialize_pipeline_result(r)
        logger.info("computed disease=%s on demand", disease)
    except Exception:
        logger.exception("pipeline failed for disease=%s", disease)
        cache[disease] = {"error": "The forecast could not be computed for this disease."}
    return cache[disease]


def _build_hybrid_metric_cards(result: dict) -> html.Div:
    hybrid_mape = result["metrics"]["mape"]
    sarima_mape = result["sarima_only_metrics"]["mape"]
    final_mape = result["final_metrics"]["mape"]
    selected = result["selected_model"]
    data_source = result.get("data_source", "mock")
    model_tier = result.get("model_tier", "unknown")
    beat_baseline = final_mape < BASELINE_MAPE

    return html.Div([
        metric("Data source", "Real (DOH-PIDSR)" if data_source == "real" else "Synthetic mock",
               "uploaded workbook" if data_source == "real" else "no real upload for this disease yet",
               good=(True if data_source == "real" else None)),
        metric("Final model", "Hybrid" if selected == "hybrid" else "SARIMA-only",
               f"tier: {model_tier}", good=None),
        metric("Final RMSE", result["final_metrics"]["rmse"], "cases/month"),
        metric("Final MAE", result["final_metrics"]["mae"], "cases/month"),
        metric("Final MAPE", f"{final_mape}%", f"baseline is {BASELINE_MAPE}%", good=beat_baseline),
        metric("Hybrid MAPE", f"{hybrid_mape}%", "SARIMA + NNAR", good=None),
        metric("SARIMA-only MAPE", f"{sarima_mape}%", "before NNAR correction", good=None),
    ], style={"display": "flex", "gap": "10px", "flexWrap": "wrap"})


def _build_warnings_panel(pipeline_warnings: list, disease: str):
    if not pipeline_warnings:
        return html.Div(
            f"\u2713 No model warnings for {disease} -- clean SARIMA + NNAR fit on both backtest and production legs.",
            style={"background": "#EFF7EE", "color": "#3B6D11", "borderRadius": "8px",
                  "padding": "8px 14px", "fontSize": "11px"},
        )
    return html.Details([
        html.Summary(f"\u26a0 {len(pipeline_warnings)} model note(s) for {disease} -- click to expand",
                    style={"cursor": "pointer", "color": "#A3702D", "fontSize": "12px", "fontWeight": "500"}),
        html.Ul([html.Li(w, style={"fontSize": "11px", "color": "#888", "marginBottom": "3px"})
                for w in pipeline_warnings], style={"margin": "8px 0 0", "paddingLeft": "18px"}),
    ], style={"background": "#FFF8EC", "borderRadius": "8px", "padding": "10px 14px"})


def _build_decomposition_chart(series):
    decomp, decomp_reason = run_decomposition(series)
    if decomp is None:
        return _placeholder_figure(decomp_reason or "Decomposition unavailable", height=440)
    return fig_decomposition(decomp)


def _render_hybrid_charts(result: dict, disease: str, year_range):
    """Build all hybrid-section outputs, returning a safe error response on failure."""
    try:
        metrics_row = _build_hybrid_metric_cards(result)
        warnings_panel = _build_warnings_panel(result.get("warnings_log", []), disease)
        chart_forecast = fig_hybrid_forecast(result, year_range)
        chart_backtest = fig_backtest(result)
        chart_residual = fig_residual_diag(result)
        chart_decomp = _build_decomposition_chart(result["series"])
    except Exception:
        logger.exception("could not render hybrid section for disease=%s", disease)
        return None
    return metrics_row, warnings_panel, chart_forecast, chart_backtest, chart_residual, chart_decomp


def _prepare_hybrid_entry(store_json: str, disease: str, cache: dict):
    """Invalidate stale cache data and lazily create the selected disease entry."""
    cache = cache if isinstance(cache, dict) else {}
    signature = _data_signature(store_json)
    if cache.get(CACHE_SIGNATURE_KEY) != signature:
        logger.info("dataset changed -- clearing cached hybrid results")
        cache = {CACHE_SIGNATURE_KEY: signature}

    if disease not in cache:
        try:
            df = pd.read_json(io.StringIO(store_json), orient="split")
            df["date"] = pd.to_datetime(df["date"])
            if "source" not in df.columns:
                df["source"] = "real"
        except Exception:
            logger.exception("could not read stored data")
            return cache, None, "Could not read the stored data. Try refreshing or re-uploading your file."
        _get_or_compute_disease(cache, df, disease)
    return cache, cache[disease], None


@app.callback(
    Output("f-hybrid-disease", "options"),
    Input("store-hybrid", "data"),
)
def update_hybrid_dropdown_status(store_hybrid):
    """Status icon per disease, right in the dropdown: not-yet-computed
    (the normal, expected state under lazy computation, not a loading
    flicker) / error / has-warnings / clean."""
    options = []
    for d in DISEASES:
        icon = "\u2753"
        if isinstance(store_hybrid, dict) and d in store_hybrid:
            entry = store_hybrid[d]
            if not isinstance(entry, dict):
                icon = "\u274c"
            elif "error" in entry:
                icon = "\u274c"
            elif entry.get("warnings_log"):
                icon = "\u26a0"
            else:
                icon = "\u2713"
        options.append({"label": f"{icon} {d}", "value": d})
    return options


@app.callback(
    Output("store-hybrid", "data"),
    Output("hybrid-metric-row", "children"),
    Output("hybrid-warnings-panel", "children"),
    Output("chart-hybrid-forecast", "figure"),
    Output("chart-backtest", "figure"),
    Output("chart-residual", "figure"),
    Output("chart-decomp", "figure"),
    Input("store-data", "data"),
    Input("f-hybrid-disease", "value"),
    Input("f-year", "value"),
    State("store-hybrid", "data"),
)
def render_hybrid_section(store_json, disease, year_range, cache):
    """Renders the hybrid section for whichever disease is selected, fitting
    it on demand if it isn't already cached for the current dataset."""
    if store_json is None:
        return {}, *_hybrid_not_ready_response("No data loaded yet.")

    cache, entry, preparation_error = _prepare_hybrid_entry(store_json, disease, cache)
    if preparation_error:
        return cache, *_hybrid_error_response("Could not read stored data", f"\u274c {preparation_error}")

    if not isinstance(entry, dict):
        return cache, *_hybrid_error_response(
            f"Cached result for {disease} is unreadable",
            f"\u274c Could not read the cached result for {disease}. Please refresh the page or re-upload your file.",
        )

    if "error" in entry:
        return cache, *_hybrid_error_response(
            f"Could not build a forecast for {disease}",
            f"\u274c {disease}: {entry['error']}",
        )

    # Defensive deserialization: session storage may hold results from a
    # previous version of this app whose schema doesn't match anymore.
    # Fail loudly-but-gracefully instead of crashing the whole page.
    try:
        result = deserialize_pipeline_result(entry)
    except Exception:
        logger.exception("could not deserialize cached result for disease=%s", disease)
        return cache, *_hybrid_error_response(
            f"Cached result for {disease} is unreadable",
            f"\u274c Could not read the cached result for {disease}. "
            "This usually means the app was updated since this browser session started -- "
            "please refresh the page or re-upload your file.",
        )

    rendered = _render_hybrid_charts(result, disease, year_range)
    if rendered is None:
        return cache, *_hybrid_error_response(
            f"Could not render a forecast for {disease}",
            f"\u274c Could not render the forecast for {disease}. Please refresh or re-upload your file.",
        )
    metrics_row, warnings_panel, chart_forecast, chart_backtest, chart_residual, chart_decomp = rendered

    return cache, metrics_row, warnings_panel, chart_forecast, chart_backtest, chart_residual, chart_decomp


def _build_aggregate_metric_cards(dff: pd.DataFrame) -> html.Div:
    total, peak_year, peak_val, top_dis, top_pct, yrs = summary_cards(dff)
    real_diseases = sorted(dff.loc[dff.get("source", "mock") == "real", "disease"].unique().tolist())
    return html.Div([
        metric("Total cases", f"{total:,}", f"({yrs})"),
        metric("Peak year", str(peak_year), f"{peak_val:,} cases"),
        metric("Top disease", top_dis, f"{top_pct}% of cases"),
        metric("COVID years", "2020\u201322", "Structural break"),
        metric("Scope", "Antipolo City", "City-wide"),
        metric("Real data", str(len(real_diseases)) if real_diseases else "0",
               ", ".join(real_diseases) if real_diseases else "none uploaded yet"),
    ], style={"display": "flex", "gap": "10px", "flexWrap": "wrap"})


def _build_data_table(dff: pd.DataFrame) -> dash_table.DataTable:
    table_df = (
        dff.groupby(["year", "disease"])["cases"].sum().reset_index()
        .pivot(index="disease", columns="year", values="cases").fillna(0).astype(int).reset_index()
    )
    table_df.columns = [str(c) for c in table_df.columns]

    return dash_table.DataTable(
        data=table_df.to_dict("records"),
        columns=[{"name": c, "id": c} for c in table_df.columns],
        style_table={"overflowX": "auto"},
        style_header={"backgroundColor": "#F5F5F5", "fontWeight": "500", "fontSize": "11px",
                      "color": "#555", "border": "none", "padding": "8px 12px"},
        style_cell={"fontSize": "12px", "fontFamily": FONT, "color": TEXTC, "padding": "7px 12px",
                   "border": "none", "borderBottom": "0.5px solid rgba(0,0,0,0.06)"},
        style_data_conditional=[{"if": {"row_index": "odd"}, "backgroundColor": "#FAFAFA"}],
        page_size=10, sort_action="native",
    )


@app.callback(
    Output("metric-row", "children"),
    Output("chart-donut", "figure"),
    Output("chart-heatmap", "figure"),
    Output("chart-bar", "figure"),
    Output("data-table", "children"),
    Input("store-data", "data"),
    Input("f-year", "value"),
    Input("f-disease", "value"),
)
def update_aggregate_section(store_json, year_range, disease):
    """Cross-disease charts and totals, unaffected by which disease is
    selected in the hybrid-forecast section above."""
    if store_json is None:
        return [], _empty_figure(), _empty_figure(), _empty_figure(), []

    try:
        df = pd.read_json(io.StringIO(store_json), orient="split")
        df["date"] = pd.to_datetime(df["date"])
        if "source" not in df.columns:
            df["source"] = "real"
    except Exception:
        logger.exception("could not read stored data in aggregate section")
        error_msg = html.Div(
            "\u274c Could not read the stored data. Try refreshing or re-uploading your file.",
            style=ERROR_PANEL_STYLE,
        )
        return [error_msg], _empty_figure(), _empty_figure(), _empty_figure(), []

    yr_min, yr_max = year_range
    dff = df[(df["year"] >= yr_min) & (df["year"] <= yr_max)].copy()
    if disease != "all":
        dff = dff[dff["disease"] == disease]

    if dff.empty:
        return [], _empty_figure(), _empty_figure(), _empty_figure(), []

    try:
        metrics = _build_aggregate_metric_cards(dff)
        chart_donut = fig_donut(dff)
        chart_heatmap = fig_seasonal_heatmap(dff)
        chart_bar = fig_disease_bar(dff)
        table = _build_data_table(dff)
    except Exception:
        logger.exception("could not render aggregate section")
        error_msg = html.Div(
            "\u274c Could not render the aggregate dashboard for this data.",
            style=ERROR_PANEL_STYLE,
        )
        return [error_msg], _empty_figure(), _empty_figure(), _empty_figure(), []

    return metrics, chart_donut, chart_heatmap, chart_bar, table
