# Thesis reconciliation and current decision ledger

Date: 2026-09-26. This is the current consolidated handoff; older changelog entries are historical. No modeling, generator, or selection-threshold changes were made in this handoff. Existing uncommitted work was preserved.

## Readiness against the five requested conditions

1. **Implemented and functionally verified:** both references appear as separate neutral cards in Forecasts and Technical model details. Exact copy appears below. Tests verify identical content, neutral colors, and undefined-score handling.
2. **Implemented and verified:** pending CSV/XLSX and PDF-converted tabular uploads cannot activate until the explicit confirmation button event. The full disease table is shown; old clicks, rejected replacements, reset, and first-load uploads are covered. Registered Dash HTTP callbacks reproduce the Malaria case below.
3. **Investigation delivered:** the real-data finding is adverse for two of three diseases, separately from six of seven synthetic diseases. Arithmetic was independently recomputed from prediction arrays, and all 30 real disease/year input totals reconcile. Evidence and limits below support the thesis decisions; they do not establish universal superiority or a causal proof of overfitting.
4. **Fresh full suite passes:** 85 passed, 11 warnings. Actual verbose output and an itemized breakdown are included below.
5. **Single current decision document:** all remaining decisions and manuscript actions are in the ledger at the end of the analysis.

Functional acceptance is verified through Dash component trees and registered HTTP callbacks. A live-browser pixel/layout inspection was not performed: no browser automation tool or installed Playwright/Selenium was available. This is a verification limitation, not a claim that screenshots were checked. The thesis itself still needs the author's decisions and source citation; this handoff does not certify scientific superiority or publication readiness.

## Item 1: exact reference wording

Both forecast cards (`_build_hybrid_metric_cards`) and the Technical model details UI (`render_technical_baselines`) use the same `_baseline_cards` helper in `dashboard/callbacks/view_callbacks.py`:

- Label: **Historical reference MAPE**; value: **32.22%**.
- Supporting text: **Fixed external/thesis reference; not computed from the active dataset. See thesis manuscript for source.**
- Label: **Seasonal-naive holdout MAPE/WAPE**; value format: **X.XX% / Y.YY%**, MAPE first, WAPE second; undefined values are **N/A**.
- Supporting text: **Live benchmark for this disease and dataset; copies the previous year's months into the same holdout. MAPE excludes zero-actual months.**

There is no ranking, merging, averaging, good/bad comparison, or use of the historical figure in selection. Both reference cards pass `good=None` to the existing metric component. The historical number is fixed across datasets, including when a live metric is unavailable; live scores come from `baseline_metrics` for the selected disease.

Exact config line:

```python
HISTORICAL_REFERENCE_MAPE = 32.22  # external/thesis reference figure, not computed from the active dataset; see thesis manuscript for source
```

README.md and ARCHITECTURE.md contain the same exact explanatory section:


```text
### Historical reference and live benchmark

**Historical reference MAPE: 32.22%** is a fixed external/thesis reference,
not computed from the active dataset. See the thesis manuscript for its source.
**Seasonal-naive holdout MAPE/WAPE** is computed separately for each disease
and active dataset by copying the previous year's monthly observations into
the same untouched 12-month holdout. MAPE excludes zero-actual months; WAPE
uses the sum of absolute actual cases as its denominator. Undefined scores
are shown as N/A. The UI displays MAPE first, then WAPE, separated by a slash.
These are distinct references, shown side by side with neutral styling; they
are not merged, averaged, ranked against each other, or used to select a model.
Seasonal naive remains a diagnostic benchmark, not a production candidate.

Current evidence, exact UI wording, verification output, and all outstanding
thesis decisions are consolidated in [THESIS_READINESS.md](THESIS_READINESS.md).
```


## Item 2: explicit catalog confirmation

`load_data` decodes, normalizes, validates, and stages a candidate; its upload path returns `no_update` for active data. `transition_data_session` is the single active/pending-state dispatcher. Only the `confirm-upload-catalog` event with a positive click and a valid pending candidate calls `confirm_pending_upload(..., confirmed=True)`.

The existing Upload summary displays every validated disease label in its disease-coverage table (page size equals the entire catalog length), then the existing preview and validation notes. The preview's ten-row limit does not limit the disease list. Active data and active summary remain unchanged while review is pending. A replacement upload supersedes pending data, rejection prevents approval of a previous candidate, reset restores sample and clears pending data, and refresh discards memory-only pending data. Session-persisted confirmed data survives refresh. The feature is a user-confirmation workflow, not a security boundary against a browser owner altering client storage.

Arbitrary nonblank disease names remain allowed. This is consistent with converted PDF/ICD-10 categories because no fixed disease whitelist is introduced. The XLSX regression includes Malaria, A90 Dengue, Pediculosis, and nine other category labels and verifies all twelve are visible and survive confirmation. Direct PDF upload remains unsupported; the existing converter produces CSV/XLSX for this same gate. Existing disease-label normalization is retained.

Actual reproduction command: `python -X utf8 -m evidence.reproduce_upload`. This invokes `/_dash-layout`, `/_dash-dependencies`, and registered `/_dash-update-component` endpoints through Flask's test client. It does not substitute direct helper calls for the end-to-end HTTP wiring.

Actual output (including the returned metric component JSON):

