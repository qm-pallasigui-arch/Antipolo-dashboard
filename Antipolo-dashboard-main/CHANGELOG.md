# Revision 39 — 2026-10-02

- Replaced the normal JSON-based workflow with guided upload, automatic source preparation, a before/after review popup, Confirm & Use Data, cancellation and inspectable transformation history.
- Restored deterministic CSV alias and multi-sheet XLSX recognition, including disease-name worksheets and morbidity-week rows across year columns, without monthly aggregation.
- Added explicit column-mapping fallback, source conflicts, retained blanks/zeros/week 53, and transformation provenance in detailed exports.
- Renamed navigation to Data and About the Model, added historical range controls, and collapsed technical diagnostics. Model/study settings are administrator-maintained; missing source facts use ordinary optional controls.
- Added real Edge browser interaction and responsive screenshot review, plus transformation regression tests. See REVISION39_REPORT.md for evidence and approval-dependent limitations.

# Weekly redesign — 2026-10-01

- Switched operational app entrypoint to the five-section weekly workflow; preserved legacy modules and evidence.
- Added canonical four-column CSV/XLSX validation, explicit gaps/zeros/week 53, reporting completeness, provenance, eligibility, and Confirm & Activate.
- Added configurable weekly SARIMA–NNAR, separate SARIMA-only, 52-point paths, explicit failure handling, chronological evaluation and context-isolated cache keys.
- Added weekly charts, source-date display summaries, cautious interpretation, MAE/WAPE emphasis, four technical metrics and accurately labeled provisional error ranges.
- Added provenance exports and append-only prospective snapshot/reconciliation support, without claiming completed validation.
- Added weekly integrity tests and current documentation. Statistical protocol defaults remain pending; no adviser-dependent methodology is invented.

The entries below describe historical versions and are retained as evidence.

# Research reconciliation - 27 September 2026

- Mandatory SARIMA+NNAR primary, disease/window-specific bounded identification, explicit failures and benchmark preservation.
- Provisional Measles-Rubella label, separate population/source metadata, strict invalid-input rejection and known incomplete-week blocking.
- Candidate/NNAR diagnostics, provenance-bearing CSV, source reconciliation, manuscript proposals and reproducible before/after evaluation.
- Initial working tree and all historical evidence preserved in reconciliation/baseline.zip. See CHATGPT_RETURN_HANDOFF.md and TEST_RESULTS.md for verified scope and remaining dependencies.

The entries below describe historical implementations and remain unchanged as evidence.

<!-- @format -->

# Change Log

This file records production-readiness changes for the Antipolo disease-surveillance dashboard. Add future entries under `Unreleased` before moving them into a dated release section.

## Unreleased

### 2026-09-26 - User-confirmed catalog and two distinct references

- Restored the fixed historical reference alongside neutral, live seasonal-naive
  holdout metrics in forecast cards and Technical model details. This supersedes
  the earlier entries that describe seasonal naive as hidden/internal-only.
- Upload summary now shows the full validated catalog before an explicit
  **Use these N diseases** action activates it. Pending/rejected uploads preserve
  active data; reset clears pending data and refresh discards unconfirmed data.
- Modeling and sample-generation code and the 1.00-point default are unchanged.
- Current investigation, threshold sensitivity, fresh verification, and the single
  remaining-decision ledger are in [THESIS_READINESS.md](docs/archive/THESIS_READINESS.md).


### 2026-09-24 - Forecast-panel audit remediation

#### Why these corrections were necessary

- A fresh arithmetic and presentation audit confirmed that the selected arrays,
  holdout metrics, chart traces, and CSV values were internally consistent, but
  several reader-facing statements claimed more than the evaluation established.
- The README promised that auto-selection made the shipped forecast "never worse
  than SARIMA alone." Rolling-fold selection cannot guarantee performance on the
  untouched holdout or unknown future months. In the built-in sample, several
  small rolling-WAPE Hybrid wins reversed on the final holdout.
- The chart called its shaded region an empirical 95% interval even though 36
  pooled historical errors make the implemented 95% finite-sample quantile the
  single largest observed absolute error. The band has not demonstrated 95%
  prospective coverage and is not horizon-specific.
- Backtest and production fits can use different fallback tiers. Static SARIMA
  labels could therefore describe a Holt-Winters or naive-drift result as if it
  were produced by SARIMA.
