# Independent reconciliation matrices

Audit date: 2026-09-27. Manuscript paragraph IDs refer to the direct DOCX extraction in `reconciliation/manuscript_extracted.txt`; originals and source hash are retained in `reconciliation/manuscript_extracted.json`. All eight diagrams were visually reviewed. Application references below identify the **preserved initial working-tree behavior**, not the last Git commit. Initial code is recoverable from `reconciliation/baseline.zip`. This prevents concurrent revisions from being mistaken for original behavior. For final implemented behavior, test evidence, and resolution status, use `CHATGPT_RETURN_HANDOFF.md` and the single `DECISION_LEDGER.md`. Proposed wording is in `MANUSCRIPT_REVISION_PROPOSALS.md`. A proposal does not resolve an implementation finding.

## A. Manuscript → Implementation

| ID | Manuscript requirement | Actual implementation at audit baseline | Evidence | Discrepancy | Required action |
|---|---|---|---|---|---|
| A01 | School-aged cases, P0046 | Data schema uses date/disease/cases; original reports are all-age | P0046; data/validation.py; source workbook/PDF audit | Target-population evidence unavailable | Preserve separate all-age evaluation; await eligible 5–19 extract; M02/M06/M44 |
| A02 | Public-school setting, title and glossary P0248 | City-wide aggregation, no enrollment or school field | modeling/series_utils.py::get_disease_series; P0051 | Cannot infer school attendance or transmission location | Clarify intended public-school preparedness benefit; M01/M25 |
| A03 | Five distinct models, P0046 | One pipeline per selected disease; software permits arbitrary labels | callbacks/view_callbacks.py::_get_or_compute_disease; data/validation.py::_normalize_disease_names | Five contradicts three initial categories; generalized software is not research scope | M06; final disease set awaits CHO |
| A04 | Hybrid primary, P0033/P0124 | Conditional selection based on rolling WAPE gain >=1 pp; base-only can win | baseline modeling/pipeline.py:135; config.py:54 | Conflicts with approved mandatory architecture; Figure 8 also contradicts prose | Implement mandatory hybrid and explicit failure states; M12/M37 |
| A05 | Disease-specific ADF/ACF/PACF/AIC/Ljung–Box identification, P0109–P0114 | Fixed SARIMA(1,1,1)(0,1,1)[12] | baseline modeling/sarima.py:24–55 | Described search not implemented | Implement bounded training-only search and diagnostics; M17/M18 |
| A06 | SARIMA component | SARIMA failure can fall back to Holt–Winters then drift | baseline modeling/sarima.py::run_arima | Different family cannot be called successful SARIMA | Remove hidden family fallback; retry admissible SARIMA candidates and report failure |
| A07 | NNAR residual model, P0124 | Three residual lags, four hidden nodes, training feature scaling and recursion; short residual series returns zeros | baseline modeling/nnar.py:21 | Core structure present; skipped fit may appear hybrid | Keep baseline architecture, explicit NNAR failure and convergence metadata; M19 |
| A08 | Missing data imputation, P0084/P0098 and Figures 1–2 | Missing observed months block forecast; generic series utility can insert zeros if used without guard | baseline pipeline.py::_validate_observation_coverage; series_utils.py:8 | Prose claims unapproved imputation | Keep no-invention contract and update prose/figures; M11/M14/M31 |
| A09 | COVID anomaly identification, P0084/P0098 | Period display labels; no validated anomaly detector or causal classifier | callbacks/view_callbacks.py; charts/figures.py | Display decoration is not anomaly detection | M15/M31; no detector added without design authorization |
| A10 | Decomposition as model input, P0098 | Descriptive decomposition chart; models fit original counts then residuals | callbacks/view_callbacks.py::_build_decomposition_chart; pipeline.py::_run_backtest_leg | Two different notions of residual conflated | M15/M22; clarify data flow |
| A11 | RMSE/MAE/MAPE and <32.22 target, P0084 | Live four metrics incl. WAPE; historical reference is fixed config | modeling/metrics.py::compute_metrics; config.py:52; publisher Table 1 | External SARIMA number is not a standard | M14/M30/M40; cite verified source and remove acceptance claim |
| A12 | Confidence intervals, Figures 1–2 | Historical maximum absolute-error envelope | baseline pipeline.py::_historical_error_band:102 | No hybrid coverage calibration supporting 95% | M32/M42; retain honest terminology |
| A13 | Three data/model databases, P0100 | Browser session stores data and result arrays; transient fitted models | ui/layout.py::build_layout:264; modeling/serialization.py | No persistent trained-model storage or database | M16/M33 |
| A14 | Resource mobilization and reduced exposure, P0026/P0043 | Forecast visualizations and export only | callbacks/view_callbacks.py::_build_forecast_export; layout.py | No allocation optimization, dispatch, causal or outcome validation | M04; describe intended decision support |
| A15 | Python3.11 prose;3.14.7 IPO | Runtime3.13.3; project minimum3.12 | direct python --version; pyproject.toml:5; Figure1 image7.png | Three inconsistent environments | M07/M29; record exact installed versions in test report |
| A16 | Train/test choice diagram Figure8 | Prior code has earlier folds plus final holdout; diagram suggests winner chosen on test | pipeline.py::run_hybrid_pipeline; image6.png | Figure omits leakage barriers and approved architecture | M37/M38/M39 |
| A17 | Combined real/mock store Figure7 | Baseline uploaded data already authoritative, no supplementation | data/combine.py::prepare_uploaded_data; image8.png | Figure reflects superseded unsafe behavior | M36, replace diagram branch |
| A18 | Six reportable diseases P0234;2015–2025 P0218 | Initial three real categories, seven demo categories; historical2016–2025 | config.py; source workbook | Glossary contradicts research period and scope | M21/M24; never equate demo catalog with thesis categories |
| A19 | School-level outbreak alerts P0238 | Input/model warnings and forecast plots | callbacks/view_callbacks.py::_hybrid_error_response | No alert threshold, notification or school observations | M23 |
| A20 | Security excluded P0052 but evaluated P0085 | No completed expert security/usability evidence | P0052/P0085; supplied artifacts | Internally inconsistent evaluation scope | M10; adviser selects protocol/edition; do not manufacture ratings |

