<!-- @format -->

# Antipolo City Disease Surveillance — Hybrid Forecast Dashboard

A Dash prototype with separate synthetic demonstrations and uploaded surveillance datasets.
The primary forecast is always SARIMA + NNAR residual correction. SARIMA-only and seasonal
naive are benchmarks; lower benchmark error never replaces the hybrid. Disease-specific
SARIMA identification uses training-window diagnostics and bounded candidate fitting.
A failed component produces an explicit unavailable result.

Start the research review at [CHATGPT_RETURN_HANDOFF.md](CHATGPT_RETURN_HANDOFF.md).
The approved population is ages 5-19, confirmed cases only; the supplied original reports
support only a separately labeled all-age evaluation with unverified case classification.
Measles-Rubella remains a combined provisional category. The disease set and 12-month
operational horizon remain subject to expert review.

## Package structure

```
app.py                          # entrypoint: wires app_instance + layout + callbacks together
dashboard/
  app_instance.py                # the shared Dash `app` object (breaks circular imports)
  config.py                      # sample diseases, model hyperparameters, thresholds
  styles.py                      # visual constants (fonts, colors, CSS-in-JS dicts)
  logging_config.py              # operator-facing logging (separate from the UI's own warnings)
  data/
    date_parser.py                # flexible dates -> canonical monthly observations
    mock_data.py                  # synthetic fallback generator
    pdf_converter.py              # offline text-PDF table conversion + audit report
    xlsx_parser.py                 # real DOH/PIDSR workbook parser
    validation.py                  # disease-label + numeric/range validation
    combine.py                     # finalizes an authoritative uploaded dataset
  modeling/
    series_utils.py                # monthly series shaping, train/test split
    sarima.py                      # bounded SARIMA identification, diagnostics and explicit failures
    nnar.py                        # neural net on SARIMA residuals
    metrics.py                     # RMSE/MAE/MAPE, hybrid recombination
    pipeline.py                    # mandatory hybrid + separate benchmarks + full-history refit
    serialization.py               # (de)serialization for session storage
  charts/figures.py               # every Plotly figure builder
  ui/
    components.py                  # small reusable Dash components
    layout.py                      # build_layout() -- the full page tree
  callbacks/
    data_callbacks.py              # file upload -> normalize -> validate -> combine
    view_callbacks.py              # source labels, lazy forecasts, exports, aggregate views
tests/                           # pytest regression suite
```

### Why it's split this way

This used to be a single 1,415-line file. Four functions had grown too complex
(radon cyclomatic complexity 11–21, grade C/D): `load_data`,
`parse_surveillance_xlsx`, `update_hybrid_section`, and `run_hybrid_pipeline`.
Each is now an orchestrator calling single-purpose helpers. Historical complexity reports predate the revised identification procedure.

The `app_instance.py` split exists specifically to avoid a circular import:
`layout.py` and `callbacks/` both need the same `app` object, but if `app.py`
imported both of them to wire things up, and they in turn imported `app` back
from `app.py`, that's a cycle. Pulling the bare `Dash(...)` construction into
its own tiny module lets everyone import it one-directionally.

## Local development

```bash
pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:8050`. Override host/port/debug via environment
variables if needed:

```bash
HOST=0.0.0.0 PORT=9000 DASH_DEBUG=false python app.py
```

## Running tests

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

## Supported uploads and date conventions

CSV and XLSX uploads may use `year`/`month`, `year`/`week`, or a supported date
column such as `date`, `report_date`, or `reporting_period`. Before uploading,
select how ambiguous numeric dates should be interpreted: day first, month
first, or year first. ISO dates, timestamps, textual dates/months, and Excel
date serials are recognized automatically. Daily and weekly records are summed
to monthly totals before validation and modeling.

The specialized DOH/PIDSR week-by-year workbook layout remains supported. A
flat, row-based XLSX sheet is used as a fallback when the specialized layout is
not present. In a week-by-year workbook, every worksheet with a usable
`Morbidity Week` table is imported and its sheet name becomes the disease
label; the original seven names are not an upload whitelist.