```text
2026-09-26 15:04:05 INFO     dashboard.callbacks.data_callbacks: no existing session data -- generating fresh sample dataset
2026-09-26 15:04:05 INFO     dashboard.callbacks.data_callbacks: staged 'malaria.csv' for explicit disease-catalog confirmation
Dash layout/dependencies: HTTP 200
Upload: Dengue=10; Malaria=500
Before confirmation: active store unchanged; active summary unchanged
Visible confirmation table: [{"disease": "Dengue", "source": "Real", "row_count": 1, "year_range": "2025"}, {"disease": "Malaria", "source": "Real", "row_count": 1, "year_range": "2025"}]
Confirmation button: {"children": "Use these 2 diseases", "disabled": false}
Before confirmation: Malaria absent from active summary cards
After explicit confirmation, actual metric-row output:
{"children": {"props": {"children": [{"props": {"children": [{"props": {"children": "Total cases", "style": {"fontSize": "10px", "color": "#888", "margin": "0 0 5px", "textTransform": "uppercase", "letterSpacing": "0.05em"}}, "type": "P", "namespace": "dash_html_components"}, {"props": {"children": "510", "style": {"fontSize": "21px", "fontWeight": "500", "color": "#333333", "margin": "0"}}, "type": "P", "namespace": "dash_html_components"}, {"props": {"children": "(2025\u20132025)", "style": {"fontSize": "11px", "margin": "3px 0 0", "color": "#888"}}, "type": "P", "namespace": "dash_html_components"}], "style": {"background": "#F7F7F5", "borderRadius": "8px", "padding": "13px 16px", "flex": "1", "minWidth": "120px"}}, "type": "Div", "namespace": "dash_html_components"}, {"props": {"children": [{"props": {"children": "Peak year", "style": {"fontSize": "10px", "color": "#888", "margin": "0 0 5px", "textTransform": "uppercase", "letterSpacing": "0.05em"}}, "type": "P", "namespace": "dash_html_components"}, {"props": {"children": "2025", "style": {"fontSize": "21px", "fontWeight": "500", "color": "#333333", "margin": "0"}}, "type": "P", "namespace": "dash_html_components"}, {"props": {"children": "510 cases", "style": {"fontSize": "11px", "margin": "3px 0 0", "color": "#888"}}, "type": "P", "namespace": "dash_html_components"}], "style": {"background": "#F7F7F5", "borderRadius": "8px", "padding": "13px 16px", "flex": "1", "minWidth": "120px"}}, "type": "Div", "namespace": "dash_html_components"}, {"props": {"children": [{"props": {"children": "Top disease", "style": {"fontSize": "10px", "color": "#888", "margin": "0 0 5px", "textTransform": "uppercase", "letterSpacing": "0.05em"}}, "type": "P", "namespace": "dash_html_components"}, {"props": {"children": "Malaria", "style": {"fontSize": "21px", "fontWeight": "500", "color": "#333333", "margin": "0"}}, "type": "P", "namespace": "dash_html_components"}, {"props": {"children": "98% of cases", "style": {"fontSize": "11px", "margin": "3px 0 0", "color": "#888"}}, "type": "P", "namespace": "dash_html_components"}], "style": {"background": "#F7F7F5", "borderRadius": "8px", "padding": "13px 16px", "flex": "1", "minWidth": "120px"}}, "type": "Div", "namespace": "dash_html_components"}, {"props": {"children": [{"props": {"children": "COVID years", "style": {"fontSize": "10px", "color": "#888", "margin": "0 0 5px", "textTransform": "uppercase", "letterSpacing": "0.05em"}}, "type": "P", "namespace": "dash_html_components"}, {"props": {"children": "2020\u201322", "style": {"fontSize": "21px", "fontWeight": "500", "color": "#333333", "margin": "0"}}, "type": "P", "namespace": "dash_html_components"}, {"props": {"children": "Structural break", "style": {"fontSize": "11px", "margin": "3px 0 0", "color": "#888"}}, "type": "P", "namespace": "dash_html_components"}], "style": {"background": "#F7F7F5", "borderRadius": "8px", "padding": "13px 16px", "flex": "1", "minWidth": "120px"}}, "type": "Div", "namespace": "dash_html_components"}, {"props": {"children": [{"props": {"children": "Scope", "style": {"fontSize": "10px", "color": "#888", "margin": "0 0 5px", "textTransform": "uppercase", "letterSpacing": "0.05em"}}, "type": "P", "namespace": "dash_html_components"}, {"props": {"children": "Antipolo City", "style": {"fontSize": "21px", "fontWeight": "500", "color": "#333333", "margin": "0"}}, "type": "P", "namespace": "dash_html_components"}, {"props": {"children": "City-wide", "style": {"fontSize": "11px", "margin": "3px 0 0", "color": "#888"}}, "type": "P", "namespace": "dash_html_components"}], "style": {"background": "#F7F7F5", "borderRadius": "8px", "padding": "13px 16px", "flex": "1", "minWidth": "120px"}}, "type": "Div", "namespace": "dash_html_components"}, {"props": {"children": [{"props": {"children": "Real data", "style": {"fontSize": "10px", "color": "#888", "margin": "0 0 5px", "textTransform": "uppercase", "letterSpacing": "0.05em"}}, "type": "P", "namespace": "dash_html_components"}, {"props": {"children": "2", "style": {"fontSize": "21px", "fontWeight": "500", "color": "#333333", "margin": "0"}}, "type": "P", "namespace": "dash_html_components"}, {"props": {"children": "Dengue, Malaria", "style": {"fontSize": "11px", "margin": "3px 0 0", "color": "#888"}}, "type": "P", "namespace": "dash_html_components"}], "style": {"background": "#F7F7F5", "borderRadius": "8px", "padding": "13px 16px", "flex": "1", "minWidth": "120px"}}, "type": "Div", "namespace": "dash_html_components"}], "style": {"display": "flex", "gap": "10px", "flexWrap": "wrap"}}, "type": "Div", "namespace": "dash_html_components"}}
PASS: Malaria is visible for approval before it becomes Top disease.
```


