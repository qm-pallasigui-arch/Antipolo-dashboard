"""
Central configuration: built-in sample diseases, model hyperparameters, and thresholds.

This module has ZERO dependencies on any other module in this package -- every
other module may import from here, but this file must never import from them.
Keeping that one-directional rule is what keeps the rest of the package free
of circular imports.
"""

# These names seed the initial synthetic demo only. Upload validation is open
# to arbitrary nonblank disease labels and never treats this list as a whitelist.
DISEASES = [
    "Dengue",
    "Acute Respiratory Infection",
    "Influenza-like Illness",
    "Tuberculosis",
    "Hand Foot & Mouth Disease",
    "Measles-Rubella",
    "Leptospirosis",
]

DISEASE_COLORS = {
    "Dengue":                      "#378ADD",
    "Acute Respiratory Infection": "#1D9E75",
    "Influenza-like Illness":      "#EF9F27",
    "Tuberculosis":                "#D85A30",
    "Hand Foot & Mouth Disease":   "#D4537E",
    "Measles-Rubella":                     "#7F77DD",
    "Leptospirosis":               "#3E8E7E",
}

# Optional aliases for historically supported DOH/PIDSR worksheet names.
# Unlisted worksheets with a valid Morbidity Week table are also imported.
# Preserve the source combined category pending clinical classification approval.
REAL_SHEET_TO_DISEASE = {
    "Dengue": "Dengue",
    "Measles-Rubella": "Measles-Rubella",
    "Leptospirosis": "Leptospirosis",
}

# Relative seasonal weight per calendar month, used ONLY for synthetic mock generation.
SEASONAL_WEIGHTS = [0.55, 0.50, 0.60, 0.65, 0.85,
                    1.30, 1.50, 1.65, 1.60, 1.40, 0.90, 0.62]

# Relative weight per disease, used ONLY for synthetic mock generation
# (real uploaded data is used as-is, un-weighted).
DISEASE_WEIGHTS = [0.30, 0.22, 0.17, 0.12, 0.08, 0.05, 0.06]

DATA_START_YEAR = 2016
DATA_END_YEAR = 2025            # inclusive -> exactly 120 months of mock history
HOLDOUT_MONTHS = 12             # backtest window
HISTORICAL_REFERENCE_MAPE = 32.22  # external/thesis reference figure, not computed from the active dataset; see thesis manuscript for source
SELECTION_FOLDS = 2             # rolling 12-month folds before the untouched final holdout
HYBRID_MIN_WAPE_GAIN_PP = 1.0   # deprecated historical constant; unused by mandatory-hybrid pipeline
FORECAST_MONTHS = 12            # production forecast horizon
NNAR_LAGS = 3                   # lagged residual window fed to the NNAR (kept small -- see note below)
NNAR_HIDDEN = (4,)              # single small hidden layer
NNAR_ALPHA = 10.0               # strong L2 regularization

# NOTE ON NNAR SIZING: SARIMA residuals are, by design, close to white noise once
# the model fits well -- there is often very little non-linear structure left for
# a neural net to learn. A large/unregularized net (many lags, big hidden layer)
# will happily overfit that noise, and because the forecast is recursive (each
# predicted residual feeds the next step), that overfit error compounds and can
# make the "hybrid" forecast WORSE than SARIMA alone. Keeping the net small and
# heavily regularized. SARIMA-only remains a benchmark; hybrid is the mandatory
# primary architecture and its measured performance need not exceed benchmarks.

# Deployment settings, overridable via environment variables (see app.py).
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8050

# Public-upload resource limits. These protect the single Gunicorn worker from
# oversized base64 payloads and workbook expansion before model fitting begins.
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_CSV_ROWS = 100_000
MAX_WORKBOOK_SHEETS = 20
MAX_WORKSHEET_ROWS = 10_000
MAX_WORKSHEET_COLUMNS = 250
MAX_WORKBOOK_CELLS = 1_000_000