A parsed upload first appears in **Upload summary** with its full validated disease list.
Only clicking **Use these N diseases** replaces the active disease catalog for that
browser session. Until confirmation, the previous session data (or sample) stays active.
A replacement upload supersedes the pending candidate; reset clears it, and refresh
discards unconfirmed data. Arbitrary labels, including PDF/ICD-10 categories, remain allowed. Disease selectors, charts, summaries, forecasts, and reporting years
are rebuilt from the uploaded values. Use **Reset to sample data** to erase the
active upload from the session and restore the seven synthetic examples.
Blank/invalid disease labels and all other rejected rows are reported visibly
in the upload status and summary.

Forecasting requires at least 72 consecutive, unique, explicitly observed monthly rows
under the default two earlier 12-month diagnostic folds plus a final 12-month holdout.
Invalid counts, duplicates, mixed populations/case classifications/sources, monthly gaps,
and known incomplete weekly coverage block modeling. Explicit zeros remain observations.
Week-to-month assignment is provisional ISO Thursday, with non-ISO week 53 assigned to
December; its official meaning and completeness await CHO confirmation.

For 2016-2025 data, earlier evaluation years are 2023 and 2024; final evaluation is 2025;
production refits 2016-2025 for 2026. Each fit identifies SARIMA using only that fit's
training history. Earlier-fold errors are diagnostic and do not gate the hybrid.
The 2025 holdout is excluded from algorithmic identification, but historical developers
have already seen its results: this is not a newly unseen prospective validation set.

RMSE, MAE, MAPE and WAPE describe holdout error. MAPE excludes zero actuals with denominator
coverage reported; WAPE is undefined if total absolute actuals are zero. The shaded region
is the maximum of 36 historical absolute hybrid errors, not a validated 95% prediction interval.
Exports include raw SARIMA/NNAR components, clipped primary counts, benchmarks, source,
population, classification, model search, warnings and evaluation metadata.

## Converting text-based PDF tables

PDF extraction runs offline rather than inside the dashboard request path:

```bash
python -m dashboard.data.pdf_converter source.pdf converted.csv --date-convention day-first
```

Use an `.xlsx` destination instead of `.csv` when desired. The command writes
the converted file and a neighboring `<output>.report.json`. Review the totals,
rejected tables, scope warnings, dashboard-compatible disease list, and source
PDF before uploading the converted file. The canonical conversion and the
dashboard preserve all valid disease categories. Do not upload when the report says
`"dashboard_ready": false`; resolve its `dashboard_blockers` first.
Scanned PDFs are not supported because this converter deliberately does not
perform OCR.

## Deployment

The Dash/Flask **development server** (`app.run()`) is single-threaded and
not meant for production traffic. Everything below runs the app through
**gunicorn** instead, targeting `app:server` — the plain Flask WSGI app that
`dashboard/app_instance.py` exposes (`server = app.server`).

Note on state: session data lives in the browser (`dcc.Store(storage_type=
"session")`), not on the server, so it's safe to run multiple gunicorn
workers — no session affinity / sticky-sessions requirement.

### Option A — plain gunicorn on a VM

```bash
pip install -r requirements.txt
gunicorn app:server --bind 0.0.0.0:8050 --workers 1 --timeout 600
```

Put this behind nginx/Caddy for TLS termination in front of it, as usual for
any Flask app. A systemd unit or `tmux`/`screen` session keeps it running
after you disconnect.

### Option B — Docker

```bash
docker build -t antipolo-surveillance .
docker run -p 8050:8050 antipolo-surveillance
```

The included `Dockerfile` installs dependencies, copies the app, and runs one
Gunicorn worker with a 600-second timeout. `PORT` defaults to 8050 inside the
container; override with `-e PORT=9000` if needed (and adjust the `-p`
mapping to match).

