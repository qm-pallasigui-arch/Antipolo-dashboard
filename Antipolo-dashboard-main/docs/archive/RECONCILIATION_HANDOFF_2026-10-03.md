> Revision 45 update: see [current reconciliation](REVISION45_REPORT.md). The authorized exploratory protocol is installed; earlier pending-default statements below are historical.

# Daily reconciliation and forecast-model handoff

**Date:** 3 October 2026, Asia/Manila.

**Status:** Today's implementation changes are consolidated and verified. The Hybrid SARIMA–NNAR implementation is complete for the supported configurable workflow. Final statistical settings, real-source training readiness, and demonstrated forecasting accuracy remain pending. This document supersedes older handoffs for today's weekly-interface behavior; it does not overwrite historical evidence.

## Reconciled implementation

| Area | Final behavior today | Evidence |
| --- | --- | --- |
| Workbook scope | Reversible Include/Exclude per worksheet; Notes and other recognizable non-data sheets are suggested for exclusion. Only included sheets gate confirmation. | WORKSHEET_REVIEW_REPORT.md; tests/browser_worksheets.py |
| Transformation review | Independent cards, explicit worksheet name, original/prepared previews, Required labels, red unresolved fields, plausible mapping choices, inferred fields retained. | tests/test_transformation.py |
| Wide weekly tables | Year columns unfold automatically; worksheet name may supply Disease. Counts are never summed across years. | tests/test_transformation.py |
| Invalid-week footer recovery | Recognized verification totals are excluded automatically, retained in the source, and disclosed in a warning and exclusion table. Unknown invalid weeks remain blocked with actual worksheet rows and values. | Local workbook regression; WORKSHEET_REVIEW_REPORT.md |
| Forecast horizon | A single 52-week path is displayed over 4/13/26/52 weeks. Historical holdout metrics do not change with display length. Historical-only charts explicitly say no forecast is available. | FORECAST_VIEW_REPORT.md; tests/test_weekly_views.py |
| Model comparison | Hybrid SARIMA–NNAR is primary; SARIMA-only is separate. No silent replacement of a failed Hybrid. | dashboard/weekly/model.py |
| Metrics | MAE/WAPE on Forecast; MAE/RMSE/MAPE/WAPE in advanced details. Unavailable evaluations show status/reasons, never invented scores. | tests/test_weekly_views.py |
| Reporting chart | Complete and incomplete/unknown reports are separate traces; unknown reports remain visible but are excluded from training. | tests/test_weekly_views.py |
| Overview | Confirming the replacement activates it and refreshes source/disease/count/latest-week information. A pending upload does not replace active data. | Edge/Playwright replacement check |
| Historical controls | Weekly/monthly/quarterly selectors use corresponding period options. Calendar summaries require source week-start dates; unavailable views explain the requirement. | Edge/Playwright quarterly-history.png |
| Warning recovery | Review details now explain how to proceed with missing counts and week 53. | dashboard/weekly/presentation.py |

## Local workbook readiness: newly checked today

Source: `reconciliation/sources/Antipolo_Disease_Surveillance_2016-2025.xlsx`.
Machine-readable evidence: `evidence/reconciliation-2026-10-03/source-readiness.json` (includes file SHA-256).

- 1,590 prepared weekly observations: 530 each for Leptospirosis, Measles-Rubella, and Dengue.
- Notes excluded; all three disease worksheets prepare successfully; no activation errors.
- 9 blank counts, 30 supplied week-53 observations, and no absent week positions under the current validator's source-calendar treatment. This does not certify calendar correctness or reporting completeness.
- All 1,590 observations currently have incomplete/unknown reporting eligibility because the source does not establish reporting status. They therefore cannot currently supply complete training observations.
- Reporting-year lengths are not established in metadata.
- The inspected process has no usable installed weekly model protocol; SARIMA candidate specification remains pending.

The workbook can be confirmed for inspection. Confirmation alone does not make it ready for forecasting or final thesis evaluation.

## How to handle the two warnings and move forward

### “Some case counts were not reported. Blank values have not been changed to zero.”

This is a data-quality warning, not an activation error by itself. A blank means unknown/unreported, while zero means a source-confirmed zero count.

