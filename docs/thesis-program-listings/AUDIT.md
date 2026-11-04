# Active-code audit for the thesis listings

Audit date: 30 October 2026 (Asia/Manila). Git HEAD: `ef1431c8dd2d83993bc30ff95ec669654e758de2`. The audited source is the working tree, not only that commit. Before this task, `.dockerignore`, `.gitignore`, `README.md`, and the two browser scripts were modified; `docs/REPOSITORY_HYGIENE.md` and `tools/clean_generated.ps1` were untracked. Those changes were preserved. This reconciliation changes active application code and tests as authorized, then regenerates the listings and evidence. Pre-existing unrelated changes remain preserved.

**The architecture matches Prophet + XGBoost, but the repository does not yet implement an approved final thesis forecasting mode.** Code listings can document the active software, provided its provisional status is retained. Do not present the accompanying forecasts, rankings or metrics as approved final study findings.

## Operational path established from source

`app.py` imports `dashboard.monthly.ui.install`, which installs security and creates `Store` and `ForecastService`. Upload callbacks call `Store.stage` → `parse_upload` → `normalize`; activation is explicit. `Store.active` refreshes descriptive data-quality statistics for all seven candidates, without a coverage gate. Generation calls `ForecastService.run_all` → `run` → `HybridModel.generate` → `PrototypeWorkflow` → Prophet → in-sample residual construction → XGBoost → weighted hybrid combination. The workflow performs the last-reported-year evaluation before full-history future forecasting. An unavailable evaluation is recorded separately from a successful future forecast. Completed runs persist twelve monthly values; ranking uses their aggregate sums. Dashboard and report readers filter current dataset, mode and configuration.

No active imports of archived model engines were found in the dashboard. The existing archive-import and monthly-entrypoint tests passed. The active Python search found no legacy algorithm implementations or synthetic year-2000 timeline. The archived source is deliberately excluded from the code listings, even when it contains useful-looking historical output.


## Reconciled study workflow

`7 ICD-10 blocks -> Data Quality Assessment -> Prophet-XGBoost Modeling -> Chronological Evaluation -> 12-Month Forecasts -> Projected Totals -> Ranking -> Projected Top Five`

All seven historically represented ICD-10 blocks undergo data-quality assessment and modeling using their available monthly observations. The removed coverage classification is no longer a Chapter 1 concept or an active gate. `dashboard/monthly/data_quality.py` replaces the previous classification module. Dataset reads rebuild descriptive fields from source rows, dropping obsolete derived classifications on older payloads without changing observations or dataset signatures. Activation notifications describe reporting coverage neutrally.

`ForecastService.run_all` invokes the workflow for every member of `CANDIDATE_BLOCKS`. Every attempted block has a persisted run and a model outcome. Rankings carry `attempted_blocks`, `failed_blocks` and `model_statuses`; they include only complete valid twelve-month forecasts. No failed values or ranks are invented. At least five successful forecasts are needed for Projected Top Five; all valid ranks remain available otherwise.

The new tests prove that twelve observed months still reach modeling, absent observations reach the workflow and return a technical failure, short residual history fails inside model processing, and evaluation_unavailable does not suppress a successfully produced future forecast. Current statuses include hybrid_completed, prophet_failed, xgboost_failed, xgboost_insufficient_history and forecast_failed; evaluation_unavailable is stored in the evaluation result. Running and not_run are execution/display states, not academic classifications.

### Existing installation compatibility

Model version is now `3`. Old forecasts remain stored but are not displayed as current results; regenerate forecasts after updating. `min_observations` was renamed to `min_evaluation_observations`, which applies only to the chronological evaluation's pre-test training history (default 17). Update any external `PROTOTYPE_CONFIG_PATH` JSON override to the new field name. There is no total-history coverage threshold before modeling. Residual fitting retains its genuine technical minimum of five usable rows. The legacy `Store(..., readiness_policy=...)` constructor extension was removed; application callers no longer supply policies.