### Option C — PaaS (Render, Railway, Heroku, Fly.io, etc.)

A `Procfile` is included:

```
web: gunicorn app:server --bind 0.0.0.0:$PORT --workers 1 --timeout 600
```

Most buildpack-based platforms auto-detect this and the `requirements.txt`,
and inject their own `$PORT` — no code changes needed. For Render
specifically: choose "Web Service", point it at this repo, and it will use
the `Procfile` automatically (or set the start command to the line above
manually if it doesn't auto-detect).

### Environment variables (all optional, all have sensible defaults)

| Variable     | Default     | Used by                                                                     |
| ------------ | ----------- | --------------------------------------------------------------------------- |
| `HOST`       | `127.0.0.1` | `app.py` (dev server only; gunicorn's `--bind` controls this in production) |
| `PORT`       | `8050`      | `app.py` (dev server) and the `Procfile`/`Dockerfile` (production)          |
| `DASH_DEBUG` | `true`      | `app.py` (dev server only — never set this true in production)              |
| `LOG_LEVEL`  | `INFO`      | `dashboard/logging_config.py`                                               |

### Things to check before deploying for real (not yet done in this repo)

- **Data persistence across deploys**: uploaded data lives only in the
  browser session, not a database. If you need uploads to persist across
  server restarts or be shared between users, that's a real architecture
  change (add a database or object storage), not a config tweak.
- **HTTPS**: gunicorn doesn't terminate TLS itself — put it behind a reverse
  proxy (nginx/Caddy) or rely on your PaaS's built-in TLS.
- **Health checks**: `/healthz` returns a lightweight 200 response for platform
  probes and container health checks.
- **Uploads**: `.csv` and `.xlsx` uploads are limited to 10 MB. CSV files are
  limited to 100,000 rows; workbooks also have sheet, dimension, and cell limits.
- **Secrets**: there currently aren't any (no API keys, no auth), but if you
  add any, use environment variables, never commit them.

### Historical reference and live benchmark

**Historical reference MAPE: 32.22%** is a fixed external/thesis reference,
not computed from the active dataset. Source: [Olana et al. (2025), Table 1](https://doi.org/10.1155/tbed/7480710), national dengue SARIMA testing MAPE; applicability as an Antipolo threshold is not established.
**Seasonal-naive holdout MAPE/WAPE** is computed separately for each disease
and active dataset by copying the previous year's monthly observations into
the same untouched 12-month holdout. MAPE excludes zero-actual months; WAPE
uses the sum of absolute actual cases as its denominator. Undefined scores
are shown as N/A. The UI displays MAPE first, then WAPE, separated by a slash.
These are distinct references, shown side by side with neutral styling; they
are not merged, averaged, ranked against each other, or used to select a model.
Seasonal naive remains a diagnostic benchmark, not a production candidate.

Current findings and the single decision ledger are linked from [CHATGPT_RETURN_HANDOFF.md](CHATGPT_RETURN_HANDOFF.md). THESIS_READINESS.md and AGENT_HANDOFF.md are preserved historical evidence.


## Reproduce the reconciliation

```bash
python reconciliation/source_reconcile.py
python -m reconciliation.evaluate reconciliation/revised-evaluation.json
python -m pytest -q -p no:cacheprovider
```

Original sources are bundled byte-for-byte under `reconciliation/sources/`. Initial working-tree
files and historical evidence are preserved in `reconciliation/baseline.zip`; do not rerun old
`evidence/investigate.py` against revised code and overwrite the historical evidence.
See `TEST_RESULTS.md` for the actual installed environment: repository dependency pins were
not reinstalled or certified. The external 32.22% reference is Olana et al. (2025), Table 1,
national dengue SARIMA testing MAPE ([source](https://doi.org/10.1155/tbed/7480710)); it is not
a local acceptance standard. See `MODEL_EVALUATION.md` for unfavorable comparisons as well.
