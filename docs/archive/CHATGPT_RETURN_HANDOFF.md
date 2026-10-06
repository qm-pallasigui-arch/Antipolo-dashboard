# Antipolo thesis and dashboard: coding-agent return handoff

Completed technical reconciliation on 27 September 2026. Assessment: **Needs revision for research claims; implemented technical corrections verified within the stated software scope.** Research/data acceptance remains partial. The original manuscript and surveillance files are unchanged.

## 20.1 Executive summary

Inspected the current uncommitted repository, all application/model/data/callback modules and tests, deployment/dependency manifests, historical evidence, original workbook, all three original disease PDFs, and the manuscript including tables and eight diagrams. Baseline recovery and hashes preceded edits. The current source was checked directly rather than accepting previous handoff assertions.

Implemented mandatory SARIMA+NNAR primary forecasting, bounded disease/window-specific SARIMA identification, typed component failures/retries, preserved independent benchmarks, corrected provisional Measles-Rubella labels, source/population/classification metadata, rejection of invalid/mixed/incomplete inputs, updated tests and documentation. General disease-label uploads and explicit catalog confirmation remain. No disease-scope expansion, age estimation, source-value correction, original-manuscript edit, dependency installation, commit, deployment or external message was made.

Verified 112 tests, independent source arithmetic and 20 before/after series evaluations. The revised all-age hybrid WAPE is 34.86% Dengue, 58.63% Leptospirosis, 576.65% Measles-Rubella. Adverse results remain visible. Source transcription agrees, but eligibility/completeness/confirmed-only claims are unsupported. Browser visual rendering and clean pinned/container deployment remain unverified. No eligible ages5-19 extract, CHO interview/acceptance or expert usability results were supplied.

Entry-point companions: AUDIT_MATRIX.md, DATA_RECONCILIATION.md, MODEL_EVALUATION.md, TEST_RESULTS.md, MANUSCRIPT_REVISION_PROPOSALS.md and the single DECISION_LEDGER.md. Historical THESIS_READINESS.md, AGENT_HANDOFF.md and evidence/ were preserved unchanged.

## 20.2 Preserved author decisions

1. **Population:** individuals aged 5-19, city-wide Antipolo surveillance intended to inform public-school preparedness. Cases are not assumed contracted at school or enrolled in public schools. The age range was not changed.
2. **Separation:** retain all-age evaluation separately; evaluate eligible 5-19 records independently when supplied. All-age results do not establish target-population performance. No populations or synthetic/real results were pooled.
3. **Case classification:** final analytical dataset must be confirmed-only. Existing report totals remain unverified for classification; no confirmed-only label was inferred.
4. **Disease coverage:** initial Dengue, Leptospirosis and provisionally combined Measles-Rubella. Final scope/classification awaits researcher/adviser/epidemiologist/CHO. No Top 5 pivot; generalized upload capability is separate from thesis scope.
5. **Architecture:** primary prediction is SARIMA forecast plus NNAR residual forecast. SARIMA-only and seasonal naive are benchmarks, never performance-based replacements. Alternative valid SARIMA configurations are tried after neural failure; no Holt-Winters/drift/base-only or fabricated zero correction is called hybrid. Failure remains explicit.
6. **Identification:** disease-specific ADF assessment, ACF/PACF evidence, candidate SARIMA fitting, AIC and residual diagnostics. Search occurs inside each training window; final holdout values do not select parameters.
7. **Horizon:**12-month capability retained provisionally pending 1/3/12-month operational interview. Thesis objective was not changed.
8. **Transparency:** disclose all benchmark comparisons, including worse hybrid results; retain final holdout outside search and do not claim general superiority. Prior human exposure to 2025 is explicitly disclosed.
9. **Week conversion:** retain existing ISO-Thursday/non-ISO-week53-December conversion provisionally; obtain official CHO calendar confirmation.
10. **Source discrepancy:** preserve Dengue 2024 printed 4516 and weekly/workbook 4588, difference 72. No choice of corrected value was fabricated.

**Agent implementation choices, not separately approved research protocol:**12-candidate bounds; ADF p=.05; D0/1 comparison; trend=c; common burn 13; root tolerance 1.000001; maxiter 300; lag 12 Ljung-Box warning; strict invalid-row rejection; preserving finite NNAR forecasts with convergence warnings. The neural architecture itself is unchanged. Adviser acceptance of these exact technical choices remains D17.

## 20.3 Repository state

- Branch: `Backend-fixes`; relevant HEAD: `46f186d353357f86c8104716c8c99a746a9486ce`. No new commit.
- Initial Git status is below; these modifications and untracked files predated this assignment. The baseline is the working tree, not HEAD.
```text
M ARCHITECTURE.md
 M CHANGELOG.md
 M README.md
 M dashboard/callbacks/data_callbacks.py
 M dashboard/callbacks/view_callbacks.py
 M dashboard/charts/figures.py
 M dashboard/config.py
 M dashboard/data/combine.py
 M dashboard/data/mock_data.py
 M dashboard/data/pdf_converter.py
 M dashboard/data/validation.py
 M dashboard/data/xlsx_parser.py
 M dashboard/modeling/metrics.py
 M dashboard/modeling/nnar.py
 M dashboard/modeling/pipeline.py
 M dashboard/modeling/sarima.py
 M dashboard/modeling/serialization.py
 M dashboard/modeling/series_utils.py
 M dashboard/ui/layout.py
 M tests/__init__.py
 M tests/test_app_contracts.py
 M tests/test_callbacks.py
 M tests/test_data_ingestion.py
 M tests/test_date_preprocessing.py
 M tests/test_modeling.py
?? "#DOH-202600000699_Top 5 Leading Infectious Diseases in Antipolo City by Month, 2016-2025.pdf"
?? AGENT_HANDOFF.md
?? THESIS_READINESS.md
?? evidence/
?? sample-pdf-converted.csv
?? sample-pdf-converted.csv.report.json
?? tests/test_upload_confirmation.py
```

- Recovery: reconciliation/baseline.zip contains 67 initial files, including all historical untracked evidence; baseline-hashes.json records SHA256. initial-working-tree.patch preserves the initial tracked diff. repository-history.bundle preserves local branch/tag/HEAD history; final working-tree files are in the updated ZIP.
- Deleted initial files: none. Authoritative original manuscript/workbook/PDFs are also bundled byte-for-byte in reconciliation/sources/. Their hashes were compared with external originals.
- Final Git status follows (also retained in reconciliation/final-git-status.txt). Existing uncommitted changes were not reset, cleaned, committed, or discarded.

```text
M ARCHITECTURE.md
 M CHANGELOG.md
 M README.md
 M dashboard/callbacks/data_callbacks.py
 M dashboard/callbacks/view_callbacks.py
 M dashboard/charts/figures.py
 M dashboard/config.py
 M dashboard/data/combine.py
 M dashboard/data/date_parser.py
 M dashboard/data/mock_data.py
 M dashboard/data/pdf_converter.py
 M dashboard/data/validation.py
 M dashboard/data/xlsx_parser.py
 M dashboard/modeling/metrics.py
 M dashboard/modeling/nnar.py
 M dashboard/modeling/pipeline.py
 M dashboard/modeling/sarima.py
 M dashboard/modeling/serialization.py
 M dashboard/modeling/series_utils.py
 M dashboard/ui/layout.py
 M tests/__init__.py
 M tests/test_app_contracts.py
 M tests/test_callbacks.py
 M tests/test_data_ingestion.py
 M tests/test_date_preprocessing.py
 M tests/test_modeling.py
?? "#DOH-202600000699_Top 5 Leading Infectious Diseases in Antipolo City by Month, 2016-2025.pdf"
?? AGENT_HANDOFF.md
?? AUDIT_MATRIX.md
?? Antipolo-dashboard-reconciled-2026-09-27.zip
?? Antipolo-dashboard-reconciled-2026-09-27.zip.sha256
?? CHATGPT_RETURN_HANDOFF.md
?? DATA_RECONCILIATION.md
?? DECISION_LEDGER.md
?? MANUSCRIPT_REVISION_PROPOSALS.md
?? MODEL_EVALUATION.md
?? TEST_RESULTS.md
?? THESIS_READINESS.md
?? dashboard/data/provenance.py
?? evidence/
?? reconciliation/
?? sample-pdf-converted.csv
?? sample-pdf-converted.csv.report.json
?? tests/test_provenance.py
?? tests/test_upload_confirmation.py
```