- When every selection-fold actual is zero, WAPE is undefined and the pipeline
  correctly falls back to MAE, but the panel previously continued to say
  "rolling WAPE — N/A vs N/A."

#### Modeling and selection changes

- Added `HYBRID_MIN_WAPE_GAIN_PP = 1.0`. Hybrid is selected only when its
  aggregate rolling-selection WAPE is at least 1.00 percentage point below the
  base-only candidate. Otherwise the simpler base-only candidate wins. This
  avoids changing model complexity for numerically tiny sample advantages.
- Stored the actual selection criterion and threshold in each result. All-zero
  selection windows record MAE as the criterion, with a strict lower-MAE rule
  and no percentage-point threshold.
- Stored the base-model tier from both selection folds and the untouched
  holdout, in addition to the production tier. This exposes cases where a
  shorter historical leg fell back even though the full production refit later
  succeeded with SARIMA.
- Added exact date-index checks before scoring. Equal-length actual and forecast
  arrays with shifted months are now rejected instead of being scored by
  position.
- Preserved seasonal naive strictly as an internal diagnostic benchmark. It was
  not added to the selectable or reader-facing thesis models, following the
  established SARIMA-only versus SARIMA + NNAR scope.

#### Panel, chart, and export corrections

- Replaced the inaccurate 95% interval claim with **historical maximum-error
  band** everywhere reader-facing. Its method text explicitly says future
  coverage is not validated. CSV fields are now `lower_error_band` and
  `upper_error_band`, rather than `lower_95` and `upper_95`.
- Forecast, backtest, and residual legends now derive their base-model names
  from the actual production or holdout tier. Backtest styling follows the
  selected model rather than always emphasizing Hybrid.
- The Selected model card names the real production fallback when base-only is
  selected, reports the actual rolling criterion, states the 1.00-point Hybrid
  threshold, and identifies the production and holdout base tiers.
- Exported `production_base_tier`, `holdout_base_tier`,
  `selection_base_tiers`, `selection_metric`, and `selection_threshold` so the
  downloaded evidence retains the same methodological context as the panel.
- Restricted the COVID annotation to the built-in synthetic dataset and
  relabeled it as a synthetic-data reduction. Arbitrary uploads no longer
  receive an unsupported event annotation.
- Replaced "clean SARIMA + NNAR fit" with the bounded statement that no runtime
  or model-fit warnings were captured. Successful SARIMA fits now retain other
  emitted warning categories instead of silently dropping them.
- Corrected the visible methodology text: two earlier rolling-origin folds
  select the candidate, and a separate final 12-month window evaluates it.
  Corrected the README by removing the impossible "never worse" guarantee.
- Incremented the forecast cache schema to `model-audit-v5`, preventing browser
  sessions from reusing results created under the previous labels and selection
  rule.

#### Verification

- Added regressions for shifted forecast dates, the 1.00-point selection rule,
  serialized tier/criterion metadata, honest historical-band labels, fallback-
  aware chart legends, selection-aware backtest styling, all-zero MAE copy,
  suppression of synthetic annotations on real uploads, and the expanded CSV
  contract.
- Independently recomputed the selected holdout metrics and confirmed that the
  final forecast equals the selected production candidate and remains enclosed
  by the historical error band.
- Full suite: `75 passed`. Remaining warnings are the existing Dash DataTable
  deprecation notice and the environment's pytest-cache permission warning.

### 2026-09-24 - Forecast correctness audit and evaluation redesign

#### Defects reproduced before the change

- **Missing months were silently modeled as zero:** A two-row disease series
  containing only January 2016 and December 2025 expanded to 120 model months
  with 118 inserted zeros, passed the old 48-month span check, and produced
  apparently valid RMSE/MAE/MAPE. This demonstrated that calendar span was
  being mistaken for observed history.
- **MAPE was mislabeled for zero actuals:** The old implementation replaced a
  zero actual denominator with `1`. For actual `[0, 5, 10]` and predicted
  `[2, 5, 8]`, it reported 73.33% rather than a defined nonzero-month MAPE of
  10%. The result was finite but was not ordinary MAPE.
