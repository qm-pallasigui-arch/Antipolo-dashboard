# Antipolo monthly ICD-10 consultation dashboard

The finalized model family is **Prophet + XGBoost**. The application now executes a clearly labeled **provisional prototype** using the activated canonical dataset. Prophet is the base forecast and baseline comparator; XGBoost is the only residual learner. Final thesis evaluation remains blocked until Chapter 3 settings are approved.

## Run

```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe app.py
```

For a fresh environment use Python 3.12+ and `python -m venv .venv`, then install requirements. Do not recreate an existing environment with a different interpreter. The workspace's Python 3.14 environment was verified with Prophet 1.5.0 and XGBoost 3.4.1. Bootstrap the first administrator with `.venv\Scripts\python.exe -m dashboard.monthly.admin researcher`; it prompts for a password. Existing installations can use `run.bat`. Open http://127.0.0.1:8050.

## Data and access

Researchers manually extract and verify the DOH PDF/DOCX source, then upload CSV/XLSX. Required fields: year, month or month_number, icd10_block, icd10_description, consultation_count. Explicit null rows also require observation_status. Upload → validation → preview → Admin Confirm & Activate. No OCR, hidden bundled input or automatic dataset activation is used.

Data cover consultations among ages 5–19 in Antipolo City, within 2016–2025. Available reports are 2016–2019, 2021 and 2023–2025. The four states are observed, observed_zero, city_report_unavailable and outside_annual_top5. Explicit zero remains zero; unavailable 2020/2022 and absent annual Top-Five blocks remain unknown. Consultations are not necessarily confirmed cases or unique patients. Schools lack source identifiers and cannot be forecast individually.

All seven candidates are assessed: A00-A09, A15-A19, A80-A89, B00-B09, B25-B34, B85-B89 and B90-B94. Historical source Top Five is separate from projected rankings. Admins upload/activate data and execute forecasts; viewers read results and generate reports. Security checks apply server-side.

## Prototype execution

`PROTOTYPE_MODE=true` by default. In Forecasting, choose **Generate forecasts and rankings**. The batch assesses all seven candidates and runs the fixed hybrid for ready blocks. Every run stores `is_prototype=true`, `methodology_status=provisional`, the configuration snapshot/hash, dataset signature and run/group IDs. The Dashboard, Forecasting, Model Performance, Reports and Notifications distinguish prototype results.

Settings are centralized in `PrototypeModelConfig`; `PROTOTYPE_CONFIG_PATH` optionally loads a JSON object with overrides. The supplied script's yearly Prophet seasonality, XGBoost parameters, twelve lags, seed 12345, one thread, correction clip ±1 and weight 0.1 remain **PROVISIONAL_MODEL_CONFIG**. Readiness uses a technical minimum of 17 observations and fitting requires five usable residual rows. These are not approved thesis thresholds.

Actual first-of-month timestamps are preserved. Prophet fits only observed values at actual dates. Residual lag features use calendar months and native missing-value handling; canonical gaps are never compressed, zero-filled or interpolated. The provisional residual method is in-sample. Trailing gaps before the common forecast origin may be bridged with predictions only. The baseline comparison holds out the last reported year generically, and MASE scaling uses training data only. Undefined MASE is null. No uncertainty interval is claimed.

Every successful block stores twelve individual future-month values. Projected totals sum those values. Rankings require a common dataset, group, mode, configuration and forecast calendar. All valid blocks are ranked. **Fewer than five successes produces Projected Top Five unavailable**, with no invented ranks; the full available ranking remains inspectable. The Projected Top Five is limited to forecastable ICD-10 blocks represented in the supplied 2016–2025 DOH Top-Five dataset.

No failed component silently substitutes another algorithm. Statuses include hybrid_completed, prophet_failed, xgboost_insufficient_history, xgboost_failed and forecast_failed. Prophet-only fallback is reserved but not used. Old prototype engines and incompatible configuration results cannot populate current views. `PROTOTYPE_MODE=false` blocks generation of final results and hides provisional results rather than relabeling them.

## Persistence and cloud

Without a cloud connection, local development uses `.monthly/state.sqlite3` (`MONTHLY_DB` overrides it). Set `MONTHLY_DATABASE_URL` to a Supabase PostgreSQL direct/session-pooler connection string to route **all structured application persistence** through the PostgreSQL boundary. It requires SSL and uses a private schema, default `antipolo_app`; set `MONTHLY_SECRET_KEY` for cloud sessions. A failed configured cloud connection never falls back silently to SQLite.

AWS is the intended hosting environment. The Docker image includes the model and database dependencies. Cloud deployment and live Supabase verification have not been performed without a configured target. See [migration/deployment](docs/SUPABASE_MIGRATION.md). Existing local records are not automatically migrated or deleted.

## Verification and provenance

```powershell
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m pyflakes dashboard/monthly tests
.venv\Scripts\python.exe tests/browser_monthly.py
```

The Supabase integration test is skipped unless a dedicated `TEST_SUPABASE_DATABASE_URL` is set. The browser check uses synthetic data and real prototype fitting in an isolated database. `tools/verify_prototype.py` also verifies real model execution without modifying active application state.

See [handoff implementation](docs/FINAL_HANDOFF_IMPLEMENTATION.md), [architecture](ARCHITECTURE.md), [readiness](THESIS_READINESS.md) and [data dictionary](docs/MONTHLY_DATA_DICTIONARY.md). The original tuning script is preserved with its SHA-256 under `archive/model_development/`. Archives are excluded from imports, default tests and deployment.
