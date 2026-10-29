"""Refresh current documentation while preserving the previous reconciliation state."""
from pathlib import Path
import shutil

root = Path(__file__).resolve().parents[1]
destination = root / 'archive/model_development/pre-final-handoff'
destination.mkdir(parents=True, exist_ok=True)
for name in ('README.md', 'ARCHITECTURE.md', 'THESIS_READINESS.md', 'docs/SUPABASE_MIGRATION.md'):
    target = destination / name.replace('/', '_')
    if target.exists():
        raise RuntimeError('Documentation snapshot already exists.')
    shutil.copy2(root / name, target)

documents = {
'README.md': '''# Antipolo monthly ICD-10 consultation dashboard

The finalized model family is **Prophet + XGBoost**. The application now executes a clearly labeled **provisional prototype** using the activated canonical dataset. Prophet is the base forecast and baseline comparator; XGBoost is the only residual learner. Final thesis evaluation remains blocked until Chapter 3 settings are approved.

## Run

```powershell
.venv\\Scripts\\python.exe -m pip install -r requirements.txt
.venv\\Scripts\\python.exe app.py
```

For a fresh environment use Python 3.12+ and `python -m venv .venv`, then install requirements. Do not recreate an existing environment with a different interpreter. The workspace's Python 3.14 environment was verified with Prophet 1.5.0 and XGBoost 3.4.1. Bootstrap the first administrator with `.venv\\Scripts\\python.exe -m dashboard.monthly.admin researcher`; it prompts for a password. Existing installations can use `run.bat`. Open http://127.0.0.1:8050.

## Data and access

Researchers manually extract and verify the DOH PDF/DOCX source, then upload CSV/XLSX. Required fields: year, month or month_number, icd10_block, icd10_description, consultation_count. Explicit null rows also require observation_status. Upload → validation → preview → Admin Confirm & Activate. No OCR, hidden bundled input or automatic dataset activation is used.

Data cover consultations among ages 5–19 in Antipolo City, within 2016–2025. Available reports are 2016–2019, 2021 and 2023–2025. The four states are observed, observed_zero, city_report_unavailable and outside_annual_top5. Explicit zero remains zero; unavailable 2020/2022 and absent annual Top-Five blocks remain unknown. Consultations are not necessarily confirmed cases or unique patients. Schools lack source identifiers and cannot be forecast individually.

All seven candidates are assessed: A00-A09, A15-A19, A80-A89, B00-B09, B25-B34, B85-B89 and B90-B94. Historical source Top Five is separate from projected rankings. Admins upload/activate data and execute forecasts; viewers read results and generate reports. Security checks apply server-side.

## Prototype execution

`PROTOTYPE_MODE=true` by default. In Forecasting, choose **Generate prototype forecasts and rankings**. The batch assesses all seven candidates and runs the fixed hybrid for ready blocks. Every run stores `is_prototype=true`, `methodology_status=provisional`, the configuration snapshot/hash, dataset signature and run/group IDs. The Dashboard, Forecasting, Model Performance, Reports and Notifications distinguish prototype results.

Settings are centralized in `PrototypeModelConfig`; `PROTOTYPE_CONFIG_PATH` optionally loads a JSON object with overrides. The supplied script's yearly Prophet seasonality, XGBoost parameters, twelve lags, seed 12345, one thread, correction clip ±1 and weight 0.1 remain **PROVISIONAL_MODEL_CONFIG**. Readiness uses a technical minimum of 17 observations and fitting requires five usable residual rows. These are not approved thesis thresholds.

Actual first-of-month timestamps are preserved. Prophet fits only observed values at actual dates. Residual lag features use calendar months and native missing-value handling; canonical gaps are never compressed, zero-filled or interpolated. The provisional residual method is in-sample. Trailing gaps before the common forecast origin may be bridged with predictions only. The baseline comparison holds out the last reported year generically, and MASE scaling uses training data only. Undefined MASE is null. No uncertainty interval is claimed.

Every successful block stores twelve individual future-month values. Projected totals sum those values. Rankings require a common dataset, group, mode, configuration and forecast calendar. All valid blocks are ranked. **Fewer than five successes produces Projected Top Five unavailable**, with no invented ranks; the full available ranking remains inspectable. The Projected Top Five is limited to forecastable ICD-10 blocks represented in the supplied 2016–2025 DOH Top-Five dataset.

No failed component silently substitutes another algorithm. Statuses include hybrid_completed, prophet_failed, xgboost_insufficient_history, xgboost_failed and forecast_failed. Prophet-only fallback is reserved but not used. Old prototype engines and incompatible configuration results cannot populate current views. `PROTOTYPE_MODE=false` blocks generation of final results and hides provisional results rather than relabeling them.

## Persistence and cloud

Without a cloud connection, local development uses `.monthly/state.sqlite3` (`MONTHLY_DB` overrides it). Set `MONTHLY_DATABASE_URL` to a Supabase PostgreSQL direct/session-pooler connection string to route **all structured application persistence** through the PostgreSQL boundary. It requires SSL and uses a private schema, default `antipolo_app`; set `MONTHLY_SECRET_KEY` for cloud sessions. A failed configured cloud connection never falls back silently to SQLite.

AWS is the intended hosting environment. The Docker image includes the model and database dependencies. Cloud deployment and live Supabase verification have not been performed without a configured target. See [migration/deployment](docs/SUPABASE_MIGRATION.md). Existing local records are not automatically migrated or deleted.

## Verification and provenance

```powershell
.venv\\Scripts\\python.exe -m pytest -q
.venv\\Scripts\\python.exe -m pyflakes dashboard/monthly tests
.venv\\Scripts\\python.exe tests/browser_monthly.py
```

The Supabase integration test is skipped unless a dedicated `TEST_SUPABASE_DATABASE_URL` is set. The browser check uses synthetic data and real prototype fitting in an isolated database. `tools/verify_prototype.py` also verifies real model execution without modifying active application state.

See [handoff implementation](docs/FINAL_HANDOFF_IMPLEMENTATION.md), [architecture](ARCHITECTURE.md), [readiness](THESIS_READINESS.md) and [data dictionary](docs/MONTHLY_DATA_DICTIONARY.md). The original tuning script is preserved with its SHA-256 under `archive/model_development/`. Archives are excluded from imports, default tests and deployment.
''',
'ARCHITECTURE.md': '''# Current prototype architecture

The final handoff authorizes provisional execution of the fixed Prophet + XGBoost family. Standalone Prophet is only the baseline comparator. No competing model-family registry exists.

| Layer | Modules | Responsibility |
|---|---|---|
| UI | ui, views, components, charts | Nine modules including Security; provisional labels, charts, rankings, comparison |
| Source domain | domain | Canonical CSV/XLSX validation and immutable source states |
| Configuration/readiness | forecasting/config, readiness | One provisional settings object; seven candidates; explicit readiness states |
| Model adapter | forecasting/adapter | Canonical fields and actual timestamps; no hidden source file |
| Base model | forecasting/prophet_model | Prophet fitting and fitted/future values |
| Residual features | forecasting/features | Replaceable residual construction; calendar lags with missing values |
| Correction | forecasting/xgboost_residual | XGBoost fitting and recursive residual prediction; explicit failures |
| Hybrid workflow | forecasting/pipeline, hybrid | Provisional composition and fixed architecture contract |
| Evaluation | forecasting/evaluation | Generic chronological split; training-only scale; baseline/hybrid comparison |
| Application services | services/forecast_service, ranking_service | RBAC, batch groups, twelve-month output, projected totals and rankings |
| Analytical persistence | repositories/forecast_repository, ranking_repository | Mode/configuration/version isolation, atomic run and monthly-value writes |
| Database boundary | repositories/database | Server-side Supabase/PostgreSQL connection, private schema, transaction and SQL compatibility layer |
| Application store | store | Users, datasets, source bytes, quality/readiness payloads, notifications, audit, annotations, reports |

The canonical dataset is never overwritten by model processing. Actual calendar gaps remain null and carry their source states. The prototype fits on observed timestamps; unknown lag values remain NaN for XGBoost. Recursive predictions bridge trailing gaps without creating observed values. Twelve future forecast months start after the common canonical endpoint, not after a compressed sequence or a block-specific shortened calendar.

All generated results are provisional. A generic last-reported-year evaluation refits both components on earlier data; residuals within that training subset remain in-sample. This limitation is disclosed. Chapter 3 can replace residual construction, features and evaluation via the module boundaries. The current implementation does not approve a final methodology through a Boolean flag.

Successful runs store status hybrid_completed, is_prototype=true, methodology_status=provisional, configuration/hash, model version, dataset/version, run/group ID, observed cutoff and calendar origin. Twelve monthly values and baseline values are persisted transactionally in forecast_values. Errors preserve prior valid results but never create substitute hybrid outputs. Ranking reads require a coherent group, mode, configuration and calendar; fewer than five valid blocks yields an unavailable Top Five while retaining full ranks.

Store operations use SQLite locally or Supabase PostgreSQL when configured. The shared database boundary handles parameter binding, identity IDs, conflict handling and transaction locking. Password hashes, revocable sessions and server-side role checks remain application-managed in either backend. PostgreSQL uses a private schema and SSL; cloud operation requires an explicit signing secret. Existing SQLite data require a deliberate migration, not an automatic destructive conversion.

Archives and the supplied original script are never imported. The default runtime has exactly one hybrid pipeline. Future final results must have a separately approved configuration/workflow and remain segregated from prototype artifacts.
''',
'THESIS_READINESS.md': '''# Prototype and thesis readiness

**Prophet + XGBoost is finalized; prototype execution is operational.** Final thesis analytical/evaluation results remain blocked pending approved Chapter 3 settings.

Implemented: actual-calendar canonical adapter; unchanged zero/missing semantics; all seven candidates; configurable provisional readiness; real Prophet and XGBoost fitting; separate residual construction; baseline comparison; generic chronological holdout; training-only MASE scale; explicit statuses without fallback; twelve stored future months; projected totals/full ranking; unavailable Top Five with fewer than five successes; prototype/configuration isolation; UI/reports/notifications; local persistence; PostgreSQL connection boundary for Supabase; RBAC; archive isolation.

Real-model verification ran against synthetic data and all seven canonical candidates in isolated temporary databases. These are prototype engineering checks, not final thesis evidence. See evidence/prototype-handoff-20261029 and [handoff implementation](docs/FINAL_HANDOFF_IMPLEMENTATION.md) for the recorded results.

Chapter 3 must still approve readiness thresholds, gap treatment, chronological residual generation, features/lags, Prophet/XGBoost tuning, clipping/shrinkage, validation/test design, metrics/scaling and any uncertainty intervals. Changing PROTOTYPE_MODE to false does not bypass these requirements.

Infrastructure gaps: no live Supabase target/credentials were configured, so the opt-in integration test has not verified cloud persistence. AWS deployment has not been executed. A PostgreSQL implementation and Docker configuration do not establish successful cloud deployment. Existing local records remain preserved; migration requires backup, staging verification and deliberate cutover.
''',
'docs/SUPABASE_MIGRATION.md': '''# Supabase PostgreSQL and AWS deployment

The PostgreSQL persistence boundary is implemented; no target cloud connection or deployment was configured during this handoff.

## Configure a new cloud environment

Use the Supabase direct connection or session pooler from the project's Connect panel. Set these server-side deployment secrets/settings:

```text
MONTHLY_DATABASE_URL=<PostgreSQL connection string>
MONTHLY_DATABASE_SCHEMA=antipolo_app
MONTHLY_SECRET_KEY=<strong persistent signing secret>
MONTHLY_COOKIE_SECURE=1
PROTOTYPE_MODE=true
```

The app uses psycopg with SSL required and a private schema. The database role must be able to create/use that schema and its tables. Do not expose this schema through a public client API. Users/roles, sessions, dataset source bytes/metadata/quality/readiness, runs, individual forecast values, rankings, notifications, reports and audit records all use this connection. This retains the application's existing password/session implementation; it is not an implicit migration to Supabase Auth.

Connection failures do not silently fall back to local SQLite. Tables are created additively; no existing columns/tables are dropped. PostgreSQL advisory transaction locks serialize activation and account safety checks across workers. Forecast run completion and its monthly values are committed together.

## Verify in staging

Set `TEST_SUPABASE_DATABASE_URL` to a dedicated test connection and run `pytest tests/test_supabase_persistence.py`. The test creates a random private test schema and removes only that schema. It verifies restart persistence for datasets, roles, forecasts, values, rankings, reports and notifications; role rejection and new-dataset result isolation are also checked. Without the test URL it is explicitly skipped.

## Existing local data

Do not switch an existing installation assuming its SQLite data will automatically appear in PostgreSQL. First back up the local database and signing key, inventory rows/source signatures, then migrate to staging through an explicit export/import procedure. Preserve account IDs, dataset provenance, null/zero distinctions and legacy result classifications. Never relabel old predictions as the new hybrid. Reconcile identity sequences after importing IDs. Validate row counts, hashes, activation atomicity and result isolation before cutover. Retain the original SQLite backup for rollback. No automatic migration was executed in this task.

## AWS container

The Dockerfile installs the application, pinned model libraries, PostgreSQL driver and CPU runtime library. It runs `gunicorn app:server`, listens on PORT (default 8050) and exposes `/healthz`. Deploy behind HTTPS with the settings above supplied through the AWS environment/secrets mechanism. Keep one worker initially because model fitting is synchronous and CPU-bound; allow up to the configured 600-second request timeout for prototype batches. Monitor failures and memory before changing concurrency. The service does not create synthetic source data on startup.

The container was prepared but not built/deployed in an AWS account during this handoff. Live connection, migration and deployment are distinct operational verification steps.
'''
}
for name, text in documents.items():
    (root / name).write_text(text, encoding='utf-8')