- **Selection used rounded values:** Metrics were rounded to two decimals
  before model selection. In the representative PDF's Pediculosis series, raw
  hybrid and SARIMA MAPEs of 96.0369588664% and 96.0381196660% both became
  96.04%, incorrectly turning a strict hybrid win into a SARIMA tie-break.
- **“Final” metrics reused the selection window:** The same last 12 months both
  chose the candidate and supplied `final_metrics`, creating selection optimism
  and making the cards sound like future accuracy estimates.
- **Intervals did not match the selected forecast:** Hybrid point forecasts
  were paired with unchanged SARIMA intervals. Several synthetic sample series
  also exported negative lower bounds for non-negative case counts.
- **Forecast lines duplicated the winner:** `final_forecast` is intentionally
  the selected candidate array, but the chart drew SARIMA, hybrid, and final as
  three lines. The final line therefore covered one candidate exactly and made
  the plot look frozen or incorrectly duplicated.

#### Corrected modeling contract

- **Complete observations required:** Forecasting now rejects a disease if any
  calendar month inside its observed range lacks an explicit row. Missing is
  treated as unknown reporting, never silently as zero. Explicit zero-case
  rows remain valid observations. The forecast panel preserves and displays
  the bounded rejection reason instead of replacing it with a generic failure.
- **72-month minimum:** The default requirement is now 36 initial training
  months, two expanding 12-month rolling-origin selection folds, and one
  separate 12-month final holdout: 72 complete observed months in total.
- **Unrounded, documented metrics:** RMSE, MAE, MAPE, and WAPE remain full
  precision inside the pipeline and are rounded only in the UI. MAPE excludes
  zero-actual months and exposes `mape_n` and total `n`; WAPE is the primary
  selection score and falls back to MAE only for an all-zero evaluation window.
- **Independent holdout:** Candidate selection uses the two rolling folds. The
  selected candidate is then evaluated on an untouched last-12-month window.
  Metrics are explicitly labeled **Holdout RMSE**, **Holdout MAE**, **Holdout
  MAPE**, and **Holdout WAPE**; they do not claim unknown future accuracy. The
  later UI simplification keeps WAPE as the sole headline and moves the other
  three into expandable diagnostics.
- **Live diagnostic benchmark:** Seasonal naive is calculated on the untouched
  holdout to replace the fixed, unproven 32.22% MAPE reference. It is not a
  selectable production model: the thesis decision remains strictly between
  SARIMA-only and SARIMA + NNAR. It is also omitted from reader-facing model
  cards and charts, remaining internal diagnostic evidence only.
- **Selected-model uncertainty:** The production interval is centered on the
  selected forecast and calibrated from 36 historical rolling/holdout absolute
  errors using a finite-sample 95% empirical quantile. Lower bounds are clipped
  at zero. This is materially more truthful than attaching SARIMA uncertainty
  to a hybrid mean, while prospective real-data coverage validation remains a
  documented limitation.
- **Cache schema invalidation:** The dataset signature now includes a modeling
  schema version, automatically discarding browser-cached results generated by
  the pre-audit metric and interval definitions.
- **Actionable warning panel:** Generic sklearn/SciPy deprecation notices are
  no longer presented as model-quality warnings; convergence and other fit
  warnings remain visible and logged.

#### Forecast-chart audit and correction

- The chart now draws the selected forecast exactly once as a solid orange
  line. The other thesis candidate is the sole dotted alternative and is not a
  duplicate of `final_forecast`. Seasonal naive is not plotted.
- Added an **NNAR forecast adjustment** card showing the mean and maximum
  absolute difference between SARIMA and hybrid. When those two candidates
  still look alike, the dashboard now quantifies that the learned residual
  correction is genuinely near zero rather than implying a rendering failure.
- The forecast subtitle and interval legend now describe the selected-model
  empirical interval. Seasonal naive remains a numeric holdout benchmark only.
- Regression coverage verifies the exact plotted arrays and legend identities,
  selected-series equality, non-negative/enclosing intervals, rolling WAPE
  selection, untouched-holdout metric routing, zero-safe MAPE/WAPE, missing-
  month rejection, and serialization of the expanded result schema.
  Full suite: `72 passed`.

#### Metric-card simplification

- Reduced the headline row to exactly three integrity/decision signals: **Data
  source**, **Selected model**, and one accuracy measure, **Holdout WAPE**.