## 20.4 Complete change inventory

This table compares assignment changes with the preserved initial working tree, not with the last commit. Line numbers identify the first changed/current line; detailed function references are in AUDIT_MATRIX.md current feature coverage. All previously modified files not listed here retain their initial assignment bytes.

| File | Previous behavior | New behavior | Reason | Verification |
|---|---|---|---|---|
| `ARCHITECTURE.md:7` | Fixed SARIMA and cross-family fallback | Exact bounded search, residuals, split and provenance contract | Match actual architecture | Source trace and model tests |
| `CHANGELOG.md:1` | Historical development record | New reconciliation entry; prior entries preserved | Version transparency | Baseline comparison |
| `README.md:5` | Conditional primary and stale interpretation | Current mandatory hybrid/reproduction/limitations | Research reconciliation | Documentation/source trace |
| `dashboard/config.py:18` | Combined source mapped to Measles | Measles-Rubella preserved; historical threshold unused | Preserve source definition | Label tests |
| `tests/test_app_contracts.py:113` | Tests of historical behavior | Updated approved contracts and regression cases | Verify revised semantics | 112-test suite |
| `tests/test_callbacks.py:120` | Tests of historical behavior | Updated approved contracts and regression cases | Verify revised semantics | 112-test suite |
| `tests/test_data_ingestion.py:126` | Tests of historical behavior | Updated approved contracts and regression cases | Verify revised semantics | 112-test suite |
| `tests/test_date_preprocessing.py:9` | Tests of historical behavior | Updated approved contracts and regression cases | Verify revised semantics | 112-test suite |
| `tests/test_modeling.py:14` | Tests of historical behavior | Updated approved contracts and regression cases | Verify revised semantics | 112-test suite |
| `dashboard/callbacks/data_callbacks.py:160` | Upload lacked population/classification/dataset metadata | Metadata defaults/preservation, unverified eligibility notice | Population separation | Upload and provenance tests |
| `dashboard/callbacks/view_callbacks.py:32` | Selected-model labels, limited metadata | Mandatory primary labels, candidate/benchmark/failure details, source-bearing CSV and new cache schema | Transparent model/provenance | Callback tests; actual three-disease exports and traces |
| `dashboard/charts/figures.py:57` | Selected candidate/alternative labels | Primary hybrid and benchmark labels | Mandatory architecture | Trace regression tests |
| `dashboard/data/combine.py:7` | Date preparation without metadata defaults | Separate category guard and metadata retained | Prevent mixed populations | Provenance tests |
| `dashboard/data/date_parser.py:100` | Invalid values dropped and metadata discarded in aggregation | Reject invalid dates/counts/duplicates/synthetic relabel; preserve metadata | No silent data invention | Date and provenance tests |
| `dashboard/data/validation.py:7` | Invalid rows dropped, negatives clipped, counts rounded, duplicate first chosen | Reject invalid labels/counts/calendar fields/duplicates | Preserve original observations | Ingestion tests |
| `dashboard/data/xlsx_parser.py:15` | Blanks silently skipped; partial weeks not identified | Blank/week coverage warnings, incomplete flag, strict numeric validation | Distinguish unknown from zero | Independent1590 cells/360 monthly checks and tests |
| `dashboard/modeling/metrics.py:9` | Missing neural correction filled with zero | Exact aligned finite component contract | No fabricated neural component | Alignment/finite tests and numerical verification |
| `dashboard/modeling/nnar.py:18` | Insufficient history returned zero correction | Explicit failure; baseline architecture plus iteration/convergence metadata | Honest component status | NNAR/failure tests |
| `dashboard/modeling/pipeline.py:1` | WAPE-gated hybrid/base primary | Mandatory hybrid, independent benchmarks, raw components, coverage/provenance validation and preserved failure evidence | Approved hybrid and separation | Model tests;20 numerical records; rolling/error-band checks |
| `dashboard/modeling/sarima.py:1` | Fixed(1, 1, 1)(0, 1, 1) with Holt-Winters/drift fallback | 12 bounded candidates, diagnostics, lowest valid AIC, neural retry; typed failures | Disease-specific identification | Actual40 window searches; failure/retry tests |
| `dashboard/modeling/serialization.py:13` | Baseline arrays/scalars only | Raw components, seasonal-naive, rolling arrays and diagnostics; legacy optional fields | Reviewable provenance | Roundtrip/export tests |
| `dashboard/ui/layout.py:128` | Conditional model-selection explanatory copy | Mandatory hybrid and provisional scope/calendar limitations | Match approved decisions | Component contracts; browser review pending |
| `dashboard/data/provenance.py:1` | Absent | Shared source/population/classification boundary check | Dataset separation | Provenance tests |
| `tests/test_provenance.py:1` | Absent | Source-label, population, metadata/export and invalid-input tests | Regression coverage | Full test suite |

New evidence/documentation files are inventoried at the end of this section. No source data or manuscript content was changed.

### Added artifacts

