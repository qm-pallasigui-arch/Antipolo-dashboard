# Revision 39 reconciliation and verification

Prepared 2 October 2026, Asia/Manila.

## Outcome

The weekly backend and research-integrity controls are retained. The normal workflow now uses automatic CSV/XLSX preparation, an original-versus-prepared review popup, ordinary source-information fields, explicit confirmation, and inspectable transformation history. Raw JSON editors have been removed. Navigation is **Overview**, **Forecast**, **Historical Trends**, **Data**, and **About the Model**.

Recognizable source files no longer need the four internal column names. Ambiguous mappings require explicit column choices. The system does not infer population, confirmed status, source system or reporting completeness from workbook shape. Default statistical settings remain pending, and no adviser-approved weekly methodology is invented.

## Acceptance reconciliation

| Updated handoff criterion | Result and evidence |
| --- | --- |
| 1. Recognizable existing CSV/XLSX works without manual restructuring | Implemented: canonical and aliased long tables, disease worksheets, and legacy week-by-year tables. |
| 2. Automatic transformation | Implemented: upload triggers source reading, preparation and review automatically. |
| 3. Canonical structure stays internal | Implemented: users see familiar field labels and mapping dropdowns. Internal records remain disease/year/morbidity week/case count. |
| 4. Original data visible | Implemented: original filename, sheet, headings, row count and up to eight source rows appear in review. Source rows remain retained. |
| 5. Prepared data visible | Implemented: weekly preview and observation count appear beside the source preview on desktop and below it on mobile. |
| 6. Review Data Transformation popup | Implemented and browser-tested. It opens automatically after preparation. |
| 7. Plain-language mapping decisions | Implemented: “What changed?” lists detected disease hints, matched columns, unfolded year columns and explicitly excluded totals/empty rows. |
| 8. Plain-language warnings | Implemented: missing weeks, unreported counts, week 53, duplicates, source conflicts and incomplete reporting remain visible. |
| 9. Explicit confirmation | Implemented: only Confirm & Use Data activates reviewed records, then navigates to Overview. |
| 10. Cancel preserves current data | Unit- and browser-tested, including cancellation of a replacement while synthetic data remain active. |
| 11. Guided ambiguous mapping | Implemented and browser-tested: source-column dropdowns include samples; duplicate field assignments are prevented and checked again on the server. |
| 12. No normal JSON editors | Verified in layout tests and the browser. Model/study settings are administrator-maintained. |
| 13. No visible implementation labels | Normal controls and statuses use user-facing language. Component IDs remain internal HTML/automation identifiers. Read-only technical output is explicitly collapsed. |
| 14. Weekly backend retained | Existing weekly fitting/evaluation logic is retained. Successful test forecasts contain 52 weekly points. |
| 15. Integrity rules retained | Tests cover missing versus zero, blanks, week 53, duplicate observations, classification/population separation, no Hybrid substitution and source provenance. |
| 16. Advanced information collapsed | About the Model explains methods first; Advanced Details contains diagnostics, settings, evidence export and prospective support. |
| 17. Real-browser end-to-end review | Completed using Microsoft Edge through Playwright: upload, review, confirmation, Overview, synthetic Forecast, and pending-protocol behavior. |
| 18. Responsive review | Completed at 1440×1000 and 390×844; screenshots inspected. No page-level horizontal overflow in the tested mobile data/review views. Tables scroll within their containers. |
| 19. Transformation/activation interaction tests | Completed: automatic and manual preparation, source-information updates, cancellation, same-file reupload, confirmation, reopening history and horizon changes. |
| 20. CHO/research-oriented experience | Replaced developer forms with a guided flow, restrained cards and plain-language explanations. This is an implementation and visual review, not a formal CHO participant usability study. |

## Supported source transformations

- CSV or XLSX long tables with canonical headings or explicit aliases, including Diagnosis, Reporting Year, Week No and Total Cases.
- Multiple XLSX worksheets inspected independently; disease worksheet names supply hints only when appropriate. Generic names such as Sheet1 do not establish a disease.
- Morbidity Week rows with year columns are unfolded into weekly observations without aggregation. Blank cells remain unreported, zeros remain zero and week 53 remains week 53.
- A source disease-column/worksheet-name conflict requires a user choice. Distinct Measles and Measles-Rubella labels are not merged.
- Repeated year headings retain both source counts and trigger duplicate-observation validation instead of silently dropping a column.
- Explicit total/empty rows remain in the source evidence but are not modeled as weekly observations. Extra columns remain in the original data and are identified as unused for modeling.
- Unknown layouts use the same review flow after manual matching. Known month/quarter columns cannot be relabeled as morbidity weeks.