Previously persisted reports and notifications are historical records and are not rewritten. Newly generated reports and activation notifications use the revised concepts. The dated 29 October handoff is explicitly marked superseded for the coverage gate. No database schema migration, source-row rewrite, active-dataset activation or live cloud write was performed by this reconciliation.

## Verified requirements

| Requirement | Finding and evidence |
| --- | --- |
| Dataset loading | Both repository canonical CSV and XLSX parse to 840 monthly rows and the same dataset signature. Supporting XLSX sheets are excluded. |
| Missing versus zero | Canonical probe: 398 observed, 82 observed_zero, 168 city_report_unavailable, 192 outside_annual_top5. Nulls remain unavailable; zeros remain observations. |
| Actual monthly dates | Adapter constructs year/month/day=1. Canonical per-block grid spans January 2016–December 2025. Calendar-lag tests preserve gaps. |
| All seven blocks | `refresh_dataset` assesses the configured seven-block pool, including absent-upload candidates. Fresh real-model verification completed all seven. All seven are attempted for every upload; short or absent observations produce technical model outcomes rather than pre-model exclusion. |
| Operational algorithm | Only Prophet base plus XGBoost corrector; standalone Prophet is retained as baseline. Both components must succeed for a hybrid completion. |
| Horizon | Exactly twelve generated months. This canonical run forecasts January–December 2026 and stores 84 monthly values across seven runs. UI 3/6-month options are display windows only. |
| Projected total/rank | Sum of each block’s twelve monthly hybrid predictions; all valid blocks ranked. Top Five is the first five sums, not historical Top-Five selection. |
| Comparability | Ranking validates dataset, group, mode, configuration and common consecutive forecast months. |
| Failure behavior | Explicit component statuses persist; no alternative algorithm or silent baseline fallback. Synthetic injected-failure tests pass. |
| Evaluation | Last reported year held out per block; both components refit using earlier observations. MASE scaling uses training-only calendar pairs. |
| Persistence and access | Local restart/version isolation, admin enforcement, forged-callback rejection, report persistence and notification visibility tests pass. |
| Archived isolation | Default test configuration excludes archives. Entrypoint/import tests pass. |

## Conflicts and qualifications that must remain visible

1. **Final analytical mode is not operational.** `ForecastService.configured` requires `store.is_prototype`; the default workflow is only supplied in prototype mode. Every generated run is stamped `is_prototype=True`, `methodology_status='provisional'`. Setting `PROTOTYPE_MODE=false` blocks generation and hides provisional results. It does not approve or convert them. This conflicts with an unqualified claim that the repository is already the final thesis implementation.

2. **Residual targets are in-sample errors.** `generate_residual_training_data` subtracts fitted Prophet values from the same observed training values. It does not generate rolling-origin or out-of-fold residual targets. `validate_error_rows` rejects nonchronological targets in its own unit test, but it is not called by the active workflow. That test must not be cited as proof of chronological residual training. The `fit_predict` helper in each model module is likewise not the operational fitting path.

3. **Settings remain provisional.** Current defaults include twelve residual lags, minimum 17 pre-test observations for evaluation only, five usable residual rows for XGBoost fitting, yearly Prophet seasonality, XGBoost depth 6 and 1,000 estimators, clip ±1, correction weight 0.1, seed 12345 and one thread. No approved tuning procedure or final Chapter 3 configuration is established by these code defaults. The residual adjustment is capped at ±0.1 per forecast month, so it can change a twelve-month baseline total by at most 1.2 in magnitude before/with the nonnegative floor. Do not describe it as an unrestricted residual correction.

4. **Evaluation years differ across blocks.** Fresh canonical output uses 2025 for five blocks, 2021 for B85-B89 and 2019 for B90-B94. B85-B89 training ends in 2018; its 2021 holdout spans an intervening gap. The evaluation is a single last-reported-year split, not rolling cross-validation or a uniform 2025 test for all blocks. Seven successful evaluations are engineering evidence, not proof of approved accuracy or hybrid superiority. No uncertainty intervals are generated.