| File | Previous behavior | New behavior | Reason | Verification |
|---|---|---|---|---|
| `Antipolo-dashboard-reconciled-2026-09-27.zip.sha256:1` | Absent at assignment start | Review artifact / retained evidence; see corresponding report | Independent review/recovery | Source hashes, recorded execution or document inspection |
| `AUDIT_MATRIX.md:1` | Absent at assignment start | Requested consolidated report, proposals, matrices or current ledger | Independent review/recovery | Source hashes, recorded execution or document inspection |
| `DATA_RECONCILIATION.md:1` | Absent at assignment start | Requested consolidated report, proposals, matrices or current ledger | Independent review/recovery | Source hashes, recorded execution or document inspection |
| `DECISION_LEDGER.md:1` | Absent at assignment start | Requested consolidated report, proposals, matrices or current ledger | Independent review/recovery | Source hashes, recorded execution or document inspection |
| `MANUSCRIPT_REVISION_PROPOSALS.md:1` | Absent at assignment start | Requested consolidated report, proposals, matrices or current ledger | Independent review/recovery | Source hashes, recorded execution or document inspection |
| `MODEL_EVALUATION.md:1` | Absent at assignment start | Requested consolidated report, proposals, matrices or current ledger | Independent review/recovery | Source hashes, recorded execution or document inspection |
| `reconciliation/application-verification.json:1` | Absent at assignment start | Machine-readable calculations, metadata, arrays or verification results | Independent review/recovery | Source hashes, recorded execution or document inspection |
| `reconciliation/assignment-change-inventory.json:1` | Absent at assignment start | Machine-readable calculations, metadata, arrays or verification results | Independent review/recovery | Source hashes, recorded execution or document inspection |
| `reconciliation/baseline-hashes.json:1` | Absent at assignment start | Machine-readable calculations, metadata, arrays or verification results | Independent review/recovery | Source hashes, recorded execution or document inspection |
| `reconciliation/baseline-tests.txt:1` | Absent at assignment start | Review artifact / retained evidence; see corresponding report | Independent review/recovery | Source hashes, recorded execution or document inspection |
| `reconciliation/build_handoff.py:1` | Absent at assignment start | Reproducible audit/evaluation/report script | Independent review/recovery | Source hashes, recorded execution or document inspection |
| `reconciliation/build_manuscript_proposals.py:1` | Absent at assignment start | Reproducible audit/evaluation/report script | Independent review/recovery | Source hashes, recorded execution or document inspection |
| `reconciliation/build_package.py:1` | Absent at assignment start | Reproducible audit/evaluation/report script | Independent review/recovery | Source hashes, recorded execution or document inspection |
| `reconciliation/delivery-manifest.json:1` | Absent at assignment start | Machine-readable calculations, metadata, arrays or verification results | Independent review/recovery | Source hashes, recorded execution or document inspection |
| `reconciliation/environment-freeze.txt:1` | Absent at assignment start | Review artifact / retained evidence; see corresponding report | Independent review/recovery | Source hashes, recorded execution or document inspection |
| `reconciliation/evaluate.py:1` | Absent at assignment start | Reproducible audit/evaluation/report script | Independent review/recovery | Source hashes, recorded execution or document inspection |
| `reconciliation/export-dengue.csv:1` | Absent at assignment start | Inspectable source reconciliation or actual forecast export | Independent review/recovery | Source hashes, recorded execution or document inspection |
| `reconciliation/export-leptospirosis.csv:1` | Absent at assignment start | Inspectable source reconciliation or actual forecast export | Independent review/recovery | Source hashes, recorded execution or document inspection |
| `reconciliation/export-measles-rubella.csv:1` | Absent at assignment start | Inspectable source reconciliation or actual forecast export | Independent review/recovery | Source hashes, recorded execution or document inspection |
| `reconciliation/figures-dengue.json:1` | Absent at assignment start | Machine-readable calculations, metadata, arrays or verification results | Independent review/recovery | Source hashes, recorded execution or document inspection |
| `reconciliation/figures-leptospirosis.json:1` | Absent at assignment start | Machine-readable calculations, metadata, arrays or verification results | Independent review/recovery | Source hashes, recorded execution or document inspection |
| `reconciliation/figures-measles-rubella.json:1` | Absent at assignment start | Machine-readable calculations, metadata, arrays or verification results | Independent review/recovery | Source hashes, recorded execution or document inspection |
| `reconciliation/final-git-status.txt:1` | Absent at assignment start | Review artifact / retained evidence; see corresponding report | Independent review/recovery | Source hashes, recorded execution or document inspection |
| `reconciliation/final-working-tree.patch:1` | Absent at assignment start | Review artifact / retained evidence; see corresponding report | Independent review/recovery | Source hashes, recorded execution or document inspection |
| `reconciliation/format_reports.py:1` | Absent at assignment start | Reproducible audit/evaluation/report script | Independent review/recovery | Source hashes, recorded execution or document inspection |
| `reconciliation/full-tests-intermediate.txt:1` | Absent at assignment start | Review artifact / retained evidence; see corresponding report | Independent review/recovery | Source hashes, recorded execution or document inspection |
| `reconciliation/full-tests.txt:1` | Absent at assignment start | Review artifact / retained evidence; see corresponding report | Independent review/recovery | Source hashes, recorded execution or document inspection |
| `reconciliation/initial-git-status.txt:1` | Absent at assignment start | Review artifact / retained evidence; see corresponding report | Independent review/recovery | Source hashes, recorded execution or document inspection |
| `reconciliation/initial-working-tree.patch:1` | Absent at assignment start | Review artifact / retained evidence; see corresponding report | Independent review/recovery | Source hashes, recorded execution or document inspection |
| `reconciliation/manuscript_extracted.json:1` | Absent at assignment start | Machine-readable calculations, metadata, arrays or verification results | Independent review/recovery | Source hashes, recorded execution or document inspection |
| `reconciliation/manuscript_extracted.txt:1` | Absent at assignment start | Review artifact / retained evidence; see corresponding report | Independent review/recovery | Source hashes, recorded execution or document inspection |
| `reconciliation/manuscript_media/image1.png:1` | Absent at assignment start | Original manuscript diagram or source-report rendering | Independent review/recovery | Source hashes, recorded execution or document inspection |
| `reconciliation/manuscript_media/image2.png:1` | Absent at assignment start | Original manuscript diagram or source-report rendering | Independent review/recovery | Source hashes, recorded execution or document inspection |
| `reconciliation/manuscript_media/image3.png:1` | Absent at assignment start | Original manuscript diagram or source-report rendering | Independent review/recovery | Source hashes, recorded execution or document inspection |
| `reconciliation/manuscript_media/image4.png:1` | Absent at assignment start | Original manuscript diagram or source-report rendering | Independent review/recovery | Source hashes, recorded execution or document inspection |
| `reconciliation/manuscript_media/image5.png:1` | Absent at assignment start | Original manuscript diagram or source-report rendering | Independent review/recovery | Source hashes, recorded execution or document inspection |
| `reconciliation/manuscript_media/image6.png:1` | Absent at assignment start | Original manuscript diagram or source-report rendering | Independent review/recovery | Source hashes, recorded execution or document inspection |
| `reconciliation/manuscript_media/image7.png:1` | Absent at assignment start | Original manuscript diagram or source-report rendering | Independent review/recovery | Source hashes, recorded execution or document inspection |
| `reconciliation/manuscript_media/image8.png:1` | Absent at assignment start | Original manuscript diagram or source-report rendering | Independent review/recovery | Source hashes, recorded execution or document inspection |
| `reconciliation/modeling-tests.txt:1` | Absent at assignment start | Review artifact / retained evidence; see corresponding report | Independent review/recovery | Source hashes, recorded execution or document inspection |
| `reconciliation/numerical-verification.json:1` | Absent at assignment start | Machine-readable calculations, metadata, arrays or verification results | Independent review/recovery | Source hashes, recorded execution or document inspection |
| `reconciliation/original-evaluation.json:1` | Absent at assignment start | Machine-readable calculations, metadata, arrays or verification results | Independent review/recovery | Source hashes, recorded execution or document inspection |
| `reconciliation/original-evaluation.log:1` | Absent at assignment start | Review artifact / retained evidence; see corresponding report | Independent review/recovery | Source hashes, recorded execution or document inspection |
| `reconciliation/package-verification.json:1` | Absent at assignment start | Machine-readable calculations, metadata, arrays or verification results | Independent review/recovery | Source hashes, recorded execution or document inspection |
| `reconciliation/pip-check.txt:1` | Absent at assignment start | Review artifact / retained evidence; see corresponding report | Independent review/recovery | Source hashes, recorded execution or document inspection |
| `reconciliation/repository-history.bundle:1` | Absent at assignment start | Recoverable local Git history; git bundle verify passed | Independent review/recovery | Source hashes, recorded execution or document inspection |
| `reconciliation/reproduce_baseline.py:1` | Absent at assignment start | Reproducible audit/evaluation/report script | Independent review/recovery | Source hashes, recorded execution or document inspection |
| `reconciliation/revised-evaluation-initial.json:1` | Absent at assignment start | Machine-readable calculations, metadata, arrays or verification results | Independent review/recovery | Source hashes, recorded execution or document inspection |
| `reconciliation/revised-evaluation.json:1` | Absent at assignment start | Machine-readable calculations, metadata, arrays or verification results | Independent review/recovery | Source hashes, recorded execution or document inspection |
| `reconciliation/revised-evaluation.log:1` | Absent at assignment start | Review artifact / retained evidence; see corresponding report | Independent review/recovery | Source hashes, recorded execution or document inspection |
| `reconciliation/source-annual-reconciliation.csv:1` | Absent at assignment start | Inspectable source reconciliation or actual forecast export | Independent review/recovery | Source hashes, recorded execution or document inspection |
| `reconciliation/source-dengue-page2.png:1` | Absent at assignment start | Original manuscript diagram or source-report rendering | Independent review/recovery | Source hashes, recorded execution or document inspection |
| `reconciliation/source-dengue-text.txt:1` | Absent at assignment start | Review artifact / retained evidence; see corresponding report | Independent review/recovery | Source hashes, recorded execution or document inspection |
| `reconciliation/source-leptospirosis-text.txt:1` | Absent at assignment start | Review artifact / retained evidence; see corresponding report | Independent review/recovery | Source hashes, recorded execution or document inspection |
| `reconciliation/source-measles-rubella-text.txt:1` | Absent at assignment start | Review artifact / retained evidence; see corresponding report | Independent review/recovery | Source hashes, recorded execution or document inspection |
| `reconciliation/source-measles.png:1` | Absent at assignment start | Original manuscript diagram or source-report rendering | Independent review/recovery | Source hashes, recorded execution or document inspection |
| `reconciliation/source-monthly-independent.csv:1` | Absent at assignment start | Inspectable source reconciliation or actual forecast export | Independent review/recovery | Source hashes, recorded execution or document inspection |
| `reconciliation/source-reconciliation.json:1` | Absent at assignment start | Machine-readable calculations, metadata, arrays or verification results | Independent review/recovery | Source hashes, recorded execution or document inspection |
| `reconciliation/source-verification-run.txt:1` | Absent at assignment start | Review artifact / retained evidence; see corresponding report | Independent review/recovery | Source hashes, recorded execution or document inspection |
| `reconciliation/source-weekly-cell-comparison.csv:1` | Absent at assignment start | Inspectable source reconciliation or actual forecast export | Independent review/recovery | Source hashes, recorded execution or document inspection |
| `reconciliation/source_reconcile.py:1` | Absent at assignment start | Reproducible audit/evaluation/report script | Independent review/recovery | Source hashes, recorded execution or document inspection |
| `reconciliation/sources/Antipolo_Disease_Surveillance_2016-2025.xlsx:1` | Absent at assignment start | Byte-identical authoritative original copy; SHA256 verified | Independent review/recovery | Source hashes, recorded execution or document inspection |
| `reconciliation/sources/BRPM_Documentation (2).docx:1` | Absent at assignment start | Byte-identical authoritative original copy; SHA256 verified | Independent review/recovery | Source hashes, recorded execution or document inspection |
| `reconciliation/sources/Distribution of Dengue Cases per Morbidity Week of Antipolo City, Rizal from year 2016-2025.........pdf:1` | Absent at assignment start | Byte-identical authoritative original copy; SHA256 verified | Independent review/recovery | Source hashes, recorded execution or document inspection |
| `reconciliation/sources/Distribution of Measles-Rubella Cases per Morbidity Week of Antipolo City, Rizal from year 2016-2025.pdf:1` | Absent at assignment start | Byte-identical authoritative original copy; SHA256 verified | Independent review/recovery | Source hashes, recorded execution or document inspection |
| `reconciliation/sources/LEPTO 2016-2025 ANTIPOLO.pdf:1` | Absent at assignment start | Byte-identical authoritative original copy; SHA256 verified | Independent review/recovery | Source hashes, recorded execution or document inspection |
| `reconciliation/static-check.txt:1` | Absent at assignment start | Review artifact / retained evidence; see corresponding report | Independent review/recovery | Source hashes, recorded execution or document inspection |
| `reconciliation/verify_application.py:1` | Absent at assignment start | Reproducible audit/evaluation/report script | Independent review/recovery | Source hashes, recorded execution or document inspection |
| `reconciliation/verify_evaluation.py:1` | Absent at assignment start | Reproducible audit/evaluation/report script | Independent review/recovery | Source hashes, recorded execution or document inspection |
| `TEST_RESULTS.md:1` | Absent at assignment start | Requested consolidated report, proposals, matrices or current ledger | Independent review/recovery | Source hashes, recorded execution or document inspection |
| `reconciliation/baseline.zip` | Absent |67-file initial working-tree snapshot | Recovery | baseline-hashes.json |
| `CHATGPT_RETURN_HANDOFF.md:1` | Absent | Consolidated20.1-20.12 handoff | Required return protocol | Final artifact checks |
| `Antipolo-dashboard-reconciled-2026-09-27.zip` | Absent | Current working-tree/source/evidence package | Return/recovery | ZIP CRC and manifest verification |

