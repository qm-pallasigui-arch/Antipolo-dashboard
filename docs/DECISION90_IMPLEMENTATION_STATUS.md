# Decision 90 integration – 10 October 2026

Production forecasting now uses Decision 90 from the validated Active Dataset. Upload, transformation, confirmation, source-calendar evidence, and missing/zero rules remain intact.

## Clarifications incorporated

1. Take the union of SARIMA orders shortlisted in any validation window, then refit every union candidate at all three training cutoffs. Only candidates with valid forecasts and metrics in every window can rank.
2. MAPE is not applicable for an all-zero window. Average it over applicable windows and record coverage. When all three windows have undefined MAPE, rank on RMSE/MAE only and flag the omission.

## Implementation

- `selection.py`: authoritative 144-model SARIMA grid, 20 NNAR configurations, validity checks, AIC shortlists, scoring coverage, equal-window means, and deterministic ranking.
- `evaluation.py`: window-specific fits/residuals, shortlist union, signed additive corrections, locked winners, final 52-position holdout, and full-history operational refits.
- NNAR uses consecutive lags, at least 52 complete residual samples, logistic hidden and linear output, five initializations (seeds 42–46), lowest converged training loss, and recursive prediction.
- Official scores use clipped final forecasts and shared finite-actual positions. Zeros remain in RMSE/MAE; MAPE coverage is explicit. Raw paths remain in the audit.
- SARIMA-only and Hybrid may select different SARIMA orders. Refit failures never select an alternative configuration.
- Complete-but-blank terminal weeks retain their positions; terminal residual gaps cause explicit Hybrid unavailability.
- Main Forecast shows final 52-week metrics. Advanced Details shows selected models, validation measures/coverage, training ranges, horizon metrics, and DM applicability. Detailed Evidence retains the complete audit.
- Production uncertainty calculation, chart bands, and CSV range columns are removed. Legacy stored bands cannot reappear in the chart.
- Cache identity includes version, dataset contents/metadata, disease, and configuration. Stale results are hidden and cannot be issued as snapshots through the UI.
- Production settings enforce Decision 90. Legacy exploratory functions remain only for offline compatibility and historical tests.

Technical conventions are recorded: training-input StandardScaler, existing L-BFGS/L2 settings, 53-position residual burn, average ranks for ties, mean cutoff-specific AIC for the AIC tie break, and NNAR simplicity by parameter count then lag window and hidden nodes.

## Supplementary DM applicability

The holdout is one fixed-origin path spanning horizons 1–52, rather than repeated errors at one horizon. No mixed-horizon DM loss/variance protocol was supplied or previously implemented. The audit/UI explicitly report DM as not applicable; no statistic or p-value is invented. This does not affect selection or primary metrics.

## Verification

- Full suite: 259 tests passed. After the final prediction-error handling and stale-snapshot guard changes, all 37 targeted selection and UI tests passed; pyflakes also passed.
- Real numerical smoke check: valid SARIMA fit and five NNAR fits; selected seed 42; 152 complete residual windows; finite 52-week path.
- Tests cover shortlist union, independent refits, invalid candidates, holdout isolation, unchanged locks when holdout outcomes change, operational failure retaining retrospective metrics, MAPE applicability, clipping, chronology, signatures, and audit export.
- Windows sandbox pytest temporary-directory permissions were handled with a process-local mkdir wrapper using inherited ACLs inside the workspace. Application/security settings were unchanged.
- Full-grid numerical execution on the real workbook was not performed. These tests do not establish real-data forecast accuracy or deployment runtime.

## Deployment limitation

Generation now uses [background jobs](FORECAST_JOBS.md) with progress, cancellation and persistent caching. The fixed search can require 432 SARIMA screening fits, up to 45 union refits, up to 4,500 NNAR initializations, and final refits. The grid is unchanged. Vercel requires the supplied worker API to be deployed on a persistent host and configured through its URL and token. All-age and synthetic runs remain separate from the ages 5–19 confirmed-case research objective.
