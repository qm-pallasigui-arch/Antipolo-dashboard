# Final handoff implementation — 29 October 2026

This handoff supersedes the earlier decision to block all forecasting development. Prototype execution is authorized; final thesis evaluation remains gated on Chapter 3 approval. The source script `icd10_prophet_xgboost_tuning.py` was found in the workspace after the user requested a second check.

## Verification results

- Regression suite: **40 passed, 1 skipped**. The skip is the dedicated Supabase integration test because no test connection was configured. Five existing Dash DataTable deprecation warnings remain.
- Real-library synthetic verification: two hybrid runs, 24 independently stored monthly values; Projected Top Five correctly unavailable.
- Real-library canonical verification: **seven hybrid runs, 84 independently stored monthly values, seven baseline/hybrid evaluations and five derived top ranks**. All artifacts are marked provisional. The original active database was not used for these checks.
- Browser workflow: actual forecast-button execution, two persisted synthetic forecasts, unavailable Top Five, baseline-comparison chart, reports, mobile layout and viewer permissions passed without browser errors.
- Pyflakes, dependency consistency (`pip check`) and diff-whitespace checks passed.
- Repository audit: [20,333 matching lines](final-handoff-audit/static-audit.csv) with dispositions and context; [95 read/decoding limitations](final-handoff-audit/scan-limitations.txt), primarily inaccessible local cache/test artifacts. No unresolved REWRITE disposition remains in active dashboard code/tests/current root documentation. REVIEW items are preserved rather than silently deleted.

Evidence is under `evidence/prototype-handoff-20261029/`: real-model-synthetic.json, real-model-canonical.json, generated HTML prototype reports and browser screenshots/logs. These checks establish prototype software operation, not final thesis accuracy or a verified cloud deployment.

## Source audit and refactor disposition

The preceding repository-wide inventory remains at [the cleanup report](reconciliation-20261029/CLEANUP_REPORT.md). The following delta covers the newly supplied model script and replacement runtime. No original DOH source or canonical CSV/XLSX is deleted.

| File | Line / symbol | Legacy or provisional assumption | Replacement | Action | Risk |
|---|---|---|---|---|---|
| icd10_prophet_xgboost_tuning.py | _synthetic_ds / fit_prophet | Synthetic year-2000 dates | Actual canonical first-of-month timestamps | REWRITE | High: preserve gaps |
| Same | get_fixed_split | A80-A89-specific split | Generic configurable last-reported-year prototype split | REWRITE | High: evaluation changes |
| Same | CSV_PATH / get_block_series | Bundled filename and alternate schema | Activated dataset through canonical model adapter | REWRITE | Medium |
| Same | fit_prophet / _recursive_predict / fit_prophet_xgboost | Silent mean/base fallback | Explicit component failure statuses; no substitute forecast | REWRITE | High |
| Same | _lag_matrix | Adjacent array rows treated as adjacent months | Calendar-month residual lags; unknown lags remain NaN | REWRITE | High |
| Same | compute_mase_scale / main | Full-series scaling includes test observations | Training-only same-calendar-month pairs; undefined scale stays null | REWRITE | High |
| Same | hyperparameters, clip, weight, seed | Experimental constants | Central PrototypeModelConfig and per-run snapshot/hash | KEEP | Clearly provisional |
| Same | original file | Research provenance | archive/model_development, excluded from deployable package | ARCHIVE | Low; original bytes preserved |
| forecasting/config.py | weekly_seasonality=False | Prophet API keyword | Explicitly disables sub-monthly seasonality | KEEP | Not a legacy study mode |
| tests | negative import and invalid-schema checks | Historical tokens in rejection tests | Keep guards that prohibit obsolete runtime paths | KEEP | Low |
| repositories/forecast_repository.py | prototype filtering | Previously excluded every prototype | Accept only versioned new hybrid prototypes; isolate approved results and configuration signatures | REWRITE | High |
| services/ranking_service.py | fewer-than-five output | Partial list labeled Top Five | Empty Top Five plus unavailable status; retain all available ranks | REWRITE | Medium |

## Provisional pipeline

`PrototypeModelConfig` centralizes seed, thread limit, Prophet settings, XGBoost settings, lag count, readiness minimum, residual-row minimum, correction clipping/weight, split rule and MASE season. The initial values follow the supplied tuning script; they are not thesis-approved. Set `PROTOTYPE_CONFIG_PATH` to a JSON override file. A configuration hash is stored with every run and ranking; changing settings hides older incompatible results without deleting them.

`PROTOTYPE_MODE=true` is the default. `false` prevents forecast generation until an approved workflow is implemented; it never relabels provisional results. Readiness uses the states not_assessed, ready, not_ready and methodology_configuration_required. No observations is a not_ready reason. The provisional technical minimum is 17 observations and at least five usable residual training rows with twelve calendar lags. This is development configuration, not an approved epidemiological criterion.

The adapter retains year, month_number, actual_timestamp, consultation_count and observation_status. Prophet fits observed values at actual dates. Calendar residual lags use native XGBoost missing-value handling for unavailable months. Internal gaps are not compressed. After the final observation, any gap before the common forecast origin is bridged with residual predictions only; those predictions never modify source observations. This treatment is provisional and disclosed on each run.

The prototype constructs in-sample Prophet residuals in a separate function. Final chronological error generation can replace this component. The generic evaluation holds out the last reported year and refits both components using only earlier observations. Both Prophet baseline and hybrid MAE/RMSE/MASE and predictions are retained. MASE uses training-only pairs separated by twelve calendar months; a missing/zero scale yields null. No block-specific split or implicit denominator fallback remains.

Completed runs have hybrid_completed, is_prototype=true and methodology_status=provisional. Component errors are recorded as prophet_failed, xgboost_insufficient_history or xgboost_failed; other failures use forecast_failed. prophet_only_fallback is reserved but deliberately not emitted: this implementation does not substitute Prophet when correction fails. No uncertainty interval is claimed.

Every successful run stores twelve individual forecast-value rows and the Prophet baseline values. Rankings require one signature, group, configuration, mode and twelve-month calendar. The complete ranking is retained. Fewer than five successes produces Projected Top Five unavailable and an empty top_five list. All rankings carry the represented-block scope limitation.

## Persistence and deployment

The PostgreSQL boundary in `repositories/database.py` is used by all Store operations when `MONTHLY_DATABASE_URL` is configured. It supports Supabase direct or session-pooler connections with required SSL, a private schema, transactional commits/rollbacks and advisory locks for activation/account checks. A configured PostgreSQL failure never silently switches to SQLite. Local SQLite remains available for development and isolated verification. The existing database is not automatically copied or modified by the cloud switch.

See [Supabase migration and deployment](SUPABASE_MIGRATION.md). No cloud connection credentials were provided; live Supabase and AWS deployment verification require the target environment. A skipped integration test must not be described as a verified cloud deployment.

## API references consulted

Real first-of-month prediction dates follow [Prophet monthly-data guidance](https://facebook.github.io/prophet/docs/non-daily_data.html). Thread/seed controls use the [XGBoost Python API](https://xgboost.readthedocs.io/en/latest/python/python_api.html). PostgreSQL transaction handling follows [Psycopg connection contexts](https://www.psycopg.org/psycopg3/docs/basic/transactions.html); cloud connection setup follows [Supabase PostgreSQL connection guidance](https://supabase.com/docs/guides/database/connecting-to-postgres).
