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
from dash import Input, Output, State, dcc, html, dash_table
from dash.exceptions import PreventUpdate

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


def _read_store_frame(store_json: str) -> pd.DataFrame:
    df = pd.read_json(io.StringIO(store_json), orient="split")
    df["date"] = pd.to_datetime(df["date"])
    if "source" not in df.columns:
        df["source"] = "real"
    return df


def _build_source_indicators(store_json: str, forecast_disease: str):
    if not store_json:
        empty = html.Div(
            "Data source unavailable until the dataset loads.",
            className="data-source-banner",
            style={"background": "#F5F5F5", "color": "#666"},
        )
        return empty, html.Span("Source unavailable", className="source-badge")
    try:
        df = _read_store_frame(store_json)
    except Exception:
        logger.exception("could not read stored data for source indicators")
        error = html.Div(
            "Data source could not be verified. Refresh or re-upload before using these results.",
            className="data-source-banner",
            style={"background": "#FBEAEA", "color": "#A32D2D"},
        )
        return error, html.Span(
            "Source unverified", className="source-badge",
            style={"background": "#FBEAEA", "color": "#A32D2D"},
        )

    real = sorted(df.loc[df["source"] == "real", "disease"].dropna().unique().tolist())
    mock = sorted(df.loc[df["source"] != "real", "disease"].dropna().unique().tolist())
    if real and mock:
        text = f"MIXED DATA — {len(real)} disease(s) use uploaded records; {len(mock)} use synthetic mock data."
        colors = {"background": "#FFF3D6", "color": "#7A4D00", "border": "1px solid #E8C36A"}
    elif real:
        text = f"UPLOADED DATA — all {len(real)} available disease series use uploaded records."
        colors = {"background": "#EFF7EE", "color": "#3B6D11", "border": "1px solid #B8D7B2"}
    else:
        text = f"SYNTHETIC DATA — all {len(mock)} disease series are generated mock data."
        colors = {"background": "#FFF3D6", "color": "#7A4D00", "border": "1px solid #E8C36A"}

    disease_rows = df[df["disease"] == forecast_disease]
    is_real = not disease_rows.empty and (disease_rows["source"] == "real").any()
    badge = html.Span(
        "Uploaded real data" if is_real else "Synthetic mock",
        className="source-badge",
        style={
            "background": "#EFF7EE" if is_real else "#FFF3D6",
            "color": "#3B6D11" if is_real else "#7A4D00",
            "border": "1px solid #B8D7B2" if is_real else "1px solid #E8C36A",
        },
    )
    return html.Div(text, className="data-source-banner", style=colors), badge