## B. Implementation → Manuscript

| ID | Implemented behavior at audit baseline | Manuscript coverage | Evidence | Impact | Required action |
|---|---|---|---|---|---|
| B01 | Seven deterministic synthetic diseases on first load/reset | Mock-data diagrams exist but imply supplementation | data/mock_data.py; config.py; Fig7 | Demo performance could be mistaken for empirical research | Separate labels/results; M36/M44 |
| B02 | Explicit complete disease-catalog confirmation before activation | Figure5 skips confirmation | callbacks/data_callbacks.py::transition_data_session; tests/test_callbacks.py | User-visible workflow omitted | M35; preserve regression coverage |
| B03 | CSV/XLSX arbitrary-label uploads with date conventions | Scope describes only three categories | data/date_parser.py::normalize_surveillance_table; validation.py | Software capability broader than approved research | Explain distinction; do not whitelist or expand scope |
| B04 | Text-PDF conversion offline; direct browser PDF upload unsupported | No precise ingestion description | data/pdf_converter.py CLI; data_callbacks.py | Reproducibility requires converter report and source review | Add source conversion provenance; DATA_RECONCILIATION.md |
| B05 | Weekly month mapping uses ISO Thursday and special week53 | Calls data monthly P0083 | data/xlsx_parser.py::epi_week_to_month:29 | Mapping unapproved by CHO may shift month counts | M13/M41; retain provisionally |
| B06 | Blank weekly cells skipped, explicit zeros counted | Broad completeness language | data/xlsx_parser.py::_cells_to_records:112 | 120 monthly rows do not prove full weekly reporting | Document missingness audit; no fabricated zero/imputation |
| B07 | Measles-Rubella normalized to Measles | Prose consistently says Measles | baseline config.py worksheet aliases; validation.py::_normalize_disease_names | Source disease definition altered | Preserve combined label; cache/export/test review |
| B08 | Minimum72 consecutive observed months | Not specified | baseline pipeline.py::_validate_observation_coverage and run_hybrid_pipeline | Upload acceptance differs from forecast eligibility | State requirements and explicit insufficient-data outcome |
| B09 | Two expanding earlier folds plus final12-month holdout | Simple train/test diagram only | baseline pipeline.py:135 | Hidden evaluation procedure affects interpretation | M39; retain algorithms' chronological boundary |
| B10 | Earlier-fold WAPE gate chooses model | Prose says final combined forecast | baseline pipeline.py selection_threshold; Fig8 | Approved research and implementation conflict | Mandatory hybrid correction; keep benchmarks visible |
| B11 | MAE when WAPE denominator zero for earlier selection | MAPE/RMSE/MAE listed without zero behavior | baseline pipeline.py::_selection_score; metrics.py | Scores not directly comparable if undefined | M40; no historical policy carried into revised selection silently |
| B12 | Live seasonal-naive copies previous year's matching months | No precise benchmark protocol | baseline pipeline.py::_run_backtest_leg | Essential adverse baseline comparison missing | M39/M40/M43; use same periods |
| B13 | WAPE and MAPE denominator coverage fields | WAPE omitted | metrics.py::compute_metrics | Sparse series MAPE can mislead | M40, display coverage |
| B14 | Nonnegative clipping after additive hybrid combination | Combination described without clipping | baseline metrics.py::hybrid_forecast:7 | Changes prediction distribution and error interpretation | M19; preserve raw component metadata where recorded |
| B15 | NNAR settings3 lags/4 ReLU nodes/alpha10/seed42/lbfgs | Generic layer description; diagram has3 hidden nodes | nnar.py:53; config.py:56; Fig4 | Model cannot be reproduced from prose | M19/M34 |
| B16 | Neural forecast recursion uses training-fitted StandardScaler | No detailed scaling or training procedure | nnar.py::run_nnar | Reproducibility and leakage review require exact procedure | M19; document warnings and failures |
| B17 | Lazy per-disease forecasting; session result cache | Diagram speaks of saved model reuse | view_callbacks.py::_get_or_compute_disease/_data_signature; serialization.py | Serialized arrays are not trained estimator persistence | M16/M33; cache invalidation includes changed metadata |
| B18 | Forecast CSV includes component/metric/result metadata | Export under-described | view_callbacks.py::_build_forecast_export:492 | External reviewer needs source/model identity | Extend provenance metadata per author requirements; handoff lists actual fields |
| B19 | Historical bands from earlier forecast errors | Confidence terminology in diagrams | pipeline.py::_historical_error_band | No statistical guarantee follows from band drawing | M32/M42 |
| B20 | Actual historical selected-model performance unfavorable vs naive for2 of3 real categories | Design claims hybrid advantage P0080 | preserved evidence/ and THESIS_READINESS.md | Superiority unsupported; label was historically Measles | M12/M43; preserve old and revised arrays separately |
| B21 | App startup/tests can check callbacks and outputs | ISO expert quality assessment proposed | tests/; app.py; P0085 | Passing tests does not establish usability, clinical or operational utility | Keep software verification separate from unavailable external assessments |