## 20.5 Modeling implementation

Source: `dashboard/modeling/sarima.py:32`, `dashboard/modeling/nnar.py:22`, `dashboard/modeling/pipeline.py:177`, `dashboard/modeling/metrics.py:18`.

The implemented primary path is `max(0, raw SARIMA prediction + recursive NNAR residual prediction)`.
Benchmarks never replace it. No Holt-Winters, drift, or skipped-NNAR zero correction is substituted.

### Identification within each training window

`modeling/sarima.py::run_arima` tries 12 candidates per window: D in {0, 1}; for each D,
ADF with constant/autolag AIC on seasonally transformed training values sets d=1 when p>0.05,
otherwise d=0. Constant series use d=0 with ADF marked undefined. For each branch,
(p, q) is (1, 0), (0, 1), or (1, 1), and (P, Q) is (1, 0) or (0, 1); period=12.
ACF/PACF through lag 12 (or feasible shorter length) are recorded for inspection; they do
not automatically interpret every significant lag as an order or prove the bounded search exhaustive.

All candidates use trend='c', enforce_stationarity=True, enforce_invertibility=True,
maxiter=300 and common loglikelihood_burn=13. This common scored span avoids favoring
models merely by omitting different initialization observations. Candidate failures,
optimizer convergence, warnings, AIC, minimum root modulus and Ljung-Box lag-12 p-values
(model_df=p+q+P+Q) are retained. Nonconverged/nonfinite fits or roots<=1.000001 are rejected.
Lowest AIC selects among valid fits; residual autocorrelation is a visible warning, not
proof of predictive accuracy or automatic exclusion. These are reproducible engineering
choices for the requested search, not researcher approval of exact bounds or thresholds.

The NNAR component is attempted on the selected base; if it fails, remaining valid
SARIMA candidates are tried in AIC order. The independent SARIMA benchmark remains the
lowest-AIC valid SARIMA regardless of NNAR feasibility. Complete failure raises
`ModelFailure` with status `sarima_failure` or `nnar_failure` and search diagnostics.
Available benchmark diagnostics are retained in the failure object.

### Residual and neural definition

Residuals are observed counts minus one-step in-sample fitted SARIMA means, excluding the
first 13 initialization observations. They never use future holdout actuals. Neural settings
retain the baseline: 3 lags, one hidden layer of 4 ReLU units, lbfgs, alpha=10,
max_iter=2000, random_state=42. StandardScaler is fitted only on training lag features;
target residuals are unscaled. Future residuals are recursive. Iterations and convergence
warnings are stored with each window. Finite forecasts with convergence warnings are
`hybrid_with_warnings`; insufficient residuals or fit exceptions are explicit failures.
This is an MLP residual autoregression, not a package-specific NNAR ensemble.

### Evaluation, refit and uncertainty

