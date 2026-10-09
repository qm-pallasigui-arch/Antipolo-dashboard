# Methodology reconciliation — 10 October 2026

This report reconciles the current implementation with the [final weekly specification](FINAL_WEEKLY_IMPLEMENTATION_SPEC.md), including the user's shortlist-union and zero-actual MAPE clarifications. It distinguishes implemented behavior from unresolved source-data and deployment requirements. It does not establish forecast accuracy or certify the uploaded workbook's reporting calendar.

## Source-data reconciliation

The workflow remains Upload → Transform → Validate → Review → Confirm → Active Dataset. Forecasting uses the validated Active Dataset and its source metadata. Activation confirms which dataset is in use; it does not establish model eligibility or research eligibility.

Reporting completeness and calendar length are separate declarations. Training eligibility requires complete reporting status supported by a reporting reference. Cross-year labels require source-supported year lengths, including the forecast year. An ISO calendar must not be substituted for a DOH/RESU morbidity-week calendar without source confirmation.

Blank counts remain missing unless explicitly resolved with evidence. An explicit zero remains a reported count. A supplied week 53 conflicts with a declared 52-week year, including when its count is zero. The existing nonexistent-week resolution accepts blank cells only; the interface does not erase, reassign, or reinterpret nonblank week-53 records.

Consequently, the real workbook still requires the applicable DOH/RESU calendar and reconciliation of conflicting records against that source. Declaring every year as 53 merely to pass validation is not a methodological resolution. Obtain the calendar, document each year's length, investigate conflicting source rows, preserve the original workbook, and retain an explanation and source reference for corrections before activating the reconciled version.

The source-calendar interface now displays compact editable cards: four desktop columns (three rows for 2016–2026), two mobile columns, and a forecast-year label. Each dropdown supports Unknown, 52, or 53 weeks. Bulk 52/53 buttons change the pending year selections, including the forecast year; users can then revise exceptions. These buttons neither supply evidence nor bypass validation or confirmation. Returning a year to Unknown removes its declaration.

The activation notification now explicitly says **Dataset activated**, states the record count, and offers Open Forecast and Dismiss. Its wording directs users to check forecast availability rather than asserting that all forecasting requirements are satisfied.

Implementation: [transformation](../dashboard/weekly/transform.py), [validation](../dashboard/weekly/data.py), [interface](../dashboard/weekly/ui.py).

## Model selection and chronological separation

The production configuration is versioned and fixed to Decision 90; fitted parameters and selected orders are learned from the eligible disease series. The search covers 144 SARIMA orders: p and q in 0–2; d, P, D, and Q in 0–1; seasonal period 52. Source year lengths control calendar positions and labels, while this seasonal period remains the specified modeling convention.

Three expanding validation windows each span 52 calendar positions after at least 156 positions of initial history. A separate final 52-position holdout follows validation, requiring at least 364 positions overall. Missingness and model-specific eligibility can still prevent a valid fit; meeting the length threshold alone is insufficient.

At each validation cutoff, the system screens valid SARIMA fits by AIC, applying the specified delta-AIC threshold of 4 and minimum-three/maximum-five shortlist rule where enough valid candidates exist. It takes the **union** of the three shortlists. Every union candidate is refitted and scored at **each** cutoff using only that cutoff's training data. A candidate must yield valid forecasts and metrics in all three windows to enter final ranking. Neither intersection-only eligibility nor freezing the first shortlist is used.

For Hybrid, residuals and NNAR training inputs are derived from the corresponding cutoff-specific SARIMA fit. NNAR searches lag windows 3, 6, 12, 26, and 52 and hidden-node counts 2, 3, 5, and 8. It uses a logistic hidden layer, linear output, training-input standardization, and recursive prediction. Each configuration needs at least 52 complete residual samples. Five seeded initializations (42–46) are attempted, with the lowest converged training loss retained. Existing L-BFGS/L2 conventions, a 53-position residual burn, and iteration limits are recorded in the implementation rather than presented as newly estimated methodological choices.

SARIMA-only and Hybrid are ranked independently and may select different SARIMA orders. Their chosen configurations are locked before holdout evaluation. Each is refitted on pre-holdout history for retrospective evaluation, then on full eligible history for the operational forecast. A failed locked refit is reported as unavailable; it does not trigger selection of an alternative configuration using holdout outcomes.

Implementation: [selection and configuration](../dashboard/weekly/selection.py), [evaluation](../dashboard/weekly/evaluation.py), [model entry point](../dashboard/weekly/model.py).

