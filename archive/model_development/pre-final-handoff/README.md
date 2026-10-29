# Antipolo monthly ICD-10 consultation dashboard

The finalized thesis model is **Prophet + XGBoost**: Prophet provides the base forecast and XGBoost corrects forecast errors. The application uses researcher-prepared DOH Top-Five monthly CSV/XLSX data for individuals aged 5–19 in Antipolo City within 2016–2025. Consultations are not necessarily confirmed cases or unique patients.

## Current execution status

The legacy prototype is archived and cannot be selected by the application. Model components, the fixed hybrid contract, twelve-month output, ranking service and persistence boundaries are implemented. **Live fitting remains blocked until the Chapter 3 readiness policy and training workflow are supplied.** No replacement thresholds, features, tuning or evaluation splits have been invented. The final training orchestration is not yet implemented; component wrappers are not evidence of a validated model.

All seven candidates are assessed: A00-A09, A15-A19, A80-A89, B00-B09, B25-B34, B85-B89 and B90-B94. Blocks absent from an upload remain visible with no-observations status. Coverage is descriptive, not a fixed forecasting eligibility threshold.

## Run locally

Use the existing virtual environment with its matching Python interpreter. This workspace's environment uses Python 3.14. For a fresh installation, Python 3.12 or later is supported by the application; model dependencies require separate compatibility verification.

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m dashboard.monthly.admin researcher
.venv\Scripts\python.exe app.py
```

Bootstrap prompts for a password; there is no default account. Open http://127.0.0.1:8050. On an existing installation, run `run.bat` without recreating the environment. Admins upload/activate data and execute configured forecasts; viewers read results and generate reports. Permissions are enforced server-side.

## Source data

PDF/DOCX source documents are manually transcribed and verified by researchers. Upload CSV/XLSX with year, month (or month_number), icd10_block, icd10_description and consultation_count. Explicit null rows also require observation_status. Monthly workbook sheets are combined; supporting sheets are excluded with a warning. Duplicate observations and incomplete reported annual entries are rejected. Review staged data before Confirm & Activate.

Reports are available for 2016–2019, 2021 and 2023–2025. Unavailable 2020/2022 values and blocks outside an annual Top Five remain null. Explicit zero remains an observation. No gap compression, automatic zero filling or fabricated source counts are permitted. See [data dictionary](docs/MONTHLY_DATA_DICTIONARY.md).

## Forecasts and projected rankings

The service produces twelve future calendar months after the dataset endpoint. A failed Prophet or XGBoost component fails the hybrid run; no substitute algorithm is used. Counts are bounded below by zero after base-plus-correction combination. No arbitrary correction multiplier or clipping is applied.

The batch service assesses all seven candidates and groups successful forecasts by dataset signature and run group. Rankings sum the same twelve calendar months, sort descending and return up to five blocks. Fewer than five valid results and failed blocks are disclosed. Equal totals use block-code order as a display tie-break. Rankings cover forecastable represented blocks, not every disease in the city. Historical source Top Five and projected Top Five remain separate.

Dashboard, Forecasting and reports consume stored analytical outputs. Old prototype records remain retained but are excluded from current result queries. A newly activated dataset cannot display another signature's results.

## Persistence and deployment

Local state remains SQLite at `.monthly/state.sqlite3` (`MONTHLY_DB` overrides it). Supabase PostgreSQL is the intended cloud database, not an already completed migration. [Migration plan](docs/SUPABASE_MIGRATION.md) documents the remaining work. Source data, accounts and old results have not been destructively migrated.

For HTTPS set `MONTHLY_SECRET_KEY` and `MONTHLY_COOKIE_SECURE=1`; preserve the database and signing key. Production entrypoint: `gunicorn app:server`; health endpoint: `/healthz`. AWS deployment is planned, not verified in this cleanup. Archives, research outputs and local state are excluded from the Docker build.

## Verification and provenance

```powershell
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m pyflakes dashboard/monthly
```

Tests use synthetic data and model doubles; they are not accuracy evidence. See [architecture](ARCHITECTURE.md), [readiness](THESIS_READINESS.md) and [cleanup report](docs/reconciliation-20261029/CLEANUP_REPORT.md). Original source documents, canonical workbooks and historical code are retained. `archive/` is historical only and excluded from package discovery and deployment.