## Item 3: sensitivity evidence, no policy change

Selection was recomputed from full-precision aggregate WAPE on the same 2023 and 2024 expanding-origin folds for every sample disease. At threshold zero Hybrid must be strictly lower; exact ties select base-only. Other columns apply the existing `gain >= threshold and hybrid < base` mechanism. No threshold was assigned or monkeypatched in the pipeline; these are read-only counterfactual calculations from the pipeline's returned scores.

S = SARIMA-only; H = Hybrid. All sample holdout base fits used SARIMA; the script retains actual fold tiers and warnings.


| Disease | Rolling gain (pp) | 0 pp | 0.5 pp | 1.0 pp (shipped) | 2.0 pp |
| --- | --- | --- | --- | --- | --- |
| Dengue | -0.13 | S | S | S | S |
| Acute Respiratory Infection | 0.81 | H | H | S | S |
| Influenza-like Illness | 0.10 | H | S | S | S |
| Tuberculosis | 0.15 | H | S | S | S |
| Hand Foot & Mouth Disease | -0.19 | S | S | S | S |
| Measles | -0.48 | S | S | S | S |
| Leptospirosis | 0.19 | H | S | S | S |


The single named policy constant remains `dashboard/config.py::HYBRID_MIN_WAPE_GAIN_PP = 1.0`. `run_hybrid_pipeline` reads this constant for WAPE selection and uses strict lower MAE only when WAPE is undefined. UI and export consume the result's threshold metadata. The existing explanatory 1.00-point UI/documentation text is not another mechanism or configurable value. The expert consultation remains **deferred, not resolved**. The sensitivity results alone are not an instruction to optimize the rule on the final holdout.

## Item 4: separate real and synthetic findings

Source: `C:/Users/redlo/Downloads/Antipolo_Disease_Surveillance_2016-2025.xlsx`.
Its Notes sheet identifies RESU, DOH Center for Health Development?CALABARZON, PIDSR, Antipolo City, morbidity weeks 1?53, 2016?2025. It states the workbook was transcribed from provided tables/PDFs. This identifies the local source requested; the underlying original disease-specific PDF transcription was not independently authenticated in this handoff. The different top-five-disease PDF in the project was not substituted for this workbook.


Workbook SHA-256: `c8e90c7e040e0c5e5b4676bbe6e26485e6921054d89f684f4f3768ae43cb73ff`.


The unchanged upload parser maps Measles-Rubella to Measles, aggregates weekly cells using the ISO week's Thursday, assigns non-ISO week 53 to December, and excludes total/notes rows. Notes is skipped because it has no morbidity-week table. There were no validation issues. Each disease has 120 monthly observations, January 2016?December 2025. Blank weekly cells are skipped by the existing parser; complete monthly coverage does not prove every weekly report is complete. `source_checks.py` independently summed numeric week rows and matched all 30 disease/year totals to parsed monthly totals. No data was imputed or supplemented with sample records.

All comparisons use the same pipeline and final January?December 2025 holdout (108 training months); selection uses earlier 2023 and 2024 folds (84 and 96 training months). WAPE is `100 * sum(abs(actual - forecast)) / sum(abs(actual))`, independently recomputed without the metric helper from each saved selected/naive prediction array. No average across real and sample data is used.

### Real Antipolo workbook


| Disease | Selected holdout WAPE | Seasonal-naive holdout WAPE |
| --- | --- | --- |
| Dengue | 25.17% | 34.90% |
| Leptospirosis | 67.08% | 55.86% |
| Measles | 162.58% | 50.00% |


**The adverse finding extends to real data:** seasonal naive beats the selected model on Leptospirosis and Measles. Dengue selects Hybrid and beats naive; the other two select SARIMA-only. All three holdout base fits used SARIMA, so this table is not explained by a holdout fallback. Measles has a production NNAR convergence warning, retained in the evidence; that production warning cannot explain the separate base-only holdout score.

The real Dengue Hybrid WAPE is 25.17%, versus SARIMA-only 27.36% and naive 34.90%. This is one observed disease/window where the neural correction adds value. Measles totals are 1,519 in 2019, 55 in 2024, and 110 in 2025; Leptospirosis totals are 16 in 2022, 124 in 2023, 87 in 2024, and 111 in 2025. These are concrete changes and low-count contexts, not proof of a particular epidemiological cause. Leptospirosis has one zero month in 2025; WAPE includes that month's absolute error. The unfavorable real scores cannot be dismissed as a synthetic-data artifact.

### Synthetic sample, independently rerun


