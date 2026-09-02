"""Small reusable Dash HTML components shared by layout.py and the callbacks
that populate it at runtime."""

from dash import html

from dashboard.styles import S_LABEL, S_VAL, S_DELTA, S_METRIC, S_SEC


def metric(label, val, delta=None, good=None):
    """good=True -> green (beat baseline/positive); good=False -> red; good=None -> neutral."""
    color = "#3B6D11" if good is True else ("#A32D2D" if good is False else "#888")
    arrow = "\u2713 " if good is True else ("\u26a0 " if good is False else "")
    return html.Div([
        html.P(label, style=S_LABEL),
        html.P(str(val), style=S_VAL),
        html.P(f"{arrow}{delta}" if delta else "", style={**S_DELTA, "color": color}),
    ], style=S_METRIC)


def section(text):
    return html.P(text, style=S_SEC)
