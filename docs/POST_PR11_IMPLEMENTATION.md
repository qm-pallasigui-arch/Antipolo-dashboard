# Approved post-PR #11 implementation

Implemented 12 October 2026, using PR #11 and the existing staged confirmation fixes as the baseline. The staged data/transformation fixes and evidence files were preserved.

## Model development and operational forecasting

The model version is `weekly-3-tvt`.

**Compute Model Performance** works before a future forecast exists. It constructs the chronological disease series, retaining missing positions, then uses:

1. Training: all positions before the final 104.
2. Validation: the next 52 positions.
3. Final Test: the last 52 positions, including trailing missing source positions.

Each explicit candidate fits Training only and predicts Validation. Hybrid and SARIMA-only are selected independently using the lowest validation RMSE; ties use MAE, then configured candidate order. The configuration is locked and saved before any final-test scoring. The locked configurations are refitted on Training + Validation to predict the 52-position Final Test. No test outcome enters candidate ranking. Failed refits do not select another configuration.

The existing bundled disease specifications form the candidate menu; each named disease currently has one candidate. Validation therefore evaluates and locks that candidate rather than comparing a newly invented grid. Administrators can specify multiple SARIMA candidates and optional `nnar_candidates` entries with `lags` and `hidden_nodes`. At most 64 explicit combinations are allowed. The inherited offline origins of the bundled candidates are retained in their authorization metadata; this implementation does not establish that earlier offline research was free from test-data exposure.

**Generate Forecast** only loads a compatible lock and fits it on all eligible available history, producing one 52-week future path per available model. The 4/13/26/52 controls display prefixes of those paths. No selection or historical evaluation runs during normal generation. Without a compatible lock, the UI directs the user to Compute Model Performance. The bundled minimum requires at least 156 finite Training observations plus the 104 reserved positions.

## Persistence and provenance

SQLite stores configurations and performance at `.weekly-models/registry.sqlite3`; `WEEKLY_MODEL_STORE` can select another durable path. No new service or package is required. Database writes are transactional and connections are closed after use. Production installations should back up this file and place it on durable writable storage. Original prospective snapshots remain separate.

Exact reuse is scoped by disease records, metadata, normalized configuration and model version. Upload/confirmation/extraction timestamps do not invalidate an otherwise identical selection. JSON numeric equivalents such as `1.0` and `1` hash identically, including after browser callbacks.

Operational forecasting also accepts strictly appended weekly records when the earlier model inputs, source context, configuration, version and existing calendar lengths are unchanged. It fits the saved configuration on the extended history without repeating selection. Historical performance retains its original test boundaries and evaluated dataset identifier; it is not presented as a new test on the appended data. Corrections, changed source context, or changed model settings require explicit model development again.

Compute Model Performance on an extended dataset develops/evaluates its new split. If an older future path is still displayed, its generation configuration remains attached to that path and the UI asks the user to generate a new forecast. Older `weekly-2` session forecasts are not displayed as results of this methodology.

## Metrics and failure states

RMSE and MAE include genuine zero actuals. MAPE excludes zero actuals without replacing them; missing actuals are excluded from all three metrics. Coverage includes scored test observations, missing actuals, MAPE-valid observations and zero actuals excluded from MAPE. All-zero observations produce unavailable MAPE. Failed models have no fabricated metric values; an independently valid SARIMA-only model is never relabeled Hybrid.

Selections and test performance survive process restarts. Successful repeated performance requests and exports reuse the stored evaluation. Failed final-test evaluation can be retried against the already locked configurations. A valid future forecast can still be exported when performance is unavailable.

## Interpretation and date basis

Preparedness Interpretation is calculated once from the generated path. It reports 4/13/26/52-week mean directions relative to the finite eligible observations in the last 13 chronological training positions, absolute/percentage changes, the maximum forecast and earliest peak week, projected weeks above the reference and their longest consecutive run. A zero reference has no percentage change. Direction uses a numerical tolerance of `1e-9`, not an epidemiological threshold. If only SARIMA is available, its interpretation is explicitly labeled.

The label is **Forecast-based preparedness interpretation — not an outbreak declaration.** No alert thresholds, outbreak declarations, or uncertainty intervals are generated.

Monthly/quarterly date basis is chosen once for the selected disease: all valid source dates, or all derived reporting-calendar dates. Period dropdowns, filtering and aggregation retain that same basis. Invalid dates trigger the derived basis for every row; filtering cannot silently switch back to source dates.

## UI and downloads

About the Model → Advanced Details includes model status, model version, locked parameters, Training/Validation/Final Test boundaries, metrics and scoring coverage. Detailed candidate records remain in the diagnostics disclosure.

Detailed JSON has four logical sections:

- `future_forecast_results`: disease, model, forecast year/week, count, version and generation timestamp.
- `historical_model_performance`: original evaluated dataset, split boundaries, metrics, coverage and failure status.
- `model_metadata`: operational and historical selected configurations, selection run/date, dataset identities and designations.
- `preparedness_summary`: structured calculations and the same template text shown in the UI.

CSV retains observation and forecast rows, with forecast-specific columns plus JSON columns for performance, metadata and preparedness. No uncertainty interval columns are included. Old interval payloads are stripped at export boundaries and ignored by charts.

## Verification

The full regression suite and focused methodology tests cover real small synthetic SARIMA/NNAR fits, test isolation, persistence across a fresh Python process, appended-history reuse, corrected-history rejection, failed refits, zero/missing coverage, browser numeric round trips, source-date consistency and exports. See the current entry in [TEST_RESULTS.md](../TEST_RESULTS.md) for final counts.

`python tests/browser_postpr11.py` runs headless Edge against an isolated synthetic protocol and registry. It checks first-use selection, future generation, interpretation without a band, Advanced Details, all four downloaded sections and refresh recovery. Evidence is in `evidence/post-pr11-browser/`.

These are implementation checks, not a new accuracy study on the surveillance workbook or external research approval. No three-window robustness study or 432-fit screening workflow was added.
