# Revision 39 verification - 2 October 2026

- Full regression suite: `python -m pytest -q -p no:cacheprovider` — **199 passed**, 10 historical DataTable deprecation warnings, 64.40 seconds.
- Focused weekly/transformation suite: `python -m pytest tests/test_weekly.py tests/test_transformation.py -q -p no:cacheprovider` — **87 passed**, 10.00 seconds.
- Final real-browser workflow: `python tests/browser_revision39.py` — **11 checks passed**, no browser page errors; final server log has no traceback or HTTP 500 response.
- Desktop **1440×1000** and mobile **390×844** screenshots were inspected. Evidence and reproduction details are in [REVISION39_REPORT.md](docs/archive/REVISION39_REPORT.md) and [evidence/revision39/browser-results.json](evidence/revision39/browser-results.json).
- Static analysis of the weekly modules and revised test files passed. Whitespace checks passed, with existing LF/CRLF notices.

The final browser pass followed the client-side upload-reset refinement and directly verified same-file reupload and fast replacement. The preceding full-suite and focused-suite counts overlap; they are not additive. Synthetic browser fixtures and test model settings establish software behavior only, not adviser-approved methodology or surveillance performance.

## Historical weekly redesign verification - 1 October 2026

- Full suite: `python -m pytest -q` — **170 passed**, 14 Dash DataTable deprecation warnings, 58.24 seconds.
- Final weekly verification after the row-context reconciliation check and metadata-default refinement: `python -m pytest tests/test_weekly.py -q` — **58 passed**, 4 DataTable deprecation warnings, 7.22 seconds.
- `python -m pyflakes dashboard/weekly tests/test_weekly.py` — clean.
- Fresh-process startup: 7 weekly callbacks; layout, health and weekly CSS routes return HTTP 200. A subprocess regression verifies that normal startup does not register historical monthly callbacks.
- `git diff --check` — no whitespace errors; Git reports existing LF/CRLF normalization notices.

Weekly tests cover canonical CSV/XLSX, invalid fields, missing/blank/zero distinctions, duplicates, week 53 preservation, source-label separation, eligibility/context isolation, incomplete-week exclusion, explicit Hybrid failure, real synthetic SARIMA/NNAR execution, 52-point paths, chronological evaluation and shared actual masks, cache isolation/reuse, activation and stale-preview clearing, exports, and append-only prospective revisions with population-context checks.

The initial sandboxed runs could not access pytest's temporary-directory/cache permissions. The reruns with the required filesystem access passed. Browser visual automation was unavailable; layout/callback/HTTP behavior was checked, but no browser screenshot review is claimed. Passing software tests do not establish statistical protocol approval, real-data performance, or completed prospective validation.

## Historical test results - 27 September 2026

The final full suite passed **112 tests, 10 warnings, 0 failures, 0 skipped** in 56.93 seconds.
This is software verification, not source eligibility, clinical validity, or expert acceptance.

| Phase | Exact command | Result / artifact |
|---|---|---|
| Initial working tree | `python -m pytest -q` |85 passed, 11 warnings, 20.82s; reconciliation/baseline-tests.txt |
| Focused revised modeling | `python -m pytest tests/test_modeling.py -q -p no:cacheprovider` |20 passed, 43.36s at that intermediate stage; modeling-tests.txt |
| Intermediate full check | `python -m pytest -q -p no:cacheprovider` |100 passed, 1 failed, 10 warnings; full-tests-intermediate.txt. Failure was obsolete chart assertion expecting Selected forecast; corrected to Primary forecast. |
| Final full check | `python -m pytest -q -p no:cacheprovider` |112 passed, 10 warnings, 56.93s; reconciliation/full-tests.txt |
| Original and revised numerical runs | `python -m reconciliation.evaluate <output.json>` |Original run used initial implementation; revised runner uses audited source-monthly-independent.csv.10 series each, complete arrays/diagnostics saved. |
| Independent source arithmetic | `python reconciliation/source_reconcile.py` |1590 source/workbook cells, 360 monthly observations, 30 annual sums; source-verification-run.txt and source-reconciliation.json |
| Independent evaluation arithmetic | `python reconciliation/verify_evaluation.py` |20 version/dataset/series records verified; numerical-verification.json |
| App and exports | `python -m reconciliation.verify_application` |Four HTTP routes200;3 actual all-age component/trace/export paths; application-verification.json |
| Compilation | `python -m compileall -q dashboard tests reconciliation` |Passed; no syntax failures in final scripts |
| Installed dependency compatibility | `python -m pip check` |No broken requirements found; pip-check.txt |
| Static check | `python -m pyflakes dashboard tests` |Exit1 for 2 intentional side-effect callback imports in dashboard/callbacks/__init__.py; static-check.txt. No new unused variables/imports remain. |
| Installed versions | `python -m pip freeze` |environment-freeze.txt |

