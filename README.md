# Antipolo weekly infectious disease forecasting

A Dash application for weekly reportable infectious disease case counts among individuals aged **5–19 in Antipolo City**, using eligible **confirmed-only CESU/PIDSAR** surveillance records to support public-school preparedness.

Run `python app.py` and open the displayed URL. Install the project dependencies from `requirements.txt` first if needed. Production WSGI remains `app:server`; `/healthz` is the health endpoint.

The dashboard has five sections: **Overview**, **Forecast**, **Historical Trends**, **Data**, and **About the Model**. In Data, upload a CSV/XLSX. Recognizable columns and legacy week-by-year worksheets are prepared automatically. A **Review Data Transformation** popup compares the original and prepared records. Resolve any ambiguous columns using dropdowns, then **Confirm & Use Data**. Cancelling keeps the current dataset. No JSON editing or manual file restructuring is required for recognized layouts.

Hybrid SARIMA–NNAR is the primary model; SARIMA-only is a separate comparison. The installed Exploratory Weekly Configuration v0.1 can generate one 52-point path; 4/13/26/52-week views do not retrain. The Revision 45 exploratory settings are authorized for Technical / Retrospective Evaluation Only, not final adviser-approved methodology. `WEEKLY_MODEL_CONFIG` may override the bundled protocol. Unknown reporting completeness or calendars still block fitting; configuration never fabricates source facts. Read-only technical details are collapsed under About the Model.

Missing weeks and blank counts are never zero-filled or automatically imputed. Week 53 is preserved. Incomplete or unknown reporting weeks remain visible and are excluded from training. All-age/unverified data are labeled Technical / Retrospective Evaluation. Synthetic / Demo Data cannot qualify as thesis evidence. Measles and Measles-Rubella remain distinct.

Read [WEEKLY_SYSTEM.md](WEEKLY_SYSTEM.md) for the input/metadata schema, eligibility gate, protocol fields, missing-data behavior, uncertainty calculation, exports, and future prospective snapshot/reconciliation workflow. Prospective validation is not yet completed. Monthly/quarterly summaries are display-only and require source-established week dates.

See [REVISION39_REPORT.md](docs/archive/REVISION39_REPORT.md) for the guided-workflow reconciliation and real-browser review evidence.

```powershell
python -m pytest -q
python -m pyflakes dashboard/weekly
```

The operational implementation is `dashboard/weekly/`. Earlier monthly modules and evidence remain preserved for historical regressions and audit purposes; they are not loaded by normal application startup. Pre-weekly documentation is archived under [docs/historical-pre-weekly](docs/historical-pre-weekly). Earlier handoffs and manuscript/audit documents describe historical work and are superseded by the weekly operational contract where they conflict.


Current implementation and evidence: [Revision 45 reconciliation](docs/archive/REVISION45_REPORT.md). Source-backed completeness, calendar declarations, and individual blank-count decisions are available in the review. Original evidence is retained.

Documentation is organized in the [documentation map](docs/README.md). Historical handoffs and individual revision reports live under `docs/archive/`.

## Running locally

The dashboard runs on any machine with Python 3.10+; no external services are
required.

**Windows, quickest start:** double-click `run.bat`. It uses `.venv` if one
exists, otherwise `python` from PATH, sets the per-disease protocol, and serves
<http://127.0.0.1:8050>. Close the window, or press Ctrl+C, to stop. The window
stays open after a crash so the error is readable.

Anything else:

```bash
python -m venv .venv
# Windows:      .venv\Scripts\activate
# macOS/Linux:  source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

The server prints its URL (default <http://127.0.0.1:8050>). To run the test
suite and linters as well, install the development extras instead:

```bash
pip install -r requirements-dev.txt
python -m pytest -q
python -m pyflakes dashboard/weekly
```

### Environment variables

All settings have working defaults, so none of these are required to start the
app. They exist for running the dashboard somewhere other than your own machine.

| Variable | Default | Purpose |
|---|---|---|
| `HOST` | `127.0.0.1` | Interface to bind. Use `0.0.0.0` to accept connections from other machines. |
| `PORT` | `8050` | TCP port for the development server. |
| `DASH_DEBUG` | `true` | Dash hot-reload/debug mode. Set `false` to run quietly. |
| `LOG_LEVEL` | `INFO` | Log verbosity. `DEBUG` adds per-candidate fit diagnostics. |
| `PYTHONUNBUFFERED` | unset | Set to `1` to stream logs immediately instead of in blocks. |
| `WEEKLY_MODEL_CONFIG` | bundled protocol | Path to a JSON file overriding the weekly SARIMA-NNAR protocol. |
| `WEEKLY_RESEARCH_CONFIG` | unset | Path to a JSON file overriding research/evaluation settings. |

PowerShell example - bind to all interfaces, quiet logs, and use the
per-disease protocol:

```powershell
$env:HOST = "0.0.0.0"
$env:PORT = "8050"
$env:DASH_DEBUG = "false"
$env:LOG_LEVEL = "INFO"
$env:PYTHONUNBUFFERED = "1"
$env:WEEKLY_MODEL_CONFIG = "config/weekly_model_per_disease.json"
python app.py
```

The equivalent `bash`/`zsh` form uses `export NAME=value` instead.

### Platform notes

- **gunicorn is POSIX-only.** `gunicorn "app:server" --bind 0.0.0.0:$PORT`
  works on Linux/macOS but fails on Windows with
  `ModuleNotFoundError: No module named 'fcntl'`. `Procfile` and `Dockerfile`
  are likewise Linux-only. On Windows, always use `python app.py`.
- `HOST` defaults to `127.0.0.1`, so the app is reachable only from the same
  machine. This is deliberate; set `0.0.0.0` explicitly to expose it, and put
  it behind a firewall or reverse proxy if it is not on a trusted network.

### Expected runtimes

Model fitting is CPU-bound and runs synchronously in the request, so the button
stays disabled until the fit finishes. On a typical laptop CPU:

| Protocol | Dengue | Measles-Rubella | Leptospirosis |
|---|---|---|---|
| Per-disease (`config/weekly_model_per_disease.json`) | ~90 s | ~135 s | ~15 s |
| Bundled default (16 candidates) | 145-406 s | 145-406 s | 145-406 s |

These are upper bounds for a single disease on one dataset. Several factors can
extend them: the number of SARIMA candidates, the length of the weekly history,
and how many weeks are missing from the training series. Progress is written to
the console at `INFO`; set `LOG_LEVEL=DEBUG` for per-candidate AIC and timing.

A repeated forecast for the same disease, dataset and protocol is served from
cache and returns immediately.