| Disease | Selected holdout WAPE | Seasonal-naive holdout WAPE |
| --- | --- | --- |
| Dengue | 27.02% | 22.67% |
| Acute Respiratory Infection | 46.50% | 18.80% |
| Influenza-like Illness | 45.91% | 30.14% |
| Tuberculosis | 24.87% | 30.06% |
| Hand Foot & Mouth Disease | 38.29% | 21.50% |
| Measles | 46.95% | 30.51% |
| Leptospirosis | 55.26% | 30.14% |


This reproduces six naive wins out of seven. At the unchanged 1.00-point default, **all seven selected candidates are SARIMA-only**; Tuberculosis is the sole selected-model win against naive.

### Checked explanation: generator structure

Read `dashboard/data/mock_data.py::generate_fallback_data` and the configuration weights. The seed is fixed at 2025. Every calendar month uses the same yearly repeating seasonal weight (0.50?1.65), multiplied by a fresh Normal(110,18) draw, then by fixed disease shares and independent Uniform(0.75,1.30) disease noise, rounded to cases. A common factor of 0.32 applies only in 2020?2022. There is no modeled trend outside that deterministic reduction and no engineered nonlinear lag signal for NNAR. The generated normal/noise draws are not identical year to year; copying last year is not an exact oracle.

The final 2024?2025 comparison stays in the same unreduced seasonal regime, making a previous-year template well matched to the fixture. Full-series lag-12 correlations range from 0.595 to 0.677 (including the reduction/recovery period). This supports a repeated seasonal structure; it does not establish that the same fixed structure describes real epidemics.

As a diagnostic only, average each calendar month across pre-2025 non-reduction years (2016?2019 and 2023?2024), excluding the known fixture reduction using generator knowledge. This was not offered as a selectable model or as an independently tuned prospective result:


| Disease | Seasonal average WAPE | Copy-last-year WAPE |
| --- | --- | --- |
| Dengue | 16.75% | 22.67% |
| Acute Respiratory Infection | 22.12% | 18.80% |
| Influenza-like Illness | 20.24% | 30.14% |
| Tuberculosis | 11.15% | 30.06% |
| Hand Foot & Mouth Disease | 18.38% | 21.50% |
| Measles | 27.68% | 30.51% |
| Leptospirosis | 19.18% | 30.14% |


The diagnostic average beats naive on six of seven diseases. Therefore the evidence supports ?the fixture favors stable seasonal templates,? not ?copying last year is trivially optimal.? No generator changes were made.

### Checked explanation: fitting noise versus generalization

Refit the existing SARIMA and NNAR on the 108-month training window. Measure both training fits on identical dates after dropping 24 initialization months and intersecting NNAR fitted dates. Compare to their same-origin 12-step holdout errors. These are one-step in-sample fits versus recursive multi-step forecasts: a gap is suggestive of generalization limitations, not a controlled proof that excess parameter fitting is the sole cause.


| Disease | Training base WAPE | Training hybrid WAPE | Holdout base WAPE | Holdout hybrid WAPE |
| --- | --- | --- | --- | --- |
| Dengue | 29.90 | 25.89 | 27.02 | 23.92 |
| Acute Respiratory Infection | 32.07 | 31.33 | 46.50 | 52.85 |
| Influenza-like Illness | 29.99 | 28.59 | 45.91 | 46.14 |
| Tuberculosis | 39.02 | 37.80 | 24.87 | 28.33 |
| Hand Foot & Mouth Disease | 35.81 | 35.65 | 38.29 | 41.14 |
| Measles | 35.85 | 34.56 | 46.95 | 45.73 |
| Leptospirosis | 30.41 | 30.07 | 55.26 | 54.10 |


NNAR improves in-sample WAPE on all seven, but worsens holdout WAPE on four (Acute Respiratory Infection, Influenza-like Illness, Tuberculosis, Hand Foot & Mouth Disease). This is consistent with learning noise or unstable residual patterns. It is not systematic harm across all diseases, and cannot be the sole explanation for the selected-model result because the default selected model excludes NNAR in all seven sample series.

Reading `run_arima` also shows a fixed differenced seasonal specification with a constant, not a fit that knows the fixture's deterministic reduction regime. `run_nnar` uses three residual lags, four hidden units, alpha=10, and recursive forecast inputs. A regime mismatch, fixed specification, parameter estimation, and forecast recursion are plausible contributors. Establishing their causal shares would require additional controlled experiments/multiple seeds or real rolling evaluations; no such causal claim is made here.

### Checked explanation: training-window fairness and structural advantage

Both methods forecast the exact same 2025 months using information available by December 2024, with no holdout access. Using fewer observations is a valid property of a benchmark, not leakage or an unfair scoring horizon. The long training window contains the earlier reduction and recovery; naive ignores older regimes, which can be beneficial here but can fail when the next year changes regime.

Diagnostic refits below retain the same holdout and unchanged model functions, but vary only the training window. These do not reselect production models or change the shipped 108-month comparison.


| Disease | Base WAPE: 36 months | Base WAPE: 60 months | Base WAPE: 108 months | Naive WAPE (all windows) |
| --- | --- | --- | --- | --- |
| Dengue | 32.77 | 17.97 | 27.02 | 22.67 |
| Acute Respiratory Infection | 36.20 | 40.95 | 46.50 | 18.80 |
| Influenza-like Illness | 29.33 | 23.04 | 45.91 | 30.14 |
| Tuberculosis | 29.36 | 34.51 | 24.87 | 30.06 |
| Hand Foot & Mouth Disease | 43.07 | 36.13 | 38.29 | 21.50 |
| Measles | 53.33 | 27.26 | 46.95 | 30.51 |
| Leptospirosis | 24.11 | 41.53 | 55.26 | 30.14 |


