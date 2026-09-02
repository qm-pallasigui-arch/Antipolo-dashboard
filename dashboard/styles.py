"""
Visual constants shared by chart builders (dashboard/charts/) and the page
layout (dashboard/ui/layout.py). Pure style data -- no logic, no Dash imports.
"""

import pandas as pd

FONT = "Inter, Segoe UI, Arial, sans-serif"
TEXTC = "#333333"
GRIDC = "rgba(0,0,0,0.06)"
PLOTBG = "white"

COVID_START = pd.Timestamp("2020-03-01")
COVID_END = pd.Timestamp("2022-12-01")

S_TOPBAR = {
    "display": "flex", "justifyContent": "space-between", "alignItems": "center",
    "padding": "13px 22px", "borderBottom": "0.5px solid rgba(0,0,0,0.08)",
    "marginBottom": "18px", "background": "white",
}
S_CARD = {"background": "white", "border": "0.5px solid rgba(0,0,0,0.08)", "borderRadius": "10px", "padding": "16px"}
S_METRIC = {"background": "#F7F7F5", "borderRadius": "8px", "padding": "13px 16px", "flex": "1", "minWidth": "120px"}
S_LABEL = {"fontSize": "10px", "color": "#888", "margin": "0 0 5px", "textTransform": "uppercase", "letterSpacing": "0.05em"}
S_VAL = {"fontSize": "21px", "fontWeight": "500", "color": TEXTC, "margin": "0"}
S_DELTA = {"fontSize": "11px", "margin": "3px 0 0"}
S_SEC = {
    "fontSize": "10px", "fontWeight": "600", "color": "#888", "textTransform": "uppercase",
    "letterSpacing": "0.07em", "padding": "0 22px", "marginBottom": "8px", "marginTop": "18px",
}
S_CHART_TITLE = {"fontSize": "13px", "fontWeight": "500", "color": TEXTC, "margin": "0 0 2px"}
S_CHART_SUB = {"fontSize": "11px", "color": "#888", "margin": "0 0 10px"}
S_DROP = {"fontSize": "13px", "width": "220px"}
