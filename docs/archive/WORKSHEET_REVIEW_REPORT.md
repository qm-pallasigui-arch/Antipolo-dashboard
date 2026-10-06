> Revision 45 update: see [current reconciliation](REVISION45_REPORT.md). The authorized exploratory protocol is installed; earlier pending-default statements below are historical.

# Worksheet review reconciliation report

Date: 2026-10-03

The workbook review now prepares and validates each included worksheet independently. Confirmation activates only the included records. Excluded source sheets remain available in the transformation history.

| Requirement | Implemented behavior |
| --- | --- |
| Worksheet Include / Exclude | Every worksheet has reversible Include / Exclude controls during review. |
| Non-data sheets must not block activation | Empty sheets and obvious non-data sheets default to excluded; the user can include them. Recognizable weekly tables remain included even when their names suggest a summary. |
| Separate transformation units and review cards | Each sheet has its own preparation status, original/prepared preview, changes, and errors. |
| Explicit worksheet context | Every card says “Reviewing worksheet: X.” |
| Required fields and guidance | Only unresolved mapping fields are requested, with Required badges, short guidance, and red highlighting until selected. |
| Confident inference | Already identified fields are displayed as inferred rather than requested again. |
| Meaningful mapping choices | Dropdowns filter by field aliases, plausible values, and existing assignments. Numeric year headers are excluded from Disease choices. |
| Week × year interpretation | Recognized tables automatically unfold year columns into weekly observations. |
| Worksheet name as Disease | Unresolved Disease offers an explicit worksheet-name choice, including generic sheet names when chosen by the user. |
| Non-data exclusion suggestions | Notes, README, Instructions, Summary, and related names show an exclusion suggestion. |
| Confirmation scope | Only included sheets must resolve successfully; excluding all sheets blocks activation. A changed selection cannot activate stale prepared records. |
| Specific errors | Mapping and validation errors identify the responsible worksheet; duplicate observations identify involved included worksheets. |

Validation: 204 automated tests passed. Static checks passed. Seven worksheet browser checks and eleven existing workflow browser checks passed in Microsoft Edge / Playwright with no page errors. Desktop worksheet screenshots were visually inspected; the existing suite also verifies 390px mobile layout.

Evidence:

- `evidence/worksheet-review/results.json`
- `evidence/worksheet-review/required-disease.png`
- `evidence/worksheet-review/excluded-ready.png`
- `evidence/revision39/browser-results.json`

Original zeros, missing observations, source week 53, and worksheet provenance remain preserved. Forecast eligibility and study-methodology requirements remain separate from successful workbook preparation.

## Invalid-week recovery — 2026-10-03

Verified the local surveillance workbook: Dengue and Measles-Rubella contain a `Source-reported total (for verification)` footer. It was incorrectly expanded into ten records and rejected as a week. Recognized verification totals are now automatically excluded from observations, retained in the original source, and listed in a reviewable excluded-row table. An alert at the top of review names each worksheet and explains the automatic fix before confirmation.

Unknown invalid weeks remain blocked: errors now use original worksheet row numbers, show offending values, and explain correction/re-upload or worksheet exclusion. No week numbers or case counts are guessed. Regression coverage includes the actual local workbook successfully preparing and activating, footer exclusions, preservation of blanks/zeros/week 53, and original-row error reporting.
