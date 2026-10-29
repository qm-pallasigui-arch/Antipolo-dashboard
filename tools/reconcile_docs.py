"""Preserve superseded documentation before writing current guidance."""
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
archive = ROOT / 'archive' / 'forecasting' / 'documentation'
archive.mkdir(parents=True, exist_ok=True)
keep = {'README.md', 'MONTHLY_UI_COMPONENTS.md', 'MONTHLY_DATA_DICTIONARY.md'}
for path in (ROOT / 'docs').glob('*.md'):
    if path.name not in keep:
        destination = archive / path.name
        if destination.exists():
            raise RuntimeError('Archive collision')
        shutil.move(str(path), str(destination))
for name in ('README.md', 'ARCHITECTURE.md', 'THESIS_READINESS.md', 'docs/README.md', 'docs/MONTHLY_DATA_DICTIONARY.md'):
    destination = archive / name.replace('/', '_')
    if destination.exists():
        raise RuntimeError('Archive collision')
    shutil.copy2(ROOT / name, destination)

documents = {
'README.md': '''# Antipolo monthly ICD-10 consultation dashboard

The finalized thesis model is **Prophet + XGBoost**: Prophet provides the base forecast and XGBoost corrects forecast errors. The application uses researcher-prepared DOH Top-Five monthly CSV/XLSX data for individuals aged 5–19 in Antipolo City within 2016–2025. Consultations are not necessarily confirmed cases or unique patients.

## Current execution status

The legacy prototype is archived and cannot be selected by the application. Model components, the fixed hybrid contract, twelve-month output, ranking service and persistence boundaries are implemented. **Live fitting remains blocked until the Chapter 3 readiness policy and training workflow are supplied.** No replacement thresholds, features, tuning or evaluation splits have been invented. The final training orchestration is not yet implemented; component wrappers are not evidence of a validated model.

All seven candidates are assessed: A00-A09, A15-A19, A80-A89, B00-B09, B25-B34, B85-B89 and B90-B94. Blocks absent from an upload remain visible with no-observations status. Coverage is descriptive, not a fixed forecasting eligibility threshold.

## Run locally

Use the existing virtual environment with its matching Python interpreter. This workspace's environment uses Python 3.14. For a fresh installation, Python 3.12 or later is supported by the application; model dependencies require separate compatibility verification.

```powershell
python -m venv .venv
.venv\\Scripts\\python.exe -m pip install -r requirements.txt
.venv\\Scripts\\python.exe -m dashboard.monthly.admin researcher
.venv\\Scripts\\python.exe app.py
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
.venv\\Scripts\\python.exe -m pytest -q
.venv\\Scripts\\python.exe -m pyflakes dashboard/monthly
```

Tests use synthetic data and model doubles; they are not accuracy evidence. See [architecture](ARCHITECTURE.md), [readiness](THESIS_READINESS.md) and [cleanup report](docs/reconciliation-20261029/CLEANUP_REPORT.md). Original source documents, canonical workbooks and historical code are retained. `archive/` is historical only and excluded from package discovery and deployment.
''',
'ARCHITECTURE.md': '''# Current architecture

The October 29, 2026 decision fixes the forecasting family as Prophet + XGBoost. Earlier study/model directions are superseded.

| Layer | Location | Responsibility |
|---|---|---|
| Presentation | dashboard/monthly/ui.py, views.py, components.py, charts.py | Authenticated monthly views, candidate review, grouped forecast controls, rankings |
| Security | security.py, admin.py | Password hashes, revocable sessions, CSRF/origin validation, roles |
| Canonical data | domain.py | Upload validation, reporting states, source provenance, preserved calendar |
| Readiness | forecasting/readiness.py | All seven candidates; explicit pending state until approved policy exists |
| Base model | forecasting/prophet_model.py | Prophet fitting on actual observed dates |
| Residual model | forecasting/xgboost_residual.py | XGBoost correction with explicit seed and thread count |
| Hybrid contract | forecasting/hybrid.py | Both components required; nonnegative base-plus-correction output |
| Evaluation support | forecasting/features.py, evaluation.py | Chronological-error provenance checks and metric utilities; final workflow pending |
| Forecast service | services/forecast_service.py | RBAC, readiness, twelve months, versioned runs, explicit failures, batch grouping |
| Ranking service | services/ranking_service.py | Comparable forecast totals, descending ranks, up to five results |
| Analytical repositories | repositories/forecast_repository.py, ranking_repository.py | Result persistence and current-model filtering |
| Existing local store | store.py | SQLite users, datasets, notifications, reports, audit and annotations |
| Reports | reports.py | Historical data, forecast and ranking snapshots, HTML/JSON/CSV |

The UI never constructs model objects from the Prophet or XGBoost libraries. The default hybrid has no approved training workflow and therefore cannot fit live models. A future approved workflow must orchestrate chronological base forecasts, residual training/features and independent evaluation using the component modules. Passing a callable in tests is dependency injection, not model-family selection or production methodology approval.

Available source years remain distinct from missing 2020/2022. Nulls are never interpreted as zero. Dates are never synthesized into an uninterrupted observed sequence. All candidates share the forecast origin at the canonical dataset calendar endpoint; an earlier last observation is recorded separately as training_cutoff.

Historical forecast payloads are preserved. Only completed records with current model name/version and a successful XGBoost correction are exposed. Dataset signatures isolate results. Ranking records contain group ID, signature, months, per-block source run IDs, totals, ranks and warnings. Activation does not delete old results.

Storage extraction is incremental: forecast/ranking repositories exist, while account/dataset/notification operations remain in the existing local Store. Full Supabase migration is pending; see [migration plan](docs/SUPABASE_MIGRATION.md). No claim of live PostgreSQL persistence is made.
''',
'THESIS_READINESS.md': '''# Thesis implementation readiness

Model-family decision: **Prophet + XGBoost, finalized October 29, 2026**.

Implemented: manual-source CSV/XLSX workflow; monthly canonical states; seven-candidate readiness inventory; archive isolation; fixed hybrid contract; separate model component wrappers; explicit component failure; twelve-calendar-month forecast service; comparable projected-total ranking; fewer-than-five handling; current-model result filtering; local persistence; RBAC; current UI/report terminology.

Not yet thesis-ready:

- Approved readiness thresholds and rules for internal/trailing gaps.
- Approved chronological residual-error generation and feature construction; full training orchestration.
- Train/evaluation split, tuning protocol, metrics/scaling and uncertainty method.
- Real Prophet/XGBoost fitting and accuracy validation with the approved methodology.
- Full Supabase repository migration and live persistence verification.
- AWS deployment and operational verification.

The application explicitly blocks live forecast execution while methodology configuration is missing. Synthetic contract tests verify software behavior only. They cannot establish forecast accuracy, a successful Supabase deployment or approved research methodology.

No official data are fabricated or automatically activated. Historical source Top Five is not a forecast. Projected rankings compare only valid represented blocks over a common twelve-month period. Schools are intended beneficiaries; the source has no school identifiers and does not support school-level forecasts.
''',
'docs/README.md': '''# Current documentation

- [Setup and behavior](../README.md)
- [Architecture](../ARCHITECTURE.md)
- [Implementation readiness](../THESIS_READINESS.md)
- [Data dictionary](MONTHLY_DATA_DICTIONARY.md)
- [UI components](MONTHLY_UI_COMPONENTS.md)
- [Cleanup report and full inventory](reconciliation-20261029/CLEANUP_REPORT.md)
- [Supabase migration plan](SUPABASE_MIGRATION.md)

The October 29, 2026 final model decision supersedes earlier methodology documents. Earlier current developer documents are preserved under `archive/forecasting/documentation/`; older snapshots remain historical provenance only.
''',
'docs/MONTHLY_DATA_DICTIONARY.md': '''# Monthly canonical data

| Field | Meaning |
|---|---|
| year | Calendar year, 2016–2025 |
| month / month_number | Month name or 1–12 input; normalized calendar month |
| icd10_block | One of A00-A09, A15-A19, A80-A89, B00-B09, B25-B34, B85-B89, B90-B94 |
| icd10_description | Consistent source description |
| consultation_count | Nonnegative integer when observed, otherwise null |
| observation_status | observed, observed_zero, city_report_unavailable, outside_annual_top5 |
| source_year_available | City report available for that year |
| top5_present | Block represented in that annual source report |
| dataset_id / dataset_signature | Source dataset version and content signature |

City reports are unavailable for 2020 and 2022. Outside-Top-Five counts are unknown, not zero. Every reported annual block entry requires twelve numeric monthly observations. Duplicates, conflicting descriptions and more than five observed blocks per available annual source report are rejected.

Candidate summaries always include all seven blocks. A block with no observations in the upload is marked no_observations. Other blocks remain methodology_pending until approved readiness rules are supplied. top5_year_count and reported_month_count describe coverage; neither is an automatic forecasting threshold. Missing-month diagnostics preserve the calendar and exclude unavailable city-report years from the available-year list.

Forecasts are separate records with model name/version, dataset ID/signature, run/group ID, calendar origin, last observation cutoff, generation time, status, values, evaluation and warnings. Rankings link the group, source runs and dataset signature, with twelve-month totals and rank. Neither output overwrites observations.
''',
'archive/README.md': '''# Historical archive

Everything under this directory is superseded provenance. None belongs to the current executable thesis system. Do not import these modules into the application or seed historical outputs into live storage.

The finalized architecture is Prophet + XGBoost. Earlier research models, wrappers, sample outputs, test contracts and methodology documents remain here for reproducibility. Some archived scripts retain original imports and paths and are not independently runnable after relocation. Use a separate research environment if reproducing them. Archives are excluded from package discovery, default tests and Docker deployment.
''',
'docs/SUPABASE_MIGRATION.md': '''# Supabase PostgreSQL migration plan

Status: planned, not executed. Local SQLite remains authoritative. No production credentials or target Supabase project were supplied for this change.

1. Back up the existing SQLite database and signing key. Inventory table schemas, counts, dataset signatures, forecast model metadata, reports and account identifiers without exposing password hashes or session tokens.
2. Create a private PostgreSQL application schema through an explicit migration. Separate repositories for datasets, users, notifications, forecasts, rankings and reports must replace remaining local SQL usage. Preserve transactional activation, unique usernames, one active dataset and per-user notification read state.
3. Add forecast-run and forecast-value tables with dataset ID/signature, run/group ID, block, month, value, model name/version, status, generated timestamp and warnings. Add ranking-run and ranking-item tables with run/group ID, signature, horizon, rank, block, total and source forecast run ID. Use foreign keys and uniqueness constraints for run/month and ranking/block.
4. Keep old forecasts in a legacy namespace or explicitly labeled historical table. Never relabel prototype predictions as final hybrid output. Refresh derived readiness under the new approved policy without changing source hashes or values.
5. Import into staging first. Verify row counts, source hashes, null/zero preservation, all seven candidate summaries, roles, notification visibility and current-model filtering. Check rollback on failed activation and failed forecast persistence.
6. Test authenticated server-side PostgreSQL access with SSL. Credentials belong in deployment secrets, never browser code. Define access controls before exposing any API. Revoke old sessions or migrate them through an explicit security decision.
7. Run integration tests against an isolated Supabase project for restart persistence, duplicate writes, concurrent activation, forecast/ranking transactions, cross-dataset isolation and RBAC. Mock tests are insufficient to claim live persistence.
8. Cut over only after staging verification; preserve a rollback copy. Remove obsolete columns only in a separate reviewed migration after inspecting retained data.

This cleanup adds a local rankings table non-destructively and stores final-model metadata in separate new forecast payloads. No existing tables or columns are dropped. The current application does not yet connect to Supabase; the migration remains an explicit acceptance gap.
'''
}
for name, text in documents.items():
    (ROOT / name).write_text(text, encoding='utf-8')
path = ROOT / 'CHANGELOG.md'
path.write_text('# Current change — 2026-10-29\n\nFinal model family: Prophet + XGBoost. Legacy forecast wrappers and sample outputs archived. Seven-candidate readiness, fixed hybrid contracts and projected rankings replace prior prototype paths. Live training and Supabase migration remain pending as documented in THESIS_READINESS.md.\n\n# Superseded implementation history\n\nAll entries below describe earlier implementation states and do not override the current model decision.\n\n' + path.read_text(encoding='utf-8'), encoding='utf-8')