1. Inspect the Unreported case counts details for affected disease/year/week records.
2. Request corrected counts or source clarification. Only enter zero when the source confirms zero. Re-upload and confirm a corrected version; preserve original evidence.
3. If a source confirms that a blank week-53 cell represents a nonexistent reporting week, reconcile that with the source calendar through an explicit, documented correction. Do not automatically delete it or label it zero.
4. A configured SARIMA state-space missing-data policy may fit across gaps without filling source values. A reject policy stops fitting instead.
5. NNAR trains on complete residual lag windows without compressing time across gaps. Too few windows or an incomplete final lag window means Hybrid unavailable. Show the reason; retain SARIMA-only as a labeled comparison if available. Never relabel SARIMA as Hybrid.
6. Missing actual counts are excluded from historical scoring using the same positions for both models; the excluded count is recorded. Zero actual counts remain in MAE/RMSE/WAPE; percentage metrics retain their documented denominator rules.

### “Week 53 was preserved from the source data.”

This is informational by itself. Preservation prevents accidental loss or remapping; it does not establish that all years actually contain 53 reporting weeks.

1. Obtain the source reporting calendar and confirm each year's 52/53-week length, including relevant forecast-boundary years.
2. Keep legitimate week-53 counts in their original disease/year/week positions. Never merge them into week 52 or another year to make a model run.
3. A declared 52-week calendar with a supplied week-53 record is a source conflict and blocks activation. Resolve it against source evidence; do not invent the calendar.
4. Modeling needs an explicit `week53_policy`. The implemented `preserve_sequence` policy keeps week 53 as an additional ordered observation. It does not automatically establish the correct SARIMA seasonal period.
5. Undetermined future calendar labels are displayed as forecast offsets rather than invented dates. Historical cross-year fitting requires known boundaries.

## Forecast-model finalization boundary

The user's earlier updated handoff explicitly says not to invent final SARIMA seasonal period/search grid, NNAR lags, holdout, rolling-origin design, or formal 95% interval methodology. Today's request does not supply these statistical decisions. A clarification is pending on whether to prepare an exploratory configuration or install a documented approved protocol.

Existing implementation:

- Explicit permitted SARIMA candidates are fitted; NNAR models their residuals recursively. Hybrid predictions add the residual correction and are clipped at zero.
- Configured missing-data and week-53 policies are enforced. NNAR failure and optimizer convergence are surfaced.
- Chronological holdout fitting uses pre-holdout data only, with shared scoring positions for both models. The supported evaluation is a single holdout; rolling-origin evaluation is not implemented.
- The uncertainty shading is provisional training-residual-RMSE shading, not a calibrated 95% prediction interval.
- Configuration is installed via `WEEKLY_MODEL_CONFIG`; research requirements via `WEEKLY_RESEARCH_CONFIG`. Neither may fabricate source reporting completeness, population, classification, or calendar facts.

Before a real-data final forecast:

1. Confirm source reporting completeness and year calendars; establish source population, classification, and provenance for the intended research context.
2. Supply or explicitly choose an exploratory protocol: SARIMA candidate orders/seasonality, NNAR lags/nodes, minimum history/residual windows, holdout, missing/week-53 policy, convergence limits, and reproducibility seed.
3. Validate and install the protocol. Keep exploratory runs labeled technical/retrospective; only document adviser approval when actually supplied.
4. Run each disease; retain status, chosen candidate, diagnostics, evaluation period/coverage, and both models' scores. Missing results remain unavailable with reasons.
5. Assess accuracy from those scores and limitations. No numerical accuracy claim for the local workbook is supported by today's synthetic browser tests.

## Verification and continuation

The immediately preceding full run passed **213 tests**, with 10 existing Dash DataTable deprecation warnings. The Edge/Playwright workflow passed **12 checks**, with no page errors, including replacement Overview refresh and monthly/quarterly charts. The separate worksheet browser suite previously passed seven checks. Static checks passed. The guidance-only change in this handoff receives a focused regression check recorded below.

Read next: this report; `WEEKLY_SYSTEM.md`; `WORKSHEET_REVIEW_REPORT.md`; `FORECAST_VIEW_REPORT.md`; `dashboard/weekly/{transform,data,model,settings,ui,presentation,charts,outputs}.py`.

Preserve the dirty working tree and untracked evidence. Older `AGENT_HANDOFF.md` and pre-weekly model scores describe historical monthly behavior and are not current weekly-model acceptance evidence. No deployment, commit, adviser approval, prospective validation, or source-data correction is implied by this handoff.

Final focused check: `python -m pytest tests/test_weekly_views.py tests/test_transformation.py -q` ? **43 passed** after adding warning-recovery guidance.
