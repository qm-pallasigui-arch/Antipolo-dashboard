# Thesis readiness — October 25, 2026 monthly revision

The October 24 handoff governs the active monthly ICD-10 application. Legacy weekly data, models and benchmarks are disconnected and retained for historical regression only.

## Implemented

- Monthly CSV/XLSX normalization; count, year, month, code, duplicate and annual-coverage validation.
- Four states; explicit zeros retained; 2020/2022 and outside-Top-5 periods stay null; no interpolation.
- Standalone 8/8-year and 96-month eligibility; all blocks remain descriptive.
- Persistent candidate preview and explicit transactional activation; failure/cancel/reject preserve active data; source bytes/signatures retained.
- Dashboard, Disease Trends, Data & Quality/provenance, forecasting shell, Model Performance, Reports, Notifications, Help & About.
- Password hashing, revocable sessions, server-side roles, administrator user management and viewer restrictions.
- Replaceable forecasting protocol; horizon 1–12; signature/block isolation; previous results survive failed runs.
- Audience-filtered persistent notifications, per-user read state, source annotations and audit records.
- HTML reports with trend, provenance, coverage, eligibility, forecast availability and limitations; JSON/CSV exports preserve states.

## Verification

tests/test_monthly_system.py covers semantics, 8/8 versus 7/8 and 96 versus 95 eligibility, gaps, invalid uploads, normalization roundtrip, CSV/XLSX, activation, persistence, reports, notifications, login/logout, inactive accounts, roles, forged viewer callbacks and replaceable model contracts. Test-double forecasts are not accuracy evidence.

Regression output: evidence/monthly-full-suite.txt. Browser checks use synthetic fixtures isolated from the default database.

Verified: 349 tests passed in the full regression suite. A real headless Edge run
passed login, upload/staging, preview, explicit activation, monthly chart rendering,
HTML download, methodology-pending forecast state, mobile layout, logout and viewer
read-only access with no JavaScript errors. Screenshots: evidence/monthly-desktop.png
and evidence/monthly-mobile.png. A candidate dropdown update race found by this run
was repaired and the browser workflow rerun successfully. Static checks passed.

## Inputs and limitations

UI consistency update: shared components now cover every monthly module and
login/account pages, with one chart theme used in exported reports. Verification:
351 regression tests passed; desktop/mobile Edge checks covered all modules,
account-page styling, activation confirmation cancel/accept, report download,
mobile navigation and viewer restrictions without browser errors.
Evidence: `evidence/monthly-shared-ui-tests.txt`, `evidence/monthly-ui-browser.txt`.

- The official revised dataset was not supplied. Upload a verified canonical transcription. The older workbook is not current study evidence.
- Direct PDF extraction and arbitrary spreadsheet mapping are not implemented. Use canonical columns and review the normalized preview.
- Incomplete reported annual entries are rejected rather than assigned a misleading fifth state. Standalone eligibility diagnoses 95/96 observations independently.
- No approved engine exists. Forecast generation remains unavailable while descriptive analysis, reporting, security and notifications work. Uncertainty intervals and statistically justified increase alerts await approval.
- The forecast contract is synchronous; retained job infrastructure can be adapted when an expensive approved engine is added.
- Account management covers creation, roles and active status; password recovery is outside this minimum implementation. Initial administrator setup is an operator command.
- No deployment or real-source validation was performed. Production needs persistent storage, HTTPS and protected database/key files.

## Research decisions awaiting approval

`[TO FINALIZE: forecasting methodology]`

- `TODO THESIS-METHOD: finalize final algorithm and candidate models.`
- `TODO THESIS-METHOD: finalize hybrid/ensemble design, if any.`
- `TODO THESIS-METHOD: finalize model-selection rule.`
- `TODO THESIS-METHOD: finalize evaluation metrics at 1, 3, 6 and 12 months.`
- `TODO THESIS-METHOD: finalize exact chronological validation strategy.`
- `TODO THESIS-METHOD: finalize treatment of city-wide missing years during fitting.`
- `TODO THESIS-METHOD: finalize uncertainty interval method.`

The active pipeline resolves none of these decisions and imports no legacy model fallback.