For 120 months beginning January 2016: train through 2022/test 2023, train through
2023/test 2024, train through 2024/test 2025, then refit through 2025/forecast2026.
Every SARIMA search is repeated inside its own training window. Earlier-fold comparisons
are diagnostics; `selected_model` is always `hybrid`, `selection_threshold` is null.
The compatibility `selection_*` fields retain their names but no longer select the primary.
2025 remains outside algorithmic search, although its prior human exposure prevents
claiming a pristine, newly unseen confirmatory holdout.

All comparable forecasts use identical actual dates. MAE=mean(abs(error));
RMSE=sqrt(mean(error^2)); MAPE=100*mean(abs(error/actual)) over nonzero actuals;
WAPE=100*sum(abs(error))/sum(abs(actual)). Undefined MAPE/WAPE return null.
Both SARIMA and seasonal-naive benchmarks are retained even if their errors are lower.
Seasonal naive repeats the last 12 training months. Raw component forecasts are exported;
nonnegative clipping happens after hybrid addition, and separately for count benchmarks.

Production uses the full available history after evaluation. The displayed error band
is forecast +/- max(abs(error)) from the earlier folds plus final holdout, lower clipped
to zero. It has no validated coverage guarantee. SARIMA component confidence bounds
are not passed off as a hybrid prediction interval. Decomposition is descriptive only.

### State and provenance

Monthly gaps, duplicate dates, invalid counts, known incomplete week1-52 coverage and
mixed provenance values are rejected before series aggregation. Default minimum is 72
months. Week53 calendar/blank meaning remains provisional. Result metadata includes
status, population, case classification, dataset, coverage, every SARIMA search and NNAR
settings, fold dates, actuals, forecasts and metrics. No upload assertion establishes
verified ages5-19 confirmed-case eligibility; eligible data remain unavailable.

Serialization converts Series to `{index,values,name}` and retains JSON diagnostics;
cache schema `mandatory-hybrid-provenance-v6` invalidates historical conditional-model
results and the SHA256 dataset signature includes stored metadata.

Extra transparency: successful fits are not proof of epidemiological fitness. ACF/PACF are retained for review and do not algorithmically expand the fixed candidate bounds. AIC comparison includes D0/1 branches on a common scored span; its adequacy and exact differencing policy deserve independent statistical scrutiny. Full candidate rejection reasons remain in JSON/UI. Failure objects preserve any completed rolling/holdout metrics and available standalone benchmarks rather than inventing a production forecast.

## 20.6 Data verification

Original source copies and SHA256:

| Source | SHA256 |
|---|---|
| Antipolo_Disease_Surveillance_2016-2025.xlsx | `c8e90c7e040e0c5e5b4676bbe6e26485e6921054d89f684f4f3768ae43cb73ff` |
| Distribution of Dengue Cases per Morbidity Week of Antipolo City, Rizal from year 2016-2025.........pdf | `b581387a11d822148c750291d45e5af6570059fb38bd41e097e13be050508955` |
| Distribution of Measles-Rubella Cases per Morbidity Week of Antipolo City, Rizal from year 2016-2025.pdf | `c2d42390a6b94158b3dd830da3308ca92cec361e5a445f92b8a6fa31459d658a` |
| LEPTO 2016-2025 ANTIPOLO.pdf | `396c1bb1a93cd4c70639ed3bc4486121d772f933f61db53fc0a9bb1a5035ba74` |
| BRPM_Documentation (2).docx | `420b3e867ad9afe2ba4f1515696c7349bb72406a15ed42194d6cf6c9633a34ce` |

All1590 weekly PDF/workbook cells match, including9 source dashes retained as blanks;1581 numeric cells include636 explicit zeros. All30 annual workbook sums match weekly PDF sums. Nineteen of 20 printed PDF totals match; Leptospirosis has no printed annual total. Dengue 2024 remains4516 printed versus4588 weekly/workbook. Weekly rows 1-53 are present;9 Dengue week53 cells 2016-2024 remain unknown. Measles-Rubella week53 has 2 cases 2023 and 5 cases 2025; Dengue 2025 week53 has 56.

Independent calendar aggregation yields360 monthly values/120 per disease and agrees with the revised parser. ISO Thursday assigns weeks to months; non-ISO week53 goes to December. Only2020 is an ISO53-week year within the historical period. This agreement does not authenticate the calendar or reporting completeness. Known missing/blank weeks1-52 block modeling; ambiguous week53 remains provisionally labeled. Workbook Notes incorrectly claims Dengue printed totals all match; original wording was preserved.

None of the three source tables supplies age, enrollment or case-classification fields. All-age status follows the established author description; confirmed-only eligibility cannot be verified. Generic uploads default to unknown metadata, even if structurally similar. Evaluator labels the reviewed original dataset all-age with its workbook hash. Existing browser sessions whose old parser lost Measles-Rubella terminology must re-upload the original; genuine arbitrary Measles labels are not forcibly reinterpreted.

Cells below give PDF printed total / weekly PDF sum / workbook weekly sum. A dash means no printed total exists, not zero cases. The annual CSV contains the full required verification status and follow-up for every row.

| Year | Leptospirosis | Measles-Rubella | Dengue |
|---|---|---|---|
| 2016 | — / 2 / 2 | 51 / 51 / 51 | 1127 / 1127 / 1127 |
| 2017 | — / 4 / 4 | 64 / 64 / 64 | 1004 / 1004 / 1004 |
| 2018 | — / 14 / 14 | 644 / 644 / 644 | 2593 / 2593 / 2593 |
| 2019 | — / 6 / 6 | 1519 / 1519 / 1519 | 2312 / 2312 / 2312 |
| 2020 | — / 5 / 5 | 27 / 27 / 27 | 503 / 503 / 503 |
| 2021 | — / 3 / 3 | 8 / 8 / 8 | 1011 / 1011 / 1011 |
| 2022 | — / 16 / 16 | 26 / 26 / 26 | 2138 / 2138 / 2138 |
| 2023 | — / 124 / 124 | 51 / 51 / 51 | 4274 / 4274 / 4274 |
| 2024 | — / 87 / 87 | 55 / 55 / 55 | **4516 / 4588 / 4588** |
| 2025 | — / 111 / 111 | 110 / 110 / 110 | 5542 / 5542 / 5542 |

All 30 workbook annual sums agree with PDF weekly sums. Nineteen of the twenty printed PDF annual totals agree; Dengue 2024 differs. No printed Leptospirosis total exists, so it would be incorrect to describe its independently computed sum as a verified printed total. CHO must identify the correct Dengue total and any affected weekly cells; this audit does not choose a correction or attribute the difference to a specific week.

## 20.7 Numerical evaluation

Fresh original and revised runs each cover3 real all-age and 7 synthetic series separately. Eligible age-specific results: unavailable. Complete unrounded arrays, raw components, monthly actuals, rolling folds, all selected configurations and diagnostics are in the JSON artifacts. MODEL_EVALUATION.md reports all four metrics for all methods; its tables are reproduced below for independent review.

These are prior handoff findings, not revised output: Dengue 25.17%, Leptospirosis67.08%, category then called Measles162.58% selected-model WAPE; naive34.90%, 55.86%, 50.00%. Fresh baseline results below independently reproduce their rounded values.

### Original implementation: all_age