5. **Forecast origin follows the canonical endpoint, not the wall clock or each block’s latest observed month.** `normalize` constructs the approved 2016–2025 grid, including unknown periods. `run` uses the dataset maximum year/month, which makes the horizon January–December 2026 here. Sparse blocks can require long trailing prediction bridges from old observations. This preserves actual dates, but the bridge method and appropriateness of forecasting from old coverage remain methodology decisions. “Future twelve months” must be understood relative to the December 2025 dataset origin, not twelve months after this October 2026 audit.

6. **Supabase is implemented but not verified live in this audit.** `Store.connect` routes configured cloud operations to psycopg with required SSL and a private schema. The fresh persistence verification ran on SQLite. The dedicated Supabase test was explicitly disabled for local-only verification and reports SKIPPED; this audit establishes neither live Supabase connectivity nor AWS deployment. SQL adaptation unit tests are not integration tests.

7. **Some source comments predate the provisional workflow.** `prophet_model.py`, `features.py` and `hybrid.py` contain comments/docstrings mentioning approved parameters or chronological errors. Runtime configuration and actual call paths show the qualifications above. Exact source excerpts retain these comments rather than silently rewriting implementation text.

8. **Latest-attempt status is authoritative in dashboard and reports.** `ForecastRepository.latest_attempt` includes running and failed attempts in the current mode/configuration/version. An older successful forecast remains stored and can be read through `latest`, but the dashboard and newly generated reports do not substitute it for a failed latest attempt. The new regression test verifies this behavior on Dashboard, Forecasting, Model Performance and HTML reports.

9. **Data-quality status is not a calibrated quality score.** Normalization sets `validation_status='warning'` with reporting-gap warnings. Descriptive data quality and actual model outcomes are separate; coverage is never an inclusion gate. Unknown annual Top-Five exclusions must not be interpreted as zero disease activity, and consultations must not be relabeled as unique patients or confirmed cases.

## Fresh execution evidence

The successful run produced:

```text
51 passed, 1 skipped, 5 warnings in 18.86s
{"statuses": {"hybrid_completed": 7}, "stored_monthly_values": 84, "ranked_blocks": 7, "top_five_status": "available"}
```

These are captured in [pytest-verified.txt](evidence/pytest-verified.txt) and [canonical-verified.txt](evidence/canonical-verified.txt). The five pytest warnings concern Dash DataTable deprecation. The model run also emitted a short-history yearly-seasonality warning; it is retained in the log. Initial sandbox attempts failed on temporary-directory permissions and are retained separately; those initial attempts belong to the earlier audit. The current verified outputs were regenerated after the authorized reconciliation.

The provisional projected order in this run was A80-A89, B25-B34, A00-A09, B00-B09, B90-B94, A15-A19, B85-B89. Exact totals and evaluation outputs are in the JSON evidence and listing output blocks. This is the recorded prototype result, not a recommendation to adopt these ranks as final thesis findings.

The real-library synthetic verification also attempted all seven candidates: two completed hybrids, five `xgboost_insufficient_history` results for blocks absent from that synthetic upload, 24 stored monthly forecasts and unavailable Top Five. See [synthetic-verified.txt](evidence/synthetic-verified.txt). These are explicit technical outcomes inside modeling, not coverage exclusions. The existing headless browser workflow passed login, activation, actual forecasting, HTML download, mobile layout and viewer permissions without browser errors; see [browser-verified.txt](evidence/browser-verified.txt). Static Python checks and diff-whitespace checks passed. The 51 generated excerpts were checked byte-for-text against their source spans and source-file SHA-256 values.

## Inventory scope

The complete numbered inventory is at the end of [PYTHON_CODE_LISTINGS.md](PYTHON_CODE_LISTINGS.md). “Included in Thesis: Yes” means the code may document the current active implementation with these qualifications. Archived weekly/PIDSR, 52-week and superseded algorithms are marked excluded. Unwired helpers are also excluded rather than misrepresented as active operational training. The model family is finalized; the execution settings remain explicitly provisional. The implementation was reconciled to the all-seven study rule, not relabeled as approved final methodology.
