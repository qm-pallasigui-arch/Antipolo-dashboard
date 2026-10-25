# Antipolo monthly ICD-10 consultation dashboard

The active application follows the October 24, 2026 handoff: monthly infectious-disease consultation counts among individuals aged 5–19 in Antipolo City, Rizal. Annual Top-5 coverage establishes historical recurrence; deterministic eligibility precedes forecasting. **The forecasting methodology is pending approval; no model is installed.**

## Install and launch

Use Python 3.12 or later. In PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m dashboard.monthly.admin researcher
.venv\Scripts\python.exe app.py
```

The setup command prompts for an administrator password of at least 12 characters. There is no default password. Bootstrap works only before the first account exists. Open http://127.0.0.1:8050 and sign in. After setup, run.bat also launches the app.

Security / Accounts lets administrators create users, assign admin/viewer roles and activate/deactivate accounts. Administrators manage datasets, annotations, approved forecast execution and users. Viewers read active data and results, generate reports and mark their notifications read. Permissions are checked server-side.

## Monthly dataset format

Upload CSV or XLSX, maximum 10 MB, with one row per reported block/month. Every workbook sheet must have the same canonical table structure.

| Column | Meaning |
| --- | --- |
| year | Integer within 2016–2025 |
| month | 1–12, English month name or abbreviation |
| icd10_block | Infectious-disease range such as A00-A09 |
| icd10_description | Consistent source description |
| consultation_count | Nonnegative integer; explicit zero is valid |
| observation_status | Optional for counts; required for explicitly supplied null rows |

Available years are **2016, 2017, 2018, 2019, 2021, 2023, 2024 and 2025**. Omit unavailable years and blocks absent from an annual Top-5 report: the calendar expands with classified nulls. A reported block/year requires all 12 numeric observations; incomplete annual entries and duplicates fail validation. No arbitrary source-PDF extraction or legacy-workbook conversion is performed. See the [data dictionary](docs/MONTHLY_DATA_DICTIONARY.md).

Data & Quality workflow: upload → validate → review pending candidate → **Confirm & Activate**. Cancel, reject and validation failure preserve active data. Candidates persist across restarts. Source bytes, hash, uploader, timestamps and normalized data are retained.

**No revised official dataset is bundled or preloaded.** The existing disease-specific workbook and legacy caches are not imported. Test fixtures are synthetic and never appear as official data.

## Data states and eligibility

- observed: positive reported consultation count.
- observed_zero: explicitly reported zero, counted toward eligibility.
- city_report_unavailable: null for 2020/2022; never interpolated or replaced with zero.
- outside_annual_top5: null when a block is absent from an available annual report.

Primary eligibility requires **8/8 available years and 96 distinct reported months**. The two unavailable years are excluded from the denominator. All blocks remain available descriptively. Eligibility does not depend on model performance or establish epidemiological importance.

## Modules and forecasts

Security precedes authenticated navigation: Dashboard, Disease Trends, Forecasting, Model Performance & Insights, Data & Quality, Reports, Notifications, Help & About. Reports export self-contained HTML (printable), JSON evidence and labeled CSV values. Notifications persist with per-user read state.

[TO FINALIZE: forecasting methodology]

The production model registry is empty. Forecast generation is disabled until researchers approve an engine. The service separates preparation, candidate fitting, evaluation, comparison, selection, refitting and generation. It supports 1–12 months ahead and evaluation at horizons 1/3/6/12. Results are isolated by signature and block; failed runs preserve prior completed results. No legacy model or benchmark is used.

Consultations are not necessarily confirmed cases or unique patients. Forecasts do not establish outbreaks, individual diagnoses or future Top-5 rankings.

## Operations and developer checks

State defaults to .monthly/state.sqlite3. Set MONTHLY_DB to an absolute path on persistent storage. A fallback signing key is created beside it. For HTTPS deployment set a strong MONTHLY_SECRET_KEY and MONTHLY_COOKIE_SECURE=1. Protect and back up the database and key, persist them across deployments and keep debug off. The production entrypoint remains gunicorn app:server; /healthz is public and contains no data.

Passwords use secure Werkzeug hashing; eight-hour sessions are revocable. Forms use CSRF tokens; callbacks enforce JSON and same-origin requests. Login failures are throttled per username.

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.venv\Scripts\python.exe -m pytest tests/test_monthly_system.py -q
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m pyflakes dashboard/monthly
```

See [architecture](ARCHITECTURE.md) and [readiness](THESIS_READINESS.md). Legacy modules remain disconnected from the active entrypoint for regression and traceability. Pre-migration documentation snapshots, including existing workspace edits, are preserved in docs/legacy-before-monthly/.