- Chose WAPE rather than MAPE for the headline because near-zero disease counts
  make MAPE unstable; WAPE is also the unrounded model-selection criterion.
- Preserved both rolling selection scores in the pipeline and condensed their
  rounded values into the **Selected model** card, for example `rolling WAPE —
  SARIMA 57.53% vs Hybrid 57.65%`.
- Moved holdout RMSE, MAE, MAPE with nonzero-denominator coverage, and the NNAR
  adjustment magnitude into a collapsed **Show more diagnostics** panel.
- Removed the standalone Forecast Interval card. The selected-model empirical
  interval remains visible as the shaded chart band and documented in exports,
  avoiding duplicate headline information.

#### Representative PDF consequence

- All seven extracted PDF disease categories remain valid upload labels, but
  all seven are now correctly blocked from forecasting: five have 24–48
  missing months inside their observed ranges, and the two complete series have
  only 36 or 48 months—below the new 72-month evaluation minimum. No accuracy
  metric is produced from the censored top-five report.

### 2026-09-24 - Upload-defined disease catalogs and session reset

- **Removed the upload whitelist:** The original seven disease names now seed
  only the synthetic sample shown on first load. CSV, flat XLSX, converted PDF,
  and PIDSR-style weekly XLSX data may contain any nonblank disease label up to
  200 characters. Unknown names are no longer discarded.
- **Authoritative uploads:** A successful upload replaces the complete active
  disease catalog for that browser session. The application no longer
  backfills absent sample diseases with mock rows, so uploaded and generated
  records cannot be mistaken for one combined surveillance dataset.
- **Dynamic dashboard:** Overview and forecast selectors, upload coverage,
  stacked bars, disease-share charts, data tables, and the reporting-year
  slider now derive their values from the active upload. Arbitrary labels such
  as Malaria or a newly monitored syndrome remain visible and forecastable when
  sufficient monthly history is available.
- **Generalized PIDSR workbooks:** Every worksheet containing a valid
  `Morbidity Week` matrix is imported, with the worksheet name used as the
  disease label. Existing aliases such as `Measles-Rubella` remain supported,
  but they are optional normalization rules rather than a sheet whitelist.
- **Explicit session reset:** Added **Reset to sample data** beside the upload
  control. It erases the active upload from browser session state and restores
  the seven-series synthetic sample. Ordinary refreshes continue to preserve
  the active session data.
- **Visible rejection:** Blank, missing, or over-200-character disease names
  are rejected with counts in the upload status and persistent Upload Summary.
  If no valid rows remain, the upload fails visibly and the prior session data
  remains active.
- **PDF compatibility:** Re-ran the supplied representative PDF after removing
  the whitelist. All 480 extracted rows across seven ICD-10 categories are now
  dashboard-compatible. `dashboard_ready` remains `false` for the independent
  scientific blockers: age-restricted scope, top-five-only scope, and the 2023
  printed-total discrepancy.
- **Regression coverage:** Added tests for arbitrary disease acceptance,
  visible invalid-label rejection, authoritative upload replacement, dynamic
  selectors/year bounds, generalized worksheets, and manual session reset.
  Full suite: `68 passed`.

### 2026-09-24 - Representative DOH PDF extraction validation

- **Fixture exercised:** Ran the offline converter against the supplied
  two-page DOH Regional Office IV-A report, “Top 5 Leading Infectious Diseases
  among School-Aged Children Aged 5–19 Years in Antipolo City, Rizal,
  2016–2025.” The source PDF remains a local, untracked input rather than being
  added to the repository.
- **Parser extension:** Added support for wide year-by-month PDF matrices where
  five disease records and their monthly values are merged into multiline
  cells. Year context now survives page breaks, which is required because the
  PDF places the 2023 year marker on page 1 and its records on page 2.
- **Extraction result:** Extracted 480 monthly rows covering eight reported
  years and seven ICD-10 disease categories. The source explicitly has no
  reports for 2020 and 2022.
- **Faithful conversion:** The canonical CSV/XLSX preserves every extracted
  disease category. With upload-defined disease catalogs, all seven extracted
  ICD-10 categories and all 480 rows are accepted by the dashboard.
- **Scope safeguards:** The audit report detects that this is an age-restricted
  5–19 population and a top-five-per-year ranking. Because missing categories
  do not mean zero cases, the report sets `dashboard_ready` to `false` and
  includes these issues in `dashboard_blockers`.