## C. Dataset → Research requirements

| ID | Research requirement | Actual source data | Evidence | Eligibility | Required action |
|---|---|---|---|---|---|
| C01 | Individuals aged5–19 | All-age city aggregates, no eligible extract supplied | Original weekly PDFs; workbook Notes; handoff §6.4 | Not eligible for approved population performance | CHO supplies verified age-specific data; retain all-age separate |
| C02 | Confirmed cases only | Original aggregate classification unverified | Original report fields; P0051 explicitly allows suspected | Unverified, not eligible as confirmed-only | CHO verifies case definition and consistent classification |
| C03 | Public-school preparedness | No enrollment/site-of-infection data | Original city-wide reports; P0051 | Supports general context only | No claim that cases were public-school students or contracted at school |
| C04 | Dengue/Leptospirosis/Measles-Rubella provisional | Three named disease reports and sheets | Workbook sheet names; source PDF titles | Provisional category coverage | Final set awaits CHO/researcher/adviser; no Top5 pivot |
| C05 | Preserve combined Measles-Rubella | Source combined label; earlier parser shortened it | Original report title; baseline config.py aliases | Combined source category, classification pending | Preserve label in data/cache/export; no measles-only interpretation |
| C06 | Historical2016–2025 | Weekly tables2016–2025 | Direct workbook and PDF audit | Temporally compatible, other criteria unmet | Correct2016–2026 and2015–2025 claims |
| C07 | Monthly forecasts | Original reporting is weekly | Source tables; xlsx_parser.py | Monthly derivation provisional | Retain mapping, obtain CHO calendar confirmation |
| C08 | Valid epidemiological weeks | Week53 behavior requires special treatment | epi_week_to_month; original tables | Calendar approval unresolved | Report ISO Thursday and non-ISO week53 December rule |
| C09 | Complete observations | Blank and zero cells differ; monthly coverage alone insufficient | DATA_RECONCILIATION.md cell/missingness artifacts | Mathematical coverage is not epidemiological completeness | Preserve blanks separately; confirm absent-report meaning |
| C10 | Faithful transcription | Weekly cell/annual/monthly comparison audited independently | DATA_RECONCILIATION.md and reconciliation source outputs | Arithmetic verification only | Preserve source hashes and mismatch records; do not infer completeness |
| C11 | Source total consistency | Dengue2024 printed4,516 vs weekly4,588; workbook follows weekly | Original Dengue PDF and workbook; difference72 | Unresolved source discrepancy | Preserve both; CHO determines correction |
| C12 | Non-synthetic real evaluation | Supplied workbook is separate from seven-disease demo | data/mock_data.py; combine.py; source file identity | All-age technical evaluation only | Never mix, proportionally estimate, or impute age groups |
| C13 | Dataset source identity | Local workbook transcribed from original disease reports | Workbook Notes and file hashes | Source attribution does not itself establish official approval | Keep PDF/workbook provenance and verification status |
| C14 | Live comparison on matched holdouts | Complete series supports2016–2025 chronological windows | preserved evaluation arrays and pipeline windows | Technical comparison feasible | Recompute revised arrays; retain final-holdout exposure caveat |
| C15 | Untouched final holdout | Historical work has already inspected2025 errors | THESIS_READINESS.md and historical evidence | Excluded algorithmically, not unseen to developers | Disclose adaptive-development limitation; prospective validation remains distinct |
| C16 | Forecast horizon operationally useful | Data alone cannot establish1/3/12-month utility | No CHO interview supplied |12-month capability provisional | CHO interview; do not change objective prematurely |
| C17 | Privacy and use authorization | Aggregate files, no supplied ethics/use-approval record | Original manuscript P0051; supplied artifact inventory | Aggregation alone does not establish compliance | Researcher/adviser assess governance; do not fabricate approval |
| C18 | Validated uncertainty | Only empirical historical forecast errors available | pipeline.py::_historical_error_band | No validated95% hybrid coverage | Accurate band naming and prospective coverage assessment if approved |
| C19 | Historical32.22 reference | External nationwide dengue SARIMA testing score, not local data | [Olana2025 Table1](https://onlinelibrary.wiley.com/doi/10.1155/tbed/7480710) | Provenance verified; local threshold validity unsupported | Cite and separate from live benchmarks; no model selection use |
| C20 | Demonstrated operational benefit | No field deployment/outcome or expert evaluation dataset | Supplied sources and manuscript proposal wording | Unavailable evidence | Retain potential-benefit language; CHO acceptance/usability deferred |

## Final-state reconciliation rule

These matrices intentionally retain baseline findings as an audit trail. Do not mark them “resolved” by editing descriptions to the target design. The consolidated handoff must map actual file changes and tests to each corrected behavior. External data eligibility, source calendar, final disease classification, corrected Dengue total, horizon usefulness, and expert acceptance remain unresolved until the corresponding evidence arrives. The separately verified 32.22 source narrows only the provenance question; it does not validate the manuscript's claimed standard.

## Current feature coverage after reconciliation

| Feature | Exact source reference | Actual status and verification |
|---|---|---|
| Application and config | `app.py:39` | Implemented; Flask routes and callback wiring verified; deployment unverified |
| Shared app instance | `dashboard/app_instance.py:19` | Implemented; upload limit and413 regression verified |
| Layout and components | `dashboard/ui/layout.py:265` | Implemented; component contracts verified; browser visual review pending |
| Reusable components | `dashboard/ui/components.py:9` | Implemented; metric cards rendered as component trees |
| Upload/catalog confirmation | `dashboard/callbacks/data_callbacks.py:227` | Implemented; replacement requires explicit catalog confirmation; tests cover reset/refresh/replacement |
| Forecast callbacks/cache/export | `dashboard/callbacks/view_callbacks.py:682` | Implemented; mandatory primary, metadata, diagnostics, failure panels and CSV verified structurally |
| Plots | `dashboard/charts/figures.py:37` | Implemented; plot trace bindings verified for3 real results; browser rendering unverified |
| Dates and aggregation | `dashboard/data/date_parser.py:138` | Implemented; invalid dates/counts/duplicate weeks rejected and metadata retained |
| Weekly workbook parser | `dashboard/data/xlsx_parser.py:138` | Implemented;1590 source cells and360 monthly values checked; calendar provisional |
| Input validation | `dashboard/data/validation.py:102` | Implemented; invalid inputs rejected rather than clipping/rounding counts |
| Population boundaries | `dashboard/data/provenance.py:4` | Implemented; mixed category rejection tested; metadata not certified |
| Dataset preparation | `dashboard/data/combine.py:5` | Implemented; no sample supplementation |
| Synthetic demonstration | `dashboard/data/mock_data.py:18` | Implemented; separate deterministic120-month demonstration, not empirical evidence |
| Offline generic PDF converter | `dashboard/data/pdf_converter.py:181` | Partial; helper tests pass but automatic extraction of complex original Measles/Dengue tables is incomplete; independent source-specific audit script succeeds |
| Series helpers | `dashboard/modeling/series_utils.py:8` | Implemented; zero-fill helper is guarded by pipeline completeness checks before forecasting; aggregate display is not proof of completeness |
| Forecast pipeline | `dashboard/modeling/pipeline.py:177` | Implemented; mandatory hybrid, isolated search windows, independent benchmarks and failures tested |
| SARIMA identification | `dashboard/modeling/sarima.py:32` | Implemented;12 candidates/window, selected orders, ADF/correlations/AIC/root/residual diagnostics; exact protocol awaits adviser acceptance |
| NNAR | `dashboard/modeling/nnar.py:22` | Implemented;3 lags/4 units/lbfgs/seed42/alpha10; recursion, convergence warnings and explicit insufficiency |
| Metrics and combination | `dashboard/modeling/metrics.py:18` | Implemented; independent arrays verify calculations, aligned components, zero handling |
| Serialization | `dashboard/modeling/serialization.py:36` | Implemented; optional legacy fields, current metadata/arrays verified |
| Source PDF audit | `reconciliation/source_reconcile.py:26` | Implemented source-specific comparison; not generalized production extraction |
| Manuscript revisions | `MANUSCRIPT_REVISION_PROPOSALS.md:14` | Proposed only;44 wording/diagram proposals, original unmodified |
| Medical resource allocation / dispatch | `dashboard/ui/layout.py:265` | Not implemented; no outcome or clinical-validation evidence |