## Metrics, ranking, and output interpretation

Hybrid combines the signed NNAR correction with the SARIMA forecast before clipping the final count forecast at zero. Official metrics use clipped final forecasts; raw paths remain available in the audit. Comparable scores use shared finite-actual positions. Missing actuals are excluded, while zero actuals remain in RMSE and MAE.

An all-zero validation window has undefined MAPE, but still contributes valid RMSE and MAE. Mean RMSE and MAE weight the validation windows equally. Mean MAPE averages only windows containing at least one nonzero actual, with coverage recorded. If MAPE is undefined in all three windows, ranking uses RMSE and MAE only and explicitly records that MAPE was unavailable.

Selection uses average metric ranks with deterministic ties. SARIMA ties use mean RMSE, MAE, applicable MAPE, mean cutoff-specific AIC, then model simplicity. NNAR ties use the corresponding errors, parameter count, lag length, and hidden-node count. Stable configuration identity resolves any remaining tie.

The final retrospective path spans 52 weeks. The 4-, 13-, 26-, and 52-week summaries are slices of that same path, not separately tuned forecasts. The main Forecast view emphasizes the final 52-week metrics; technical details preserve validation coverage, selected configurations, chronology, and audit information. These retrospective results must not be described as prospective performance.

Production uncertainty bands and exported range columns have been removed. There is no implemented current prediction-interval claim to interpret as a calibrated uncertainty range. Older output should be identified by its model version before interpretation.

## Reconciliation status

| Requirement or issue | Current implementation | Remaining boundary |
| --- | --- | --- |
| Independent AIC shortlists | Union, followed by refits at all three cutoffs | Candidate must succeed in every window |
| All-zero validation actuals | RMSE/MAE retained; MAPE coverage recorded | MAPE omitted from ranking when wholly unavailable |
| Locked holdout evaluation | Separate selection, holdout, and full-history refits | Real-data accuracy is not established by software tests |
| Week-53 integrity | Conflicts remain blocking; original counts preserved | Actual source calendar and conflicting rows need reconciliation |
| Bulk calendar editing | Pending selections only, editable exceptions | Source evidence remains mandatory |
| Research population | All-age technical and synthetic contexts remain separate | Ages 5–19 confirmed-case evidence is required for the stated research objective |
| Supplementary DM comparison | Explicitly reported as not applicable/unavailable | No numeric DM statistic or p-value is implemented |
| Long-running generation | Persistent background jobs, progress, cancellation, cache | Vercel needs a separately deployed persistent worker |

The DM limitation is explicit: the holdout is one fixed-origin path across horizons 1–52. No mixed-horizon loss/variance protocol was supplied or already implemented. The current system does not manufacture a statistic from that path. This is an outstanding methodological decision, not a completed inferential comparison.

## Runtime and reproducibility

Background execution changes delivery, not the statistical search. The fixed grid can require 432 SARIMA screening fits, up to 45 union refits, up to 4,500 NNAR initializations, and final refits. A first uncached run can therefore remain expensive. Progress reporting and cancellation make that work observable and controllable; they do not imply a measured runtime improvement for the full real workbook.

Cache identity includes dataset contents and metadata, disease, configuration, and model version. Durable jobs prevent equivalent submissions from starting duplicate active work and preserve completed results. Failed jobs do not publish a partial successful cache entry. Local workers run outside the request process. Vercel requires the remote worker URL/token and a persistent service with storage; the provided worker has not been deployed as part of this change. See [worker setup](FORECAST_JOBS.md).

## Verification and limits

For this calendar/notification change, 66 targeted tests passed across calendar UX, transformation, Revision 45, and weekly views. Tests cover bulk field isolation, source-reference requirements, preservation of nonblank week-53 conflicts, editing existing declarations, removal to Unknown, and notification semantics.

Local browser checks passed at desktop and mobile sizes: eleven cards form three desktop rows and two mobile columns; both bulk selections work; missing evidence blocks applying declarations; activation displays the distinct notification; Open Forecast and Dismiss work; no browser JavaScript or HTTP error was recorded. Evidence is retained locally under `evidence/calendar-ux/`.

Earlier statistical tests and the real numerical SARIMA/NNAR smoke check are documented separately in [Decision 90 integration](DECISION90_IMPLEMENTATION_STATUS.md). A complete full-grid run on the real workbook, a verified source-calendar reconciliation, numeric DM testing, and a deployed Vercel-to-worker execution are not claimed by this report.