The 36-month fits use SARIMA; all 60-month fits fall back to Holt-Winters on convergence failure; the 108-month fits use SARIMA. Thus the 60-month improvement cannot be attributed to history length alone. Neither shortening history nor retaining more history universally solves the problem. Full hybrid-window scores and warnings are retained in `investigation.json`.

The already-used earlier folds provide another diagnostic: naive beats base-only on six of seven 2023 windows, with naive WAPE roughly 65?73% during recovery from the fixture's reduction; on 2024 it wins only two of seven. These folds informed selection and are not additional independent test sets. They show that the six-of-seven 2025 result is not a universal ordering even within this one fixture.

### What the evidence supports for thesis claims

The implemented selection/evaluation workflow is reproducible and exposes when a simple benchmark wins. It does **not** establish general superiority of the hybrid, general superiority of the selected candidate, or a guarantee against SARIMA on unseen periods. The narrow positive result is Hybrid improving real Dengue's 2025 holdout against both SARIMA and seasonal naive in this workbook. ?Outperforms under conditions X and Y? is not yet a validated rule: one favorable disease/window cannot identify reliable general conditions.

For a limitations discussion, the evidence to represent is: the sample has fixed annual weights and a hard-coded temporary reduction; results depend on window/regime and fitting behavior; training improvements sometimes fail to generalize; real naive wins on two of three diseases; only one final holdout was independently evaluated per disease; and the workbook is a transcription whose source/calendar assumptions remain relevant. Broader prospective or rolling-origin real-data evaluation is needed before asserting dependable hybrid value. This is evidence guidance, not replacement thesis prose.

## Current thesis-change ledger: all remaining author decisions

| Item | Current state / verified evidence | Remaining author decision or manuscript action |
| --- | --- | --- |
| Two distinct references | Resolved in code/UI/docs; shared neutral cards and tests | Supply/verify manuscript citation and original dataset/method for the fixed historical MAPE; align manuscript terminology with the exact copy above. Historical provenance was not independently supplied or validated. |
| Upload-defined disease catalog | Resolved: explicit gate, full table, registered HTTP Malaria reproduction, CSV/XLSX/converted-category tests | Describe upload-defined labels with explicit user confirmation, not a fixed whitelist. |
| 1.00-point materiality threshold | Deferred intentionally; single named constant unchanged; sensitivity table supplied | Expert consultation must decide whether to retain or change the value. No new value approved here. Update the manuscript with the eventual rationale. |
| Real-data benchmark weakness | Newly confirmed: naive wins Leptospirosis and Measles | Revise any general superiority claim; decide how to present the narrow real Dengue gain and unfavorable results. |
| Mock-generator realism | Diagnosed, not changed: fixed seasonal weights, seeded noise, reduction regime | Decide whether a future scope should redesign the fixture or add multi-seed experiments. It must not be presented as validation of real epidemiology. |
| Model specification/generalization | Mixed NNAR generalization; history/fallback sensitivity documented | Decide whether future model research, residual diagnostics, regime treatment, and broader real rolling evaluation are required. No model changes were authorized here. |
| Seasonal naive in production | Still diagnostic, consistent with current scope | Any decision to make it a selectable forecast is separate and remains with the author; do not imply selection considered it. |
| Guaranteed performance language | No active UI/README promise; historical changelog references describe removal | Remove any corresponding guarantee in manuscript. Selection-fold success does not guarantee holdout/future success. |
| Error-band interpretation | Existing historical maximum-error band retained; no new coverage validation | Align manuscript with historical calibration and unvalidated future coverage, rather than a proved 95% prospective interval. |
| Real-data provenance/category/calendar | Local workbook Notes reviewed; 30 totals reconcile; Measles-Rubella alias and week-53 handling retained | Confirm original transcription, combined-category terminology, and reporting-week convention in the thesis. No independent source-PDF authentication was performed. |
| Dependency reproducibility | Installed scientific/UI versions differ from repository pins; exact versions recorded in `evidence/runtime-check-2026-09-27.json` and `AGENT_HANDOFF.md` | Decide the supported reproducible environment before packaging/deployment; validate pins in isolation and rerun evidence if versions change. No dependency changes made. |
| UI visual acceptance | Component and HTTP checks pass; no live-browser screenshot inspection | Review rendered layout before presentation/deployment; this remains an explicitly unverified visual check. |

## Item 5: fresh verification

Command: `python -X utf8 -m pytest -v --tb=short` (stdout/stderr captured in `evidence/pytest-full.txt`). The warnings are ten Dash DataTable deprecation notices and one cache-directory permission warning. They are reported, not suppressed; no tests failed. Earlier successful-ingestion tests now explicitly confirm their staged candidates; new tests exercise unconfirmed behavior independently.

Per-file breakdown, counted from the actual PASSED lines:


| Test file | Passed |
| --- | --- |
| tests/test_app_contracts.py | 10 |
| tests/test_callbacks.py | 18 |
| tests/test_data_ingestion.py | 20 |
| tests/test_date_preprocessing.py | 9 |
| tests/test_modeling.py | 15 |
| tests/test_production_safety.py | 4 |
| tests/test_upload_confirmation.py | 9 |