| Disease | Method | MAE | RMSE | MAPE % | WAPE % | Nonzero MAPE months |
|---|---|---:|---:|---:|---:|---:|
| Dengue | Hybrid (primary) | 116.2294 | 139.9173 | 33.6716 | 25.1670 | 12/12 |
| Dengue | SARIMA-only | 126.3746 | 151.5495 | 37.2044 | 27.3637 | 12/12 |
| Dengue | Seasonal naive | 161.1667 | 185.7812 | 41.9819 | 34.8971 | 12/12 |
| Leptospirosis | Hybrid | 6.4840 | 11.2451 | 158.8059 | 70.0969 | 11/12 |
| Leptospirosis | SARIMA-only (primary) | 6.2052 | 9.9232 | 163.8850 | 67.0834 | 11/12 |
| Leptospirosis | Seasonal naive | 5.1667 | 10.5119 | 72.8854 | 55.8559 | 11/12 |
| Measles | Hybrid | 14.9570 | 18.7418 | 175.6830 | 163.1675 | 12/12 |
| Measles | SARIMA-only (primary) | 14.9028 | 18.4918 | 175.2038 | 162.5765 | 12/12 |
| Measles | Seasonal naive | 4.5833 | 5.5453 | 47.3336 | 50.0000 | 12/12 |

### Original implementation: synthetic

| Disease | Method | MAE | RMSE | MAPE % | WAPE % | Nonzero MAPE months |
|---|---|---:|---:|---:|---:|---:|
| Dengue | Hybrid | 8.3510 | 9.4146 | 27.9711 | 23.9170 | 12/12 |
| Dengue | SARIMA-only (primary) | 9.4340 | 10.3955 | 32.0235 | 27.0185 | 12/12 |
| Dengue | Seasonal naive | 7.9167 | 10.9886 | 20.0039 | 22.6730 | 12/12 |
| Acute Respiratory Infection | Hybrid | 11.7161 | 12.3167 | 69.1433 | 52.8548 | 12/12 |
| Acute Respiratory Infection | SARIMA-only (primary) | 10.3083 | 10.8370 | 61.3260 | 46.5037 | 12/12 |
| Acute Respiratory Infection | Seasonal naive | 4.1667 | 5.8166 | 22.6787 | 18.7970 | 12/12 |
| Influenza-like Illness | Hybrid | 8.4204 | 9.4364 | 56.2754 | 46.1392 | 12/12 |
| Influenza-like Illness | SARIMA-only (primary) | 8.3778 | 9.4137 | 55.9997 | 45.9058 | 12/12 |
| Influenza-like Illness | Seasonal naive | 5.5000 | 7.1647 | 35.3376 | 30.1370 | 12/12 |
| Tuberculosis | Hybrid | 3.8486 | 4.6119 | 45.0299 | 28.3332 | 12/12 |
| Tuberculosis | SARIMA-only (primary) | 3.3778 | 4.1499 | 40.3844 | 24.8676 | 12/12 |
| Tuberculosis | Seasonal naive | 4.0833 | 4.7871 | 33.5922 | 30.0613 | 12/12 |
| Hand Foot & Mouth Disease | Hybrid | 3.6685 | 4.0621 | 66.1595 | 41.1423 | 12/12 |
| Hand Foot & Mouth Disease | SARIMA-only (primary) | 3.4140 | 3.7281 | 61.1892 | 38.2884 | 12/12 |
| Hand Foot & Mouth Disease | Seasonal naive | 1.9167 | 2.1794 | 25.7641 | 21.4953 | 12/12 |
| Measles | Hybrid | 2.2486 | 2.5031 | 61.7881 | 45.7336 | 12/12 |
| Measles | SARIMA-only (primary) | 2.3083 | 2.5613 | 64.0402 | 46.9475 | 12/12 |
| Measles | Seasonal naive | 1.5000 | 2.1213 | 37.1528 | 30.5085 | 12/12 |
| Leptospirosis | Hybrid | 3.2910 | 3.4123 | 70.3469 | 54.0981 | 12/12 |
| Leptospirosis | SARIMA-only (primary) | 3.3614 | 3.4803 | 71.7957 | 55.2553 | 12/12 |
| Leptospirosis | Seasonal naive | 1.8333 | 2.0412 | 33.8961 | 30.1370 | 12/12 |

### Revised mandatory hybrid: all_age

| Disease | Method | MAE | RMSE | MAPE % | WAPE % | Nonzero MAPE months |
|---|---|---:|---:|---:|---:|---:|
| Dengue | Hybrid (primary) | 160.9763 | 201.2782 | 48.9126 | 34.8559 | 12/12 |
| Dengue | SARIMA-only | 162.4125 | 200.7529 | 49.3110 | 35.1669 | 12/12 |
| Dengue | Seasonal naive | 161.1667 | 185.7812 | 41.9819 | 34.8971 | 12/12 |
| Leptospirosis | Hybrid (primary) | 5.4236 | 9.8391 | 104.9136 | 58.6331 | 11/12 |
| Leptospirosis | SARIMA-only | 5.3443 | 9.8089 | 109.2864 | 57.7757 | 11/12 |
| Leptospirosis | Seasonal naive | 5.1667 | 10.5119 | 72.8854 | 55.8559 | 11/12 |
| Measles-Rubella | Hybrid (primary) | 52.8594 | 64.9712 | 584.6661 | 576.6479 | 12/12 |
| Measles-Rubella | SARIMA-only | 17.6486 | 17.8359 | 215.9056 | 192.5303 | 12/12 |
| Measles-Rubella | Seasonal naive | 4.5833 | 5.5453 | 47.3336 | 50.0000 | 12/12 |

### Revised mandatory hybrid: synthetic

| Disease | Method | MAE | RMSE | MAPE % | WAPE % | Nonzero MAPE months |
|---|---|---:|---:|---:|---:|---:|
| Dengue | Hybrid (primary) | 8.3505 | 10.9067 | 28.0596 | 23.9155 | 12/12 |
| Dengue | SARIMA-only | 9.3389 | 13.3655 | 24.4381 | 26.7464 | 12/12 |
| Dengue | Seasonal naive | 7.9167 | 10.9886 | 20.0039 | 22.6730 | 12/12 |
| Acute Respiratory Infection | Hybrid (primary) | 9.4086 | 10.6486 | 63.4620 | 42.4446 | 12/12 |
| Acute Respiratory Infection | SARIMA-only | 7.0012 | 7.8741 | 47.2504 | 31.5842 | 12/12 |
| Acute Respiratory Infection | Seasonal naive | 4.1667 | 5.8166 | 22.6787 | 18.7970 | 12/12 |
| Influenza-like Illness | Hybrid (primary) | 4.0311 | 4.8611 | 30.3487 | 22.0879 | 12/12 |
| Influenza-like Illness | SARIMA-only | 4.2866 | 5.1784 | 30.5678 | 23.4882 | 12/12 |
| Influenza-like Illness | Seasonal naive | 5.5000 | 7.1647 | 35.3376 | 30.1370 | 12/12 |
| Tuberculosis | Hybrid (primary) | 4.2305 | 4.7123 | 44.1818 | 31.1449 | 12/12 |
| Tuberculosis | SARIMA-only | 4.2652 | 4.9137 | 42.9974 | 31.4003 | 12/12 |
| Tuberculosis | Seasonal naive | 4.0833 | 4.7871 | 33.5922 | 30.0613 | 12/12 |
| Hand Foot & Mouth Disease | Hybrid (primary) | 5.7265 | 6.2398 | 92.2155 | 64.2226 | 12/12 |
| Hand Foot & Mouth Disease | SARIMA-only | 5.6249 | 6.1467 | 90.6732 | 63.0834 | 12/12 |
| Hand Foot & Mouth Disease | Seasonal naive | 1.9167 | 2.1794 | 25.7641 | 21.4953 | 12/12 |
| Measles-Rubella | Hybrid (primary) | 1.3100 | 1.4395 | 36.9861 | 26.6432 | 12/12 |
| Measles-Rubella | SARIMA-only | 1.3143 | 1.4411 | 36.8401 | 26.7313 | 12/12 |
| Measles-Rubella | Seasonal naive | 1.5000 | 2.1213 | 37.1528 | 30.5085 | 12/12 |
| Leptospirosis | Hybrid (primary) | 1.6124 | 1.9619 | 35.6644 | 26.5056 | 12/12 |
| Leptospirosis | SARIMA-only | 1.5700 | 1.9433 | 34.3529 | 25.8082 | 12/12 |
| Leptospirosis | Seasonal naive | 1.8333 | 2.0412 | 33.8961 | 30.1370 | 12/12 |

