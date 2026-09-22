<!-- @format -->

# Change Log

This file records production-readiness changes for the Antipolo disease-surveillance dashboard. Add future entries under `Unreleased` before moving them into a dated release section.

## Unreleased

### 2026-09-22 - Persistent upload summary

- **Change:** Added an always-visible, session-persistent Upload Summary so users can verify upload success or failure, filename and load time, uploaded year coverage, per-disease real-versus-mock status, row counts, date ranges, data-quality notes, and a validated-row preview.
- **Scope:** Added the `store-upload-summary` session store; extended the upload callback to persist structured metadata and preserve or regenerate it safely after a refresh; rendered the summary with the dashboard's existing warning-panel and DataTable patterns. Real-disease metrics describe validated uploaded rows before mock backfill, while missing diseases describe their generated mock series.
- **Data quality:** Added an independent month-gap check for real disease data. It reports entirely absent months between the first and last observation while correctly treating explicit zero-case rows as present; duplicate-row warnings remain a separate validation check.
- **Validation:** Added regression coverage for summary keys and per-disease counts, zero-case-versus-missing-month behavior, refresh persistence, callback wiring, and failed-upload summaries. Full suite: `42 passed` with `pytest tests/ -v`.
- **Follow-up:** The repository currently defines seven tracked diseases, so the summary follows that canonical configuration automatically.

### Completed

- Added upload resource limits:
  - 10 MB maximum decoded upload size.
  - 100,000 maximum CSV rows.
  - 20 maximum workbook sheets.
  - 10,000 maximum worksheet rows.
  - 250 maximum worksheet columns.
  - 1,000,000 maximum parsed workbook cells.
- Normalized CSV headers by trimming whitespace and lowercasing before required-column validation.
- Restricted uploads to the supported `.csv` and `.xlsx` formats. Legacy `.xls` files are rejected because no `.xls` parsing engine is deployed.
- Replaced browser-facing parser, callback, and model exception details with bounded user messages while retaining diagnostics in server logs.
- Hardened malformed browser-session cache, stored-data, and chart-rendering paths.
- Added the `/healthz` endpoint and a matching Docker `HEALTHCHECK`.
- Added `.dockerignore` rules for repository metadata, tests, caches, virtual environments, local logs, and development artifacts.
- Reconciled Dockerfile, Procfile, README deployment examples, and package metadata around the pinned dependencies and one-worker/600-second Gunicorn policy.
- Added monthly Dependabot updates for pip dependencies and GitHub Actions.
- Added callback and production-safety regression tests covering layout contracts, uploads, malformed files, resource limits, unsupported formats, and health checks.
- Reduced callback/parser complexity so every dashboard function is radon grade A or B.
- Verified the repository with 35 passing tests, radon complexity analysis, pyflakes, and `pip-audit`.

### Future work

Track planned or newly discovered work here. Each entry should include the motivation, affected files or systems, and validation required.

- [ ] Add callback tests for cache hits, cache invalidation, stale cache schemas, and lazy model computation.
- [ ] Decide and document whether missing monthly observations mean zero cases or unknown reporting; update the modeling pipeline accordingly.
- [ ] Add an automated container startup smoke test that imports `app:server` and checks `/healthz`.
- [ ] Replace deprecated literal-string `pandas.read_json` usage in tests with `StringIO`.
- [ ] Plan the migration from Dash `DataTable` to `dash-ag-grid` before the component removal becomes blocking.
- [ ] Reassess browser session storage if uploaded datasets or cached model results grow beyond the current small-client use case.
- [ ] Consider server-side per-session state with expiry and access controls for larger deployments.
- [ ] Review Gunicorn recycling and graceful-shutdown settings using production memory and runtime measurements.
- [ ] Continue monthly dependency updates through Dependabot and run `pip-audit -r requirements.txt` before releases.

## Entry template

Copy this template into `Unreleased` for future work:

```markdown
### YYYY-MM-DD - Short change title

- **Change:** What changed and why.
- **Scope:** Files, deployment settings, or user-visible behavior affected.
- **Validation:** Tests, scans, or manual checks run.
- **Follow-up:** Any remaining risk or next action.
```