@app.callback(
    Output("global-data-source-banner", "children"),
    Output("forecast-data-source-badge", "children"),
    Input("store-data", "data"),
    Input("f-hybrid-disease", "value"),
)
def render_data_source_indicators(store_json, forecast_disease):
    return _build_source_indicators(store_json, forecast_disease)


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
        metric("Data source", "Uploaded real data" if data_source == "real" else "Synthetic mock",
               "uploaded surveillance data" if data_source == "real" else "no real upload for this disease yet",
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


def _build_upload_warnings_panel(notes: list):
    """Use the model-warning Details/Summary treatment for upload quality."""
    informational_prefixes = (
        "No data-quality issues",
        "Matched sheet",
        "No upload yet",
        "Upload summary was regenerated",
        "Used the supplied",
        "Parsed '",
        "Converted ISO",
        "Imported tabular",
        "Interpreted ",
        "Aggregated ",
    )
    warnings = [note for note in notes if not note.startswith(informational_prefixes)]
    if not warnings:
        return html.Div(
            "\u2713 No data-quality warnings found for the active data.",
            style={"background": "#EFF7EE", "color": "#3B6D11", "borderRadius": "8px",
                   "padding": "8px 14px", "fontSize": "11px"},
        )
    return html.Details([
        html.Summary(
            f"\u26a0 {len(warnings)} data-quality warning(s) -- click to expand",
            style={"cursor": "pointer", "color": "#A3702D", "fontSize": "12px", "fontWeight": "500"},
        ),
        html.Ul([
            html.Li(warning, style={"fontSize": "11px", "color": "#888", "marginBottom": "3px"})
            for warning in warnings
        ], style={"margin": "8px 0 0", "paddingLeft": "18px"}),
    ], style={"background": "#FFF8EC", "borderRadius": "8px", "padding": "10px 14px"})


def _table_style(page_size: int = 10) -> dict:
    """Shared DataTable presentation used by previews throughout the page."""
    return {
        "style_table": {"overflowX": "auto"},
        "style_header": {"backgroundColor": "#F5F5F5", "fontWeight": "500", "fontSize": "11px",
                         "color": "#555", "border": "none", "padding": "8px 12px"},
        "style_cell": {"fontSize": "12px", "fontFamily": FONT, "color": TEXTC, "padding": "7px 12px",
                       "border": "none", "borderBottom": "0.5px solid rgba(0,0,0,0.06)"},
        "style_data_conditional": [{"if": {"row_index": "odd"}, "backgroundColor": "#FAFAFA"}],
        "page_size": page_size,
        "sort_action": "native",
    }


def _build_summary_disease_table(diseases: list) -> dash_table.DataTable:
    records = []
    for disease in diseases:
        year_min, year_max = disease.get("year_min"), disease.get("year_max")
        year_range = "—" if year_min is None else (
            str(year_min) if year_min == year_max else f"{year_min}–{year_max}"
        )
        records.append({
            "disease": disease.get("name", ""),
            "source": "Real" if disease.get("source") == "real" else "Synthetic mock",
            "row_count": disease.get("row_count", 0),
            "year_range": year_range,
        })
    table_style = _table_style(page_size=max(len(records), 1))
    table_style["style_data_conditional"] += [
        {"if": {"filter_query": '{source} = "Real"', "column_id": "source"},
         "backgroundColor": "#EFF7EE", "color": "#3B6D11", "fontWeight": "500"},
        {"if": {"filter_query": '{source} = "Synthetic mock"', "column_id": "source"},
         "backgroundColor": "#F5F5F5", "color": "#888"},
    ]
    return dash_table.DataTable(
        data=records,
        columns=[
            {"name": "Disease", "id": "disease"},
            {"name": "Source", "id": "source"},
            {"name": "Rows", "id": "row_count", "type": "numeric"},
            {"name": "Year range", "id": "year_range"},
        ],
        **table_style,
    )


def _build_upload_preview_table(preview: list) -> dash_table.DataTable:
    columns = ["year", "month", "disease", "cases", "source"]
    return dash_table.DataTable(
        data=preview,
        columns=[{"name": column.replace("_", " ").title(), "id": column} for column in columns],
        **_table_style(page_size=5),
    )


@app.callback(
    Output("upload-summary-content", "children"),
    Input("store-upload-summary", "data"),
)
def render_upload_summary(summary):
    if not summary:
        return html.P("No upload summary is available yet.", style={"fontSize": "12px", "color": "#888"})

    success = bool(summary.get("success"))
    uploaded = bool(summary.get("uploaded"))
    filename = summary.get("filename") or "Unknown file"
    loaded_at = summary.get("loaded_at", "")
    try:
        display_time = pd.Timestamp(loaded_at).strftime("%Y-%m-%d %H:%M UTC") if loaded_at else ""
    except (TypeError, ValueError):
        display_time = str(loaded_at)
    if success and uploaded:
        status_text, status_color = f"\u2713 Upload ready: {filename}", "#3B6D11"
    elif success:
        status_text, status_color = "\U0001F4CA No upload yet — using built-in synthetic data", "#185FA5"
    else:
        status_text, status_color = f"\u274c Upload failed: {filename}", "#A32D2D"

    year_min, year_max = summary.get("year_min"), summary.get("year_max")
    coverage = "No usable date range" if year_min is None else (
        str(year_min) if year_min == year_max else f"{year_min}–{year_max}"
    )
    header = html.Div([
        html.Div([
            html.P(status_text, style={"fontSize": "14px", "fontWeight": "500", "color": status_color,
                                       "margin": "0 0 3px"}),
            html.P(f"Coverage: {coverage}", style={"fontSize": "11px", "color": "#888", "margin": "0"}),
        ]),
        html.P(f"Loaded {display_time}" if display_time else "", style={"fontSize": "11px", "color": "#888",
                                                                    "margin": "0"}),
    ], style={"display": "flex", "justifyContent": "space-between", "gap": "12px", "flexWrap": "wrap"})

    children = [header]
    diseases = summary.get("diseases") or []
    if diseases:
        children.extend([
            html.P("Disease coverage", style={"fontSize": "12px", "fontWeight": "500", "margin": "14px 0 6px"}),
            _build_summary_disease_table(diseases),
        ])
    children.extend([
        html.Div(_build_upload_warnings_panel(summary.get("warnings") or []), style={"marginTop": "12px"}),
    ])
    preview = summary.get("preview") or []
    if preview:
        children.extend([
            html.P("Uploaded data preview" if uploaded else "Synthetic data preview",
                   style={"fontSize": "12px", "fontWeight": "500", "margin": "14px 0 2px"}),
            html.P("First 10 validated rows; 5 shown per page.",
                   style={"fontSize": "11px", "color": "#888", "margin": "0 0 6px"}),
            _build_upload_preview_table(preview),
        ])
    return children


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
            df = _read_store_frame(store_json)
        except Exception:
            logger.exception("could not read stored data")
            return cache, None, "Could not read the stored data. Try refreshing or re-uploading your file."
        _get_or_compute_disease(cache, df, disease)
    return cache, cache[disease], None


def _build_forecast_export(entry: dict, disease: str) -> pd.DataFrame:
    result = deserialize_pipeline_result(entry)
    records = [
        {
            "disease": disease, "date": index, "record_type": "observed",
            "observed_cases": float(value), "forecast_cases": None,
            "lower_95": None, "upper_95": None,
        }
        for index, value in result["series"].items()
    ]
    forecast_index = result["final_forecast"].index
    records.extend(
        {
            "disease": disease, "date": index, "record_type": "forecast",
            "observed_cases": None, "forecast_cases": float(result["final_forecast"].loc[index]),
            "lower_95": float(result["ci_lower"].reindex(forecast_index).loc[index]),
            "upper_95": float(result["ci_upper"].reindex(forecast_index).loc[index]),
        }
        for index in forecast_index
    )
    exported = pd.DataFrame.from_records(records)
    exported["date"] = pd.to_datetime(exported["date"]).dt.strftime("%Y-%m-%d")
    exported["selected_model"] = result["selected_model"]
    exported["data_source"] = result.get("data_source", "mock")
    return exported


@app.callback(
    Output("download-forecast-button", "disabled"),
    Output("download-forecast-button", "title"),
    Input("store-hybrid", "data"),
    Input("f-hybrid-disease", "value"),
)
def update_forecast_download_state(cache, disease):
    entry = cache.get(disease) if isinstance(cache, dict) else None
    required = {"series", "final_forecast", "ci_lower", "ci_upper", "selected_model"}
    ready = isinstance(entry, dict) and "error" not in entry and required.issubset(entry)
    title = (
        "Download observed history, forecast, uncertainty bounds, model, and source."
        if ready else "Compute this disease forecast before downloading."
    )
    return not ready, title


@app.callback(
    Output("download-forecast-csv", "data"),
    Input("download-forecast-button", "n_clicks"),
    State("store-hybrid", "data"),
    State("f-hybrid-disease", "value"),
    prevent_initial_call=True,
)
def download_forecast_csv(n_clicks, cache, disease):
    if not n_clicks or not isinstance(cache, dict):
        raise PreventUpdate
    entry = cache.get(disease)
    if not isinstance(entry, dict) or "error" in entry:
        raise PreventUpdate
    try:
        exported = _build_forecast_export(entry, disease)
    except Exception as exc:
        logger.warning("could not export forecast for disease=%s: %s", disease, exc)
        raise PreventUpdate from exc
    safe_name = "-".join(str(disease).lower().replace("&", "and").split())
    return dcc.send_data_frame(exported.to_csv, f"{safe_name}-forecast.csv", index=False)


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
        **_table_style(page_size=10),
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
        df = _read_store_frame(store_json)
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