### Selected revised configurations

Each disease/window performs its own12-candidate search. AIC and residual diagnostics are training diagnostics, not accuracy claims.

| Dataset | Disease | 2023 fold | 2024 fold | 2025 holdout | Full-history production |
|---|---|---|---|---|---|
| all_age | Dengue | (1, 0, 0)(0, 1, 1, 12) | (1, 0, 0)(1, 0, 0, 12) | (0, 1, 1)(0, 1, 1, 12) | (1, 0, 0)(0, 1, 1, 12) |
| all_age | Leptospirosis | (1, 0, 0)(0, 0, 1, 12) | (1, 0, 1)(1, 0, 0, 12) | (1, 0, 1)(0, 1, 1, 12) | (1, 0, 0)(1, 1, 0, 12) |
| all_age | Measles-Rubella | (1, 0, 1)(1, 0, 0, 12) | (1, 0, 1)(1, 0, 0, 12) | (1, 0, 1)(1, 0, 0, 12) | (1, 0, 1)(1, 0, 0, 12) |
| synthetic | Dengue | (1, 1, 1)(1, 0, 0, 12) | (1, 1, 1)(1, 0, 0, 12) | (1, 1, 1)(1, 0, 0, 12) | (0, 1, 1)(0, 1, 1, 12) |
| synthetic | Acute Respiratory Infection | (1, 1, 1)(1, 0, 0, 12) | (1, 1, 1)(1, 0, 0, 12) | (0, 1, 1)(1, 0, 0, 12) | (0, 1, 1)(0, 1, 1, 12) |
| synthetic | Influenza-like Illness | (0, 1, 1)(1, 0, 0, 12) | (0, 1, 1)(1, 0, 0, 12) | (1, 1, 1)(1, 0, 0, 12) | (1, 1, 1)(1, 0, 0, 12) |
| synthetic | Tuberculosis | (1, 1, 1)(1, 0, 0, 12) | (1, 1, 0)(1, 0, 0, 12) | (1, 1, 0)(1, 0, 0, 12) | (1, 1, 1)(0, 1, 1, 12) |
| synthetic | Hand Foot & Mouth Disease | (1, 1, 0)(1, 0, 0, 12) | (1, 1, 0)(1, 1, 0, 12) | (1, 1, 0)(1, 1, 0, 12) | (1, 1, 0)(0, 1, 1, 12) |
| synthetic | Measles-Rubella | (0, 1, 1)(1, 0, 0, 12) | (1, 1, 1)(1, 0, 0, 12) | (1, 1, 1)(1, 0, 0, 12) | (1, 1, 1)(1, 0, 0, 12) |
| synthetic | Leptospirosis | (1, 1, 1)(1, 0, 0, 12) | (1, 1, 1)(1, 0, 0, 12) | (1, 1, 1)(1, 0, 0, 12) | (1, 1, 1)(1, 0, 0, 12) |

No hyperparameters were subsequently tuned to reduce the disclosed2025 errors. Poor Measles-Rubella performance is evidence against a broad superiority claim, not a reason to suppress the hybrid or invent a favorable dataset. The historical holdout is computationally excluded from search, but was previously examined by developers; prospective confirmation remains unresolved.

## 20.8 Testing

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

### Environment

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

### Meaningful coverage

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

### Unverified checks

No browser automation tool was callable; neither playwright nor selenium was installed. Actual browser
rendering, narrow-screen layout, clickable interactions and session-size behavior remain unverified.
No Gunicorn/container deployment, clean dependency installation, public-service security assessment,
CHO acceptance or expert usability assessment was performed. File copies/hashes and Git history bundle
provide recovery; no commit, push, deployment or external message was made.

## 20.9 Manuscript reconciliation

The authoritative DOCX was not edited. MANUSCRIPT_REVISION_PROPOSALS.md provides44 traceable proposals: original paragraphs or diagram labels, exact replacement wording, reason, source evidence and acceptance status. The manuscript extraction includes 292 XML paragraphs, three tables and eight figures. It contains introduction and Chapter 2; no completed results chapter was present. Text/diagram review is not a full Word pagination/formatting proofread.

Chapters/sections needing changes: both title dates; background/causal and superiority statements; objectives (five models vs initial three categories); significance and resource-allocation claims; population and public-school delimitation; confirmed-only eligibility vs suspected cases; historical period2016-2025 vs2016-2026/2015-2025; disease terminology; literature comparison/ref duplicates; research design; data preprocessing and COVID-imputation claims; decomposition vs model residuals; SARIMA identification; NNAR settings; metric definitions/denominators; rolling/holdout split; uncertainty; session stores vs databases/model persistence; software/dependency versions; all conflicting Figures1-8; glossary; source completeness; bibliographic validation; future-dated cover; evaluation-standard/security-scope discrepancies.

Exact core insertion: "The primary forecast is the nonnegative sum of the SARIMA point prediction and the NNAR residual prediction. SARIMA-only and seasonal naive are reported as benchmarks on the same held-out dates; their lower errors do not replace the primary hybrid. Each SARIMA identification procedure uses only its own training window. A failed component makes the hybrid unavailable rather than triggering a different model family."

Exact population insertion: "The approved population is individuals aged 5-19 in city-wide Antipolo surveillance, with findings intended to inform public-school preparedness. Existing all-age totals are evaluated separately and do not establish performance for that population or confirmed-only cases. Enrollment or transmission within public schools is not inferred."

Exact uncertainty insertion: "The displayed band uses the maximum historical absolute hybrid error from earlier evaluation folds and the final holdout, with a nonnegative lower bound. It is descriptive; no validated95% future prediction coverage is claimed."

