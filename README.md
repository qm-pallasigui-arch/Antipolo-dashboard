# Antipolo City Disease Surveillance — Hybrid Forecast Dashboard

A Dash app that ingests real DOH/PIDSR surveillance data (or falls back to
synthetic mock data for diseases without a real upload) and forecasts each
tracked disease with a hybrid SARIMA + NNAR model, backtested and
auto-selected against a SARIMA-only baseline so the shipped forecast is never
worse than SARIMA alone.

## Package structure

```
app.py                          # entrypoint: wires app_instance + layout + callbacks together
dashboard/
  app_instance.py                # the shared Dash `app` object (breaks circular imports)
  config.py                      # tracked diseases, model hyperparameters, thresholds
  styles.py                      # visual constants (fonts, colors, CSS-in-JS dicts)
  logging_config.py              # operator-facing logging (separate from the UI's own warnings)
  data/
    mock_data.py                  # synthetic fallback generator
    xlsx_parser.py                 # real DOH/PIDSR workbook parser
    validation.py                  # disease whitelist + numeric/range validation
    combine.py                     # merges real data with mock backfill for missing diseases
  modeling/
    series_utils.py                # monthly series shaping, train/test split
    sarima.py                      # SARIMA -> Holt-Winters -> naive drift tiered fit
    nnar.py                        # neural net on SARIMA residuals
    metrics.py                     # RMSE/MAE/MAPE, hybrid recombination
    pipeline.py                    # per-disease orchestration + auto-select safeguard
    serialization.py               # (de)serialization for session storage
  charts/figures.py               # every Plotly figure builder
  ui/
    components.py                  # small reusable Dash components
    layout.py                      # build_layout() -- the full page tree
  callbacks/
    data_callbacks.py              # file upload -> validate -> combine -> train
    view_callbacks.py              # render dropdown status, hybrid section, aggregate section
tests/                           # pytest suite (25 tests as of writing)
```

### Why it's split this way

This used to be a single 1,415-line file. Four functions had grown too complex
(radon cyclomatic complexity 11–21, grade C/D): `load_data`,
`parse_surveillance_xlsx`, `update_hybrid_section`, and `run_hybrid_pipeline`.
Each is now a thin orchestrator calling several single-purpose helper
functions, and `radon cc dashboard/ -n C` reports zero remaining hotspots.

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
gunicorn app:server --bind 0.0.0.0:8050 --workers 2 --timeout 120
```

Put this behind nginx/Caddy for TLS termination in front of it, as usual for
any Flask app. A systemd unit or `tmux`/`screen` session keeps it running
after you disconnect.

### Option B — Docker

```bash
docker build -t antipolo-surveillance .
docker run -p 8050:8050 antipolo-surveillance
```

The included `Dockerfile` installs dependencies, copies the app, and runs the
same gunicorn command as Option A. `PORT` defaults to 8050 inside the
container; override with `-e PORT=9000` if needed (and adjust the `-p`
mapping to match).

### Option C — PaaS (Render, Railway, Heroku, Fly.io, etc.)

A `Procfile` is included:

```
web: gunicorn app:server --bind 0.0.0.0:$PORT --workers 2 --timeout 120
```

Most buildpack-based platforms auto-detect this and the `requirements.txt`,
and inject their own `$PORT` — no code changes needed. For Render
specifically: choose "Web Service", point it at this repo, and it will use
the `Procfile` automatically (or set the start command to the line above
manually if it doesn't auto-detect).

### Environment variables (all optional, all have sensible defaults)

| Variable | Default | Used by |
|---|---|---|
| `HOST` | `127.0.0.1` | `app.py` (dev server only; gunicorn's `--bind` controls this in production) |
| `PORT` | `8050` | `app.py` (dev server) and the `Procfile`/`Dockerfile` (production) |
| `DASH_DEBUG` | `true` | `app.py` (dev server only — never set this true in production) |
| `LOG_LEVEL` | `INFO` | `dashboard/logging_config.py` |

### Things to check before deploying for real (not yet done in this repo)

- **Data persistence across deploys**: uploaded data lives only in the
  browser session, not a database. If you need uploads to persist across
  server restarts or be shared between users, that's a real architecture
  change (add a database or object storage), not a config tweak.
- **HTTPS**: gunicorn doesn't terminate TLS itself — put it behind a reverse
  proxy (nginx/Caddy) or rely on your PaaS's built-in TLS.
- **Secrets**: there currently aren't any (no API keys, no auth), but if you
  add any, use environment variables, never commit them.
