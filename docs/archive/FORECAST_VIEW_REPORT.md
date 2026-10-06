> Revision 45 update: see [current reconciliation](REVISION45_REPORT.md). The authorized exploratory protocol is installed; earlier pending-default statements below are historical.

# Forecast and historical-view reconciliation

Date: 2026-10-03

- Forecast horizon: the model generates a single 52-week path. Next 4/13/26/52 weeks selects a prefix, preserving the forecast issue and earlier values. Charts now state the selected horizon and focus on recent history plus the selected future weeks. If no forecast exists, the interface explicitly identifies the chart as historical reports only.
- Evaluation: historical holdout scores are separate from the future display range. MAE and WAPE remain fixed when that display range changes. Both model rows display evaluation status, including reasons when evaluation could not run. A configured holdout records its length and scored-week count.
- Hybrid implementation: SARIMA forecasts plus recursively forecast NNAR residual corrections, clipped at zero. SARIMA-only remains a separately labeled comparison. Source inspection confirms this implementation; no claim of demonstrated accuracy on the surveillance workbook is made. Default model settings remain pending, and synthetic fixture success does not establish real-data accuracy.
- Reporting markers: complete and incomplete/unknown observations now occupy separate traces. Excluded values remain visible without duplicating them in the complete-report trace. Reporting status controls training eligibility; exclusion does not mean the source count was deleted.
- Overview: uses the activated dataset, falls back to its first disease during selection refresh, and shows latest supplied week, included disease count, and selected-disease observations even when completeness is unknown. Confirmation, not file selection, activates replacements. Stale result metrics are suppressed before rendering technical details.
- Historical views: monthly and quarterly options require valid source Week Start Date values. Their range selectors show months/quarters and filter those periods. Without dates they are disabled with guidance and the selection resets to Weekly. Whole weekly totals are assigned to the month/quarter containing their source start date; cases are never split or dates invented from morbidity-week numbers.

Regression coverage: tests/test_weekly_views.py and tests/browser_revision39.py include horizon lengths, metric rendering, distinct reporting traces, replacement overview, source-date grouping, dynamic period controls, and missing-calendar behavior.

Validation completed: 213 automated tests passed; 12 Edge/Playwright browser checks passed with no page errors. Static checks passed. Quarterly-history screenshot was inspected.