External32.22 provenance is now verified against [Olana et al.(2025), publisher Table1](https://doi.org/10.1155/tbed/7480710): national dengue SARIMA testing MAPE, train 2017-2023/test 2024. Its use as a local acceptance standard is unsupported. Other bibliography claims were not exhaustively authenticated.

## 20.10 Remaining decisions

The following is a synchronized delivery snapshot of the single authoritative DECISION_LEDGER.md, not an independently maintained ledger.

Updated 27 September 2026. Historical THESIS_READINESS.md and AGENT_HANDOFF.md remain evidence, not competing current ledgers. Each item has exactly one status. Implementation success does not resolve source eligibility or manuscript acceptance.

| ID | Item / decision | Status | Evidence / next step |
|---|---|---|---|
| D01 | Hybrid primary; benchmarks cannot win production selection | Resolved and verified | Mandatory-path tests; all 10 revised runs selected hybrid |
| D02 | Bounded disease/window-specific SARIMA identification | Resolved and verified |12 candidates/window, training-only dates, ADF/ACF/PACF/AIC/root/Ljung-Box evidence; candidate failure/retry tests |
| D03 | NNAR true component and explicit failure states | Resolved and verified | Baseline architecture preserved; no skipped zero correction; retry/all-fail tests and recorded convergence warnings |
| D04 | Preserve Measles-Rubella source terminology | Resolved and verified | Source parser, cache version, output and tests |
| D05 | Separate synthetic/real, population and case classification | Resolved and verified | Mixed-value rejection, provenance serialization/export and all-age separate evaluator; labels never certify eligibility |
| D06 | Original working tree/evidence preservation | Resolved and verified | baseline.zip, initial status/patch/hashes, Git history bundle; no original evidence file removed |
| D07 | Numerical before/after evaluation and unfavorable results | Resolved and verified |20 series/version records, independent arithmetic verification, arrays and MODEL_EVALUATION.md |
| D08 |32.22 historical reference provenance | Resolved and verified | Olana2025 publisher Table 1, national dengue SARIMA test MAPE; not a local performance standard |
| D09 | Workbook transcription vs original PDFs | Resolved and verified |1590 cell comparisons;360 monthly values;30 weekly/workbook annual totals; printed discrepancy preserved |
| D10 | Approved ages5-19 confirmed-case evaluation | Blocked by unavailable evidence | No eligible extract supplied; do not infer age/enrollment from all-age totals |
| D11 | Historical case definitions and confirmed-only status | Awaiting CHO confirmation | Need classification/case-definition fields and office verification; generic labels are unverified |
| D12 | Final disease set and combined Measles-Rubella classification | Awaiting CHO confirmation | Initial three categories retained; consult epidemiologist then researcher/adviser; no Top 5 pivot |
| D13 | Official epidemiological calendar and week53/dash meaning | Awaiting CHO confirmation | ISO Thursday plus December week53 provisionally retained;9 unknown Dengue blanks; known incomplete week1-52 data block modeling |
| D14 | Corrected Dengue 2024 source values | Awaiting CHO confirmation | Printed4516 vs weekly/workbook 4588, difference 72; request corrected total and any affected weekly cells |
| D15 | Final operational horizon | Awaiting CHO confirmation |1/3/12-month usefulness needs interview; current 12-month capability retained |
| D16 | Exact manuscript title and 44 wording/diagram proposals | Awaiting researcher decision | Review MANUSCRIPT_REVISION_PROPOSALS.md; original untouched; approved scope is not reopened |
| D17 | Statistical acceptance of exact bounded search choices and warning policy | Awaiting adviser decision | Review d/D decision, 12-candidate bounds, constant trend, common burn 13, stationarity/root checks, lag 12 diagnostic, finite-but-nonconverged NNAR warnings; implementation choices are not formal protocol approval |
| D18 | Prior exposure to 2025 and prospective confirmation plan | Awaiting adviser decision | Code excludes2025 from training search, but historical developers saw errors; consider prospective future observations vs descriptive retrospective evaluation |
| D19 | Manuscript bibliographic claims, duplicate references and evaluation-standard edition | Awaiting adviser decision | M10/M27 and comparative-table inconsistencies; no exhaustive primary-literature authentication |
| D20 | Browser desktop/narrow rendering and interaction review | Implemented, pending validation | HTTP, components, callbacks, exports and trace bindings checked; no callable browser automation and Python browser packages absent |
| D21 | Pinned clean environment and container deployment | Implemented, pending validation | Installed environment tested and pip check clean; repository pins not installed; container/Gunicorn not run |
| D22 | Formal CHO acceptance and expert usability results | Blocked by unavailable evidence | No interview/acceptance/usability dataset; no scores or approval invented |
| D23 | Clinical utility, resource allocation and causal outcomes | Blocked by unavailable evidence | App forecasts counts; no allocation/dispatch/causal/prevention module or outcome validation |
| D24 | General PDF conversion of supplied complex reports | Awaiting researcher decision | Generic auto-table converter does not completely extract Measles and Dengue page2; workbook and source-specific audited extraction are verified; broader generalized converter repair outside authorized core corrections |

### Material researcher/adviser questions

1. **Exact wording/title approval (D16):** accept the proposed scope-accurate title and corrected prose, or retain the current title with explicit population/setting qualifications. The former is supported by the approved ages5-19 city-wide scope; either requires adviser approval. This affects manuscript accuracy, not the already-approved population.
2. **Confirmatory evaluation plan (D18):** describe2025 honestly as an algorithmically excluded but previously examined retrospective holdout, or additionally preregister a future untouched period when observations arrive. Evidence supports the first label now; prospective evidence would provide stronger independent confirmation. Do not choose new settings by optimizing on the disclosed2025 errors.
3. **Exact technical protocol (D17):** accept the documented bounded search as the implementation protocol, or prospectively amend search bounds/diagnostics with rationale before fresh confirmation. Current evidence supports reproducibility, not optimality or clinical validity. An amendment needs new versioned evaluation, with all adverse baseline results retained.

CHO questions belong to D11-D15 and must be answered by source-office records/interview, not researcher guesses. The age range, mandatory hybrid and population-separation decisions are already settled and are not questions.

## 20.11 Independent review requests

- Check the actual search/training boundaries and whether prior2025 exposure undermines confirmatory claims despite algorithmic exclusion.
- Scrutinize the12-candidate bounds, D0/1 treatment, ADF policy, common AIC burn, constant trend, stability tolerance and residual whiteness warning policy; these are implementation choices, not a demonstrated optimal search.
- Inspect residual initialization/alignment, training-only feature scaling, recursion and finite NNAR convergence-warning policy; confirm raw addition before nonnegative clipping.
- Verify independent SARIMA/seasonal-naive benchmark fairness, all unfavorable arrays, MAPE/WAPE zero handling and the lack of any superiority guarantee.
- Cross-check1590 original weekly cells, 9 unknown blanks, week53 assignment, missing age/classification and Dengue 2024 totals; arithmetic agreement is not source-office approval.
- Review all 44 manuscript proposals and conflicting figures against the original DOCX; no proposed wording is automatically accepted.
- Inspect UI metadata and exports; perform missing desktop/mobile browser and clean pinned/container checks. Check whether additional eligibility controls are needed when actual verified records arrive.
- Challenge every resolved claim using its test/source artifact; passing112 tests does not certify methodology, clinical utility or thesis readiness.

## 20.12 Final limitations

This work establishes a recoverable, tested implementation of the authorized technical corrections and auditable retrospective calculations. It does not establish target-population performance, confirmed-case eligibility, complete surveillance, official calendar correctness, corrected Dengue counts, final disease/horizon approval, validated probabilistic coverage, causal mechanisms, clinical safety, prevention, optimized medical allocation, field benefit, formal CHO acceptance, expert usability, publication readiness or a previously unseen confirmatory validation set.

General PDF extraction remains partial for the complex original layouts; source-specific audit extraction and the workbook are verified. Source copies are bundled for researcher review, not independently authorized public redistribution. No upload label or file hash authenticates the issuing office. Exact dependency pins and browser rendering remain unverified. The current deliverable is ready for independent technical/research review, not a claim of final thesis acceptance.

### Return files and recovery

Return CHATGPT_RETURN_HANDOFF.md, Antipolo-dashboard-reconciled-2026-09-27.zip, TEST_RESULTS.md, MODEL_EVALUATION.md and MANUSCRIPT_REVISION_PROPOSALS.md. The ZIP includes these reports, AUDIT_MATRIX.md, DATA_RECONCILIATION.md, DECISION_LEDGER.md, original source copies, current code/tests, baseline.zip and repository-history.bundle. Restore the baseline ZIP into a new directory to inspect initial uncommitted files; do not overwrite the active workspace. Git history can be recovered from the verified bundle in a separate directory, then overlaid with the delivered working-tree files. No original branch was modified by a commit.

Copyable return message:

"Continue my Antipolo thesis audit using the attached coding-agent handoff and updated repository. Independently review the implementation, reconcile it against my original manuscript and established research decisions, challenge unsupported claims, identify remaining inconsistencies, and ask me only the next material clarification questions. Do not assume the coding agent's conclusions are correct simply because tests passed."