Actual full command output:

```text
============================= test session starts =============================
platform win32 -- Python 3.13.3, pytest-9.1.1, pluggy-1.6.0 -- C:\Python313\python.exe
cachedir: .pytest_cache
rootdir: C:\Users\redlo\Downloads\Antipolo-dashboard
configfile: pyproject.toml
testpaths: tests
plugins: dash-4.2.0
collecting ... collected 85 items

tests/test_app_contracts.py::test_layout_contains_every_callback_component_id PASSED [  1%]
tests/test_app_contracts.py::test_app_import_wires_layout_and_callbacks PASSED [  2%]
tests/test_app_contracts.py::test_vercel_entrypoint_is_wsgi_app PASSED   [  3%]
tests/test_app_contracts.py::test_load_data_initializes_mock_data_without_upload PASSED [  4%]
tests/test_app_contracts.py::test_load_data_accepts_csv_as_authoritative_session_dataset PASSED [  5%]
tests/test_app_contracts.py::test_upload_summary_has_expected_keys_and_upload_grounded_disease_counts PASSED [  7%]
tests/test_app_contracts.py::test_refresh_preserves_existing_upload_summary PASSED [  8%]
tests/test_app_contracts.py::test_reset_replaces_upload_with_builtin_sample PASSED [  9%]
tests/test_app_contracts.py::test_aggregate_callback_returns_expected_output_shape PASSED [ 10%]
tests/test_app_contracts.py::test_dataset_signature_changes_when_upload_data_changes PASSED [ 11%]
tests/test_callbacks.py::test_prepare_hybrid_entry_computes_only_selected_disease PASSED [ 12%]
tests/test_callbacks.py::test_prepare_hybrid_entry_reuses_matching_cache PASSED [ 14%]
tests/test_callbacks.py::test_prepare_hybrid_entry_invalidates_old_dataset_cache PASSED [ 15%]
tests/test_callbacks.py::test_pipeline_failure_is_cached_as_safe_error PASSED [ 16%]
tests/test_callbacks.py::test_pipeline_validation_rejection_is_visible_to_user PASSED [ 17%]
tests/test_callbacks.py::test_render_hybrid_section_handles_unreadable_store PASSED [ 18%]
tests/test_callbacks.py::test_dropdown_status_icons_cover_lazy_warning_success_and_error PASSED [ 20%]
tests/test_callbacks.py::test_uploaded_diseases_drive_both_selectors_and_year_range PASSED [ 21%]
tests/test_callbacks.py::test_aggregate_charts_render_arbitrary_disease_names PASSED [ 22%]
tests/test_callbacks.py::test_forecast_chart_does_not_plot_selected_candidate_twice PASSED [ 23%]
tests/test_callbacks.py::test_forecast_and_backtest_labels_disclose_actual_fallback_tier PASSED [ 24%]
tests/test_callbacks.py::test_headline_includes_neutral_distinct_baselines_and_collapsed_diagnostics PASSED [ 25%]
tests/test_callbacks.py::test_technical_baselines_match_forecast_and_handle_undefined_scores PASSED [ 27%]
tests/test_callbacks.py::test_source_indicators_make_mixed_and_selected_source_visible PASSED [ 28%]
tests/test_callbacks.py::test_all_zero_selection_card_names_mae_fallback_instead_of_wape PASSED [ 29%]
tests/test_callbacks.py::test_forecast_export_contains_history_forecast_bounds_and_provenance PASSED [ 30%]
tests/test_callbacks.py::test_download_is_blocked_until_selected_forecast_is_cached PASSED [ 31%]
tests/test_callbacks.py::test_download_button_is_enabled_only_for_ready_selected_forecast PASSED [ 32%]
tests/test_data_ingestion.py::test_epi_week_to_month_normal_week PASSED  [ 34%]
tests/test_data_ingestion.py::test_epi_week_to_month_week_53_in_a_real_iso_53_week_year PASSED [ 35%]
tests/test_data_ingestion.py::test_epi_week_to_month_week_53_in_a_non_iso_53_week_year_falls_back_to_december PASSED [ 36%]
tests/test_data_ingestion.py::test_epi_week_to_month_week_54_still_raises PASSED [ 37%]
tests/test_data_ingestion.py::test_parse_surveillance_xlsx_happy_path PASSED [ 38%]
tests/test_data_ingestion.py::test_parse_surveillance_xlsx_fuzzy_sheet_name_match PASSED [ 40%]
tests/test_data_ingestion.py::test_parse_surveillance_xlsx_accepts_arbitrary_disease_sheet PASSED [ 41%]
tests/test_data_ingestion.py::test_parse_surveillance_xlsx_skips_sheet_without_weekly_header_visibly PASSED [ 42%]
tests/test_data_ingestion.py::test_parse_surveillance_xlsx_not_an_excel_file PASSED [ 43%]
tests/test_data_ingestion.py::test_validate_accepts_arbitrary_disease_names PASSED [ 44%]
tests/test_data_ingestion.py::test_validate_drops_blank_disease_names_with_visible_reason PASSED [ 45%]
tests/test_data_ingestion.py::test_validate_clips_negative_cases_to_zero PASSED [ 47%]
tests/test_data_ingestion.py::test_validate_drops_invalid_month_and_year PASSED [ 48%]
tests/test_data_ingestion.py::test_validate_reports_no_issues_when_data_is_clean PASSED [ 49%]
tests/test_data_ingestion.py::test_validate_discards_duplicate_observation_and_reports_it PASSED [ 50%]
tests/test_data_ingestion.py::test_date_range_gap_warning_distinguishes_absent_from_zero_case_months PASSED [ 51%]
tests/test_data_ingestion.py::test_server_rejects_upload_exceeding_max_content_length_cleanly PASSED [ 52%]
tests/test_data_ingestion.py::test_unicode_decode_error_returns_friendly_upload_message PASSED [ 54%]
tests/test_data_ingestion.py::test_csv_date_column_uses_selected_convention_and_monthly_aggregation PASSED [ 55%]
tests/test_data_ingestion.py::test_flat_xlsx_date_table_is_supported_after_pidsr_shape_fallback PASSED [ 56%]
tests/test_date_preprocessing.py::test_day_first_convention_resolves_ambiguous_numeric_dates PASSED [ 57%]
tests/test_date_preprocessing.py::test_month_first_convention_changes_ambiguous_date_interpretation PASSED [ 58%]
tests/test_date_preprocessing.py::test_text_month_iso_timestamp_and_excel_serial_are_supported PASSED [ 60%]
tests/test_date_preprocessing.py::test_iso_week_rows_are_aggregated_to_months PASSED [ 61%]
tests/test_date_preprocessing.py::test_textual_month_with_year_columns_is_supported PASSED [ 62%]
tests/test_date_preprocessing.py::test_invalid_dates_are_reported_and_removed PASSED [ 63%]
tests/test_date_preprocessing.py::test_pdf_converter_writes_canonical_csv_and_review_report PASSED [ 64%]
tests/test_date_preprocessing.py::test_doh_multiline_month_matrix_survives_page_break PASSED [ 65%]
tests/test_date_preprocessing.py::test_pdf_extraction_reports_age_ranking_and_missing_year_scope PASSED [ 67%]
tests/test_modeling.py::test_compute_metrics_perfect_prediction_is_zero_error PASSED [ 68%]
tests/test_modeling.py::test_compute_metrics_handles_zero_actuals_without_dividing_by_zero PASSED [ 69%]
tests/test_modeling.py::test_scoring_rejects_same_length_forecast_on_wrong_dates PASSED [ 70%]
tests/test_modeling.py::test_hybrid_forecast_clips_negative_combined_values_to_zero PASSED [ 71%]
tests/test_modeling.py::test_run_arima_uses_sarima_tier_on_well_behaved_series PASSED [ 72%]
tests/test_modeling.py::test_run_arima_short_series_skips_straight_to_holt_winters PASSED [ 74%]
tests/test_modeling.py::test_run_decomposition_reports_reason_when_too_short PASSED [ 75%]
tests/test_modeling.py::test_run_decomposition_succeeds_on_long_series PASSED [ 76%]
tests/test_modeling.py::test_run_nnar_degrades_gracefully_with_too_few_residuals PASSED [ 77%]
tests/test_modeling.py::test_run_nnar_produces_a_forecast_with_enough_residuals PASSED [ 78%]
tests/test_modeling.py::test_pipeline_raises_clearly_on_insufficient_history PASSED [ 80%]
tests/test_modeling.py::test_pipeline_selection_is_rolling_and_final_metrics_use_untouched_holdout PASSED [ 81%]
tests/test_modeling.py::test_pipeline_rejects_missing_months_instead_of_imputing_zero PASSED [ 82%]
tests/test_modeling.py::test_pipeline_data_source_detection PASSED       [ 83%]
tests/test_modeling.py::test_pipeline_result_survives_serialization_roundtrip PASSED [ 84%]
tests/test_production_safety.py::test_oversized_upload_is_rejected_before_parsing PASSED [ 85%]
tests/test_production_safety.py::test_corrupt_xlsx_has_a_bounded_user_message PASSED [ 87%]
tests/test_production_safety.py::test_legacy_xls_is_not_advertised_or_accepted PASSED [ 88%]
tests/test_production_safety.py::test_health_endpoint_is_lightweight_and_successful PASSED [ 89%]
tests/test_upload_confirmation.py::test_upload_cannot_activate_without_explicit_confirmation PASSED [ 90%]
tests/test_upload_confirmation.py::test_malaria_visible_in_full_confirmation_table_before_activation PASSED [ 91%]
tests/test_upload_confirmation.py::test_old_confirmation_click_does_not_approve_new_upload[None] PASSED [ 92%]
tests/test_upload_confirmation.py::test_old_confirmation_click_does_not_approve_new_upload[reset-session-data] PASSED [ 94%]
tests/test_upload_confirmation.py::test_old_confirmation_click_does_not_approve_new_upload[upload-csv] PASSED [ 95%]
tests/test_upload_confirmation.py::test_rejected_replacement_clears_previous_candidate_and_preserves_active PASSED [ 96%]
tests/test_upload_confirmation.py::test_upload_before_initial_load_keeps_sample_active PASSED [ 97%]
tests/test_upload_confirmation.py::test_xlsx_and_pdf_icd_categories_require_confirmation PASSED [ 98%]
tests/test_upload_confirmation.py::test_registered_http_flow_requires_confirmation PASSED [100%]

============================== warnings summary ===============================
tests/test_app_contracts.py: 1 warning
tests/test_upload_confirmation.py: 9 warnings
  C:\Users\redlo\AppData\Roaming\Python\Python313\site-packages\dash\development\base_component.py:139: DeprecationWarning:
  
  
  The dash_table.DataTable will be removed from the builtin dash components in a future major version.
  We recommend using dash-ag-grid as a replacement. Install with `pip install dash[ag-grid]`.

..\..\AppData\Roaming\Python\Python313\site-packages\_pytest\cacheprovider.py:469
  C:\Users\redlo\AppData\Roaming\Python\Python313\site-packages\_pytest\cacheprovider.py:469: PytestCacheWarning:
  
  could not create cache path C:\Users\redlo\Downloads\Antipolo-dashboard\.pytest_cache\v\cache\nodeids: [WinError 5] Access is denied: 'C:\\Users\\redlo\\Downloads\\Antipolo-dashboard\\.pytest_cache\\v\\cache'

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
====================== 85 passed, 11 warnings in 19.83s =======================
```