- **Source discrepancy found:** Visual review confirmed that the PDF's 2023
  Intestinal Infectious Diseases monthly values sum to 287 while its printed
  annual total is 274. The converter reports this mismatch and treats it as an
  additional dashboard blocker rather than changing either value silently.
- **Provenance:** The report records the source document's Field Health Services
  Information System Database attribution and its missing-year note.
- **Artifacts:** Generated `sample-pdf-converted.csv` and
  `sample-pdf-converted.csv.report.json` for review. These outputs are local and
  untracked.
- **Validation:** Added regression coverage for multiline month matrices,
  cross-page year context, scope detection, source-note extraction, and
  dashboard-readiness reporting. The later upload-catalog change supersedes the
  original whitelist behavior: the generated CSV now retains all seven
  extracted categories with no mock backfill.

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
  months, and runs the normal disease-label and numeric/range validation chain.
- Output can be canonical CSV or XLSX with `year`, `month`, `disease`, and
  `cases` columns.
- The converter preserves every extracted disease category in that canonical
  output. Its report lists the rows and disease labels that pass the same open
  dashboard validation used for uploads.
- Every conversion also writes `<output>.report.json` with page/table counts,
  rejected-table reasons, parsing and validation notes, coverage, diseases,
  and an explicit manual-review requirement.
- The report includes a `dashboard_ready` decision and concrete blockers.
  Scope mismatches, annual-total discrepancies, or zero compatible tracked rows
  prevent a conversion from being described as dashboard-ready even though the
  faithful canonical CSV/XLSX is still produced for inspection.
- Added support for DOH year-by-month matrices whose top-five disease records
  are visually merged into multiline PDF cells, including year groups split
  across page boundaries and checks against the printed annual totals.
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
- **Scope:** Added the `store-upload-summary` session store; extended the upload callback to persist structured metadata and preserve or regenerate it safely after a refresh; rendered the summary with the dashboard's existing warning-panel and DataTable patterns. The later upload-defined catalog change removed mock backfill from successful uploads.
- **Data quality:** Added an independent month-gap check for real disease data. It reports entirely absent months between the first and last observation while correctly treating explicit zero-case rows as present; duplicate-row warnings remain a separate validation check.
- **Validation:** Added regression coverage for summary keys and per-disease counts, zero-case-versus-missing-month behavior, refresh persistence, callback wiring, and failed-upload summaries. Full suite: `42 passed` with `pytest tests/ -v`.
- **Follow-up resolved:** Disease coverage now follows the active uploaded catalog; the seven configured names are sample data only.

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

- [ ] Add an automated container startup smoke test that imports `app:server` and checks `/healthz`.
- [ ] Plan the migration from Dash `DataTable` to `dash-ag-grid` before the component removal becomes blocking.
- [ ] Reassess browser session storage if uploaded datasets or cached model results grow beyond the current small-client use case.
- [ ] Consider server-side per-session state with expiry and access controls for larger deployments.
- [ ] Review Gunicorn recycling and graceful-shutdown settings using production memory and runtime measurements.
- [ ] Continue monthly dependency updates through Dependabot and run `pip-audit -r requirements.txt` before releases.
- [ ] Add fixture PDFs from the actual surveillance source once redistribution approval is confirmed; use them for end-to-end extraction regression tests.
- [ ] Develop and prospectively validate a horizon-specific probabilistic interval on representative complete real surveillance series. The current historical maximum-error band deliberately makes no 95% future-coverage claim.

## Entry template

Copy this template into `Unreleased` for future work:

```markdown
### YYYY-MM-DD - Short change title

- **Change:** What changed and why.
- **Scope:** Files, deployment settings, or user-visible behavior affected.
- **Validation:** Tests, scans, or manual checks run.
- **Follow-up:** Any remaining risk or next action.
```


## 2026-10-03 ? Revision 45 exploratory weekly protocol

Installed the explicitly authorized exploratory 16-candidate SARIMA/NNAR configuration, horizon-specific holdout metrics, candidate convergence records, source-backed completeness/calendar declarations, and individual audited blank-count resolutions. Preserved weekly semantics, source evidence, synthetic isolation, and final-methodology boundaries. Reconciliation: REVISION45_REPORT.md.
