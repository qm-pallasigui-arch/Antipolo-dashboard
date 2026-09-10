<!-- @format -->

# Change Log

This file records production-readiness changes for the Antipolo disease-surveillance dashboard. Add future entries under `Unreleased` before moving them into a dated release section.

## Unreleased

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