## Reproduction and evidence files

- `python -m evidence.investigate`: runs the actual pipeline for all seven sample and three real diseases, independent WAPE assertions, read-only threshold sensitivity, training/holdout diagnostics, and window checks. Results: `evidence/investigation.json`, `evidence/investigation-run.txt`.
- `python -m evidence.source_checks`: reconciles workbook totals and computes the diagnostic seasonal average. Results: `evidence/source-checks.json`; canonical parser output is `evidence/real-monthly.csv`.
- `python -X utf8 -m evidence.reproduce_upload`: registered Dash HTTP flow; actual output is `evidence/malaria-reproduction.txt`.
- `python -X utf8 -m pytest -v --tb=short`: complete suite; actual output is `evidence/pytest-full.txt`.

Numerical environment (saved with the results):

{
  "python": "3.13.3",
  "versions": {
    "numpy": "2.3.4",
    "pandas": "2.3.3",
    "scipy": "1.16.3",
    "statsmodels": "0.14.6",
    "scikit-learn": "1.4.0"
  }
}

## Final reference/guarantee inventory

Actual command: `rg -n -i '32\.22|never\s+worse|HISTORICAL_REFERENCE_MAPE' dashboard tests README.md ARCHITECTURE.md CHANGELOG.md THESIS_READINESS.md`.
This inventories the entire application, tests, README, architecture, changelog, and this handoff before appending this inventory (to avoid self-recursion). The inventory log and this embedded copy necessarily repeat those matches. `evidence/` contains investigation numbers and raw logs rather than additional UI claims.