Irregular layouts that cannot be safely identified still require matching or source correction. Monthly-only reports are not converted into fabricated weekly counts. Fundamentally unreadable files receive a readable file-opening error.

## Verification results

| Check | Recorded result |
| --- | --- |
| Full regression suite | **199 passed**, 10 historical Dash DataTable deprecation warnings, 64.40 seconds. |
| Focused weekly/transformation suite | **87 passed**, 10.00 seconds. These overlap the full-suite tests. |
| Final Edge browser workflow | **11 checks passed**, no browser page errors reported. The final server log contains no traceback or HTTP 500 response. |
| Static analysis | `python -m pyflakes dashboard/weekly tests/test_weekly.py tests/test_transformation.py tests/browser_revision39.py` — clean. |
| Whitespace | `git diff --check` — no whitespace errors; existing Git LF/CRLF notices remain. |

The final browser pass followed the last upload-reset refinement. The full-suite result precedes that client-side refinement; browser interaction testing specifically verifies the resulting same-file reupload and fast replacement behavior. No new statistical performance claim is inferred from these software checks.

Browser testing found and resolved two interaction issues: absent dynamic field identifiers after a cancelled review, and an asynchronous upload reset that could erase a newly selected replacement. Resetting the upload selection now occurs immediately in the browser while reviewed/active records remain separate.

The forecast interaction test uses an explicitly **synthetic-only test configuration**, installed only for the test server. It is not a production default or adviser approval. The browser also tests an empty/pending protocol and confirms the plain-language unavailable state. The test server is stopped after each run.

## Inspectable evidence

- [Browser check results](evidence/revision39/browser-results.json)
- [Desktop upload](evidence/revision39/desktop-data.png)
- [Desktop transformation review](evidence/revision39/desktop-transformation.png)
- [Desktop overview](evidence/revision39/desktop-overview.png)
- [Desktop synthetic forecast](evidence/revision39/desktop-forecast.png)
- [Manually matched transformation review](evidence/revision39/desktop-manual-review.png)
- [About the Model](evidence/revision39/desktop-about.png)
- [Mobile data view](evidence/revision39/mobile-data.png)
- [Mobile transformation review](evidence/revision39/mobile-transformation.png)
- [Mobile prepared-data view](evidence/revision39/mobile-prepared-data.png)
- [Mobile pending forecast](evidence/revision39/mobile-pending-forecast.png)
- [Browser reproduction script](tests/browser_revision39.py)
- [Transformation regression tests](tests/test_transformation.py)

All browser source fixtures are artificial testing records, not real Antipolo surveillance evidence. Screenshots and the test configuration must not be cited as real-data model validation.

## Configuration and remaining research dependencies

Normal users do not edit model dictionaries. Administrators can point `WEEKLY_MODEL_CONFIG` to the installed model protocol, and `WEEKLY_RESEARCH_CONFIG` to documented disease-scope/history requirements. The research configuration accepts only study requirements; it cannot fill unknown population, classification, source or completeness. Without approval evidence, thesis eligibility remains pending.

Source reporting calendar lengths can be declared through optional ordinary dropdowns when established by the source. Unknown calendar facts stay unknown. Monthly/quarterly summaries still require source-established week dates and remain display-only.

Final SARIMA seasonal assumptions/candidates, NNAR design, evaluation protocol, gap/week-53 treatment and validated uncertainty remain adviser-dependent. Prospective-validation recordkeeping remains structural support, not a completed prospective study. Eligible-real-data evaluation, actual adviser approval and formal CHO acceptance are not established by this interface revision.

Transformation evidence is retained with the active dataset and detailed exports. Session state and local prospective files retain the prototype storage limitations documented in [WEEKLY_SYSTEM.md](WEEKLY_SYSTEM.md). Historical modules, source evidence and pre-existing workspace changes remain preserved.