Final warnings are10 Dash DataTable deprecations. The initial run had the same10 plus a pytest cache permission warning; subsequent runs disable the cache provider and do not alter protected cache directories. The first verification-script invocation as a direct path failed to import app; the script now adds repository root and the module invocation passed. An early report-generator bracket error was fixed before artifacts were produced. These attempts did not alter source evidence or model results.

## Environment

The existing interpreter/package environment was used without installing/upgrading packages or overwriting it. Python 3.13.3 on Windows. Project metadata requires Python>=3.12; Docker targets3.12. These are distinct from the tested interpreter. A clean pinned environment/container was not verified.

| Package | Tested installed version |
|---|---|
| numpy | 2.3.4 |
| pandas | 2.3.3 |
| scipy | 1.16.3 |
| statsmodels | 0.14.6 |
| scikit-learn | 1.4.0 |
| dash | 4.2.0 |
| plotly | 5.19.0 |
| pytest | 9.1.1 |

Repository requirements pin dash4.4.1, plotly7.0.0, pandas3.0.5, numpy2.5.2,
statsmodels0.15.0, scikit-learn1.9.0, openpyxl3.1.5, gunicorn26.2.0 and
pdfplumber>=0.11,<0.13. The recorded installed environment differs from several pins.
`pip check` checks installed dependency compatibility, not availability or correctness of these repository pins.

## Meaningful coverage

Tests cover existing app/ingestion/date/PDF-helper/catalog-confirmation/callback/production-limit behavior,
mandatory hybrid despite a deliberately worse benchmark score, exact2022/2023/2024/2025 training ends,
SARIMA complete failure and neural retry across valid candidates, all-neural failure, preservation of
completed evaluations on production failure, initial residual burn, invalid schema/count/date/duplicate
rejection, mixed population/classification/source rejection, synthetic-upload relabel rejection,
Measles-Rubella preservation, serialization and provenance export. The source-specific PDF audit independently
reads actual reports; mocked generic PDF tests do not certify arbitrary report extraction.

HTTP checks exercise `/`, `/healthz`, `/_dash-layout`, `/_dash-dependencies` using Flask's test client.
Three real evaluated results were deserialized and rendered into Dash components/Plotly trace structures,
then exported with 132 rows each, 12 holdout predictions and 12 future neural components. These are
integration checks, not browser screenshots or a human usability assessment.

## Unverified checks

No browser automation tool was callable; neither playwright nor selenium was installed. Actual browser
rendering, narrow-screen layout, clickable interactions and session-size behavior remain unverified.
No Gunicorn/container deployment, clean dependency installation, public-service security assessment,
CHO acceptance or expert usability assessment was performed. File copies/hashes and Git history bundle
provide recovery; no commit, push, deployment or external message was made.

## Worksheet review update — 2026-10-03

204 tests passed after adding worksheet Include/Exclude, independent preparation and review, required-field guidance, plausible mapping choices, and activation-scope checks. Both Edge/Playwright suites passed: seven worksheet checks and eleven existing workflow checks, with no page errors. See WORKSHEET_REVIEW_REPORT.md and evidence/worksheet-review/results.json.


## Final Revision 45 verification ? 2026-10-03

`python -m pytest -q`: **221 passed**, 10 existing Dash DataTable deprecation warnings, 61.76 seconds. Both browser suites passed (13 workflow checks + 7 worksheet checks), no page errors. Pyflakes and diff whitespace checks passed. Full 16-candidate seasonal synthetic run completed with both 52-point model paths and all four horizon scores. See `evidence/revision45/verification-summary.json` and `REVISION45_REPORT.md`.