The runtime figure is defined once in config, formatted by `_baseline_cards`, and used in both forecast and technical-model cards. README and architecture explain its separate provenance. Test literals assert its display. Remaining performance-guarantee phrases occur only in the historical changelog's explanation of the removed guarantee; no current code/UI/README guarantee was found. The changelog's old baseline-removal entry is preserved as history and explicitly superseded by its new 2026-09-26 entry.

```text
ARCHITECTURE.md:339:**Historical reference MAPE: 32.22%** is a fixed external/thesis reference,

README.md:213:**Historical reference MAPE: 32.22%** is a fixed external/thesis reference,

CHANGELOG.md:29:- The README promised that auto-selection made the shipped forecast "never worse

CHANGELOG.md:87:  Corrected the README by removing the impossible "never worse" guarantee.

CHANGELOG.md:154:  holdout to replace the fixed, unproven 32.22% MAPE reference. It is not a

tests\test_callbacks.py:244:    assert "32.22%" in rendered

tests\test_callbacks.py:274:    assert '32.22%' in technical and 'N/A / N/A' in technical

dashboard\callbacks\view_callbacks.py:39:from dashboard.config import DISEASES, HOLDOUT_MONTHS, FORECAST_MONTHS, HISTORICAL_REFERENCE_MAPE

dashboard\callbacks\view_callbacks.py:192:        metric("Historical reference MAPE", f"{HISTORICAL_REFERENCE_MAPE:.2f}%",

dashboard\config.py:52:HISTORICAL_REFERENCE_MAPE = 32.22  # external/thesis reference figure, not computed from the active dataset; see thesis manuscript for source

THESIS_READINESS.md:19:- Label: **Historical reference MAPE**; value: **32.22%**.

THESIS_READINESS.md:29:HISTORICAL_REFERENCE_MAPE = 32.22  # external/thesis reference figure, not computed from the active dataset; see thesis manuscript for source

THESIS_READINESS.md:38:**Historical reference MAPE: 32.22%** is a fixed external/thesis reference,

```

Changed Python modules and new evidence scripts also passed a targeted `python -m pyflakes` check (exit 0, no diagnostics).

## 2026-09-27 operational handoff update

Detailed receiving-agent context and process explanations are in [AGENT_HANDOFF.md](AGENT_HANDOFF.md). The local server was started at http://127.0.0.1:8050 with debug disabled. Health, page, layout, and dependency endpoints responded successfully; a live HTTP forecast request returned twelve sample Dengue predictions, SARIMA-only selection, WAPE 27.018472980905077%, and both reference cards. See `evidence/runtime-check-2026-09-27.json`. This does not replace live-browser visual inspection, rerun the full suite, or alter the numerical investigation. The decision ledger above remains the single current author-decision list.
