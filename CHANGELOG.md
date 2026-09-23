<!-- @format -->

# Change Log

This file records production-readiness changes for the Antipolo disease-surveillance dashboard. Add future entries under `Unreleased` before moving them into a dated release section.

## Unreleased

### 2026-09-23 - Callback coverage, source provenance, exports, and flexible preprocessing

#### Scientific provenance and dashboard visibility

- Added a prominent source banner to the surveillance overview. It explicitly
  labels the active dataset as real, mixed, or synthetic and reports the number
  of diseases backed by uploaded records versus generated mock series.
- Added a per-disease source badge beside the forecast selector. Each forecast
  is now visibly labeled `Uploaded real data` or `Synthetic mock` before the
  chart is interpreted. The label does not overstate provenance for generic
  CSV/XLSX uploads that the application cannot independently authenticate.
- Kept the existing detailed source metric and upload summary, so provenance is
  visible at the overview, forecast, and data-quality levels.
- Added graceful `unavailable` and `unverified` states when session data is not
  loaded or cannot be decoded. The UI does not silently imply that unreadable
  data is real.

#### Forecast export

- Added a `Download forecast CSV` action to the forecast tab.
- CSV exports contain the complete observed history and 12-month forecast in a
  tidy format with disease, date, record type, observed cases, forecast cases,
  95% lower and upper bounds, selected model, and data source.
- Downloads are only produced for a successfully cached forecast belonging to
  the selected disease. Missing, failed, or unreadable cached results do not
  create misleading partial files.
- The download button remains visibly disabled until the selected disease has
  a successfully cached forecast.
- Made Plotly's existing image export easier to discover with visible guidance
  next to the CSV action. PNG exports use a stable filename and 2x scale.

#### Flexible CSV and XLSX date preprocessing

- Added an upload-time date-convention selector with day-first, month-first,
  and year-first choices. The selected convention controls ambiguous numeric
  dates instead of relying on a hidden parser default.
- CSV and ordinary row-based XLSX tables can now use any of these date layouts:
  - canonical `year` and `month` columns;
  - `year` and epidemiological `week` columns;
  - `date`, `report_date`, `reporting_date`, `onset_date`,
    `observation_date`, `period`, or `reporting_period`;
  - textual dates and month names;
  - ISO dates and timestamps;
  - Excel 1900-system date serials.
- Daily and weekly observations are normalized to calendar months and summed
  at the dashboard's modeling grain: one row per disease and month.
- Epidemiological weeks continue to use the existing ISO-week Thursday rule,
  including the established week-53 fallback.
- Date parsing, non-numeric case values, negative case values, dropped rows,
  and monthly aggregation are recorded in the upload's data-quality notes.
- Existing DOH/PIDSR workbooks retain their specialized parser. When a workbook
  does not have that layout, ingestion now falls back to ordinary tabular sheets
  with the same limits and validation rules.

#### Offline text-PDF conversion

- Added `dashboard.data.pdf_converter`, a standalone converter for text-based
  PDF tables. It is intentionally excluded from Dash callbacks so table
  extraction cannot consume the web worker and recreate the previous hosting
  timeout failure.
- The converter extracts non-empty tables, identifies likely headers, removes
  repeated page headers, applies the selected date convention, aggregates to
  months, and runs the normal tracked-disease validation chain.
- Output can be canonical CSV or XLSX with `year`, `month`, `disease`, and
  `cases` columns.
- Every conversion also writes `<output>.report.json` with page/table counts,
  rejected-table reasons, parsing and validation notes, coverage, diseases,
  and an explicit manual-review requirement.
- Scanned/image-only PDFs are rejected with a clear explanation. OCR is not
  performed or silently approximated.
- Added `pdfplumber` as the isolated PDF extraction dependency. It is imported
  lazily and is not loaded during normal dashboard startup or uploads.

#### Callback reliability and automated tests

- Expanded the suite from 42 to 61 tests.
- Added direct callback-layer regression coverage for:
  - selected-disease-only lazy computation;
  - reuse of matching cached results;
  - full cache invalidation when the dataset signature changes;
  - safe caching of pipeline failures without exposing exception details;
  - unreadable session data;
  - ready, warning, failed, and not-yet-computed dropdown states;
  - mixed-data and per-disease source indicators;
  - forecast export schema and provenance;
  - prevention of downloads before a forecast is ready.
- Added preprocessing tests for day-first and month-first ambiguity, ISO
  timestamps, textual dates and month names, Excel serial dates, ISO weeks,
  invalid dates, monthly aggregation, generic XLSX fallback, and the PDF
  converter's canonical output and review report.
- Updated the layout contract test for every new callback-facing component.

#### Internal structure

- Added a shared store-deserialization helper to keep source banners, forecast
  callbacks, and aggregate callbacks consistent about dates and legacy source
  defaults.
- Added `dashboard/data/date_parser.py` as the single normalization boundary for
  row-based CSV, XLSX, and extracted PDF tables.
- Preserved upload size, CSV row, workbook sheet, worksheet dimension, and total
  workbook cell limits for the new ingestion paths.

#### Operational notes

- Existing canonical CSV files and DOH/PIDSR workbooks remain compatible.
- The upload default is day-first (`DD/MM/YYYY`), matching the selected project
  convention, but users can change it before each upload.
- PDF conversion is run separately, for example:

  ```bash
  python -m dashboard.data.pdf_converter source.pdf converted.csv --date-convention day-first
  ```

- The converted file must be reviewed against the source PDF, then uploaded
  through the normal dashboard validation path.

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

- [ ] Decide and document whether missing monthly observations mean zero cases or unknown reporting; update the modeling pipeline accordingly.
- [ ] Add an automated container startup smoke test that imports `app:server` and checks `/healthz`.
- [ ] Plan the migration from Dash `DataTable` to `dash-ag-grid` before the component removal becomes blocking.
- [ ] Reassess browser session storage if uploaded datasets or cached model results grow beyond the current small-client use case.
- [ ] Consider server-side per-session state with expiry and access controls for larger deployments.
- [ ] Review Gunicorn recycling and graceful-shutdown settings using production memory and runtime measurements.
- [ ] Continue monthly dependency updates through Dependabot and run `pip-audit -r requirements.txt` before releases.
- [ ] Add fixture PDFs from the actual surveillance source once redistribution approval is confirmed; use them for end-to-end extraction regression tests.

## Entry template

Copy this template into `Unreleased` for future work:

```markdown
### YYYY-MM-DD - Short change title

- **Change:** What changed and why.
- **Scope:** Files, deployment settings, or user-visible behavior affected.
- **Validation:** Tests, scans, or manual checks run.
- **Follow-up:** Any remaining risk or next action.
```
