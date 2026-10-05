# Weekly surveillance system — operational contract

The research objective is weekly reportable infectious disease case counts among individuals aged **5–19 in Antipolo City**, using **confirmed-only CESU/PIDSAR** surveillance. FHSIS is contextual/reference material, not an equivalent modeling source. All-age, unverified, or out-of-scope sources remain usable as **Technical / Retrospective Evaluation**. Synthetic datasets are **Synthetic / Demo Data** and cannot supply thesis evidence. Measles and Measles-Rubella retain distinct source labels.

## Use the application

Run `python app.py`, then open the displayed local URL. The application starts without active data. Open **Data**, choose a CSV/XLSX, and wait for automatic file preparation. The **Review Data Transformation** popup compares original and prepared data, explains mappings and warnings, and offers **Confirm & Use Data** or **Cancel**. Ambiguous layouts use column dropdowns with sample values. Neither upload nor preparation replaces active data. Confirmation returns to Overview. The demo button also stages data for review. Reset clears the active context, retaining lifecycle history in the browser session.

The sections are Overview, Forecast, Historical Trends, Data, and About the Model. Overview presents the current source, selected disease, complete week, direction, data status and eligibility. Forecast emphasizes Hybrid SARIMA–NNAR, its separate SARIMA-only comparison, MAE/WAPE, a provisional range, and cautious interpretation. The display ranges are 4, 13, 26 or 52 weeks from one forecast path. Detailed diagnostics and all four metrics appear under About the Model → Advanced Details, collapsed by default. Historical range filters use reporting year/week to avoid guessing calendar dates.

## Structured input

These four fields are required **internally**, not as mandatory original upload headings:

```csv
disease,year,morbidity_week,case_count
Measles,2025,1,0
Measles,2025,2,
Measles-Rubella,2025,1,4
```

This illustrates the normalized structure, not real surveillance data. Counts must be non-negative integers; blank counts remain null. Reporting years must be integers from 1900 through 9999 and weeks integers from 1 through 53. Duplicate disease/year/week keys prevent activation. Label case/whitespace inconsistencies are reported and never silently normalized. PDF parsing is not part of the operational model path.

Source recognition accepts canonical or aliased long-table headings such as Diagnosis, Reporting Year, Week No and Total Cases. Each XLSX worksheet is inspected independently, including header rows following a title/preamble. Named disease sheets can supply disease hints. The historical layout with Morbidity Week down rows and reporting years across columns is unfolded directly into weekly records, including blank cells and week 53. A cross-year total column is not counted again; explicitly named total rows and empty rows are excluded from model observations but retained and explained in the transformation history. Duplicate year columns retain both counts and trigger duplicate-observation validation.

Unknown/ambiguous mappings ask for user selection rather than rejecting a readable file for lacking internal column names. One source column cannot supply two required fields. A disease-column/worksheet-name conflict requires an explicit choice. Generic names such as Sheet1 do not establish a disease. User-supplied disease/year constants are marked as declarations in the history. Known month/quarter columns cannot be mapped to morbidity week; monthly totals are never disaggregated into invented weekly records.

The review retains original file identity (SHA-256), worksheet, source header names, source rows and counts, prepared records, mapping choices, unused columns, excluded total/empty rows and warnings. **View Transformation Details** reopens the same evidence after activation. Tables preview up to eight rows per side, with controlled scrolling. Cancel and Close are explicit; Escape/backdrop clicks do not dismiss the review. Detailed evidence exports include transformation history, and CSV includes transformation provenance.

Optional metadata may be supplied at dataset or row level. Uniform, fully populated row metadata is resolved into dataset context; conflicting or incomplete metadata prevents eligibility as appropriate. Original row values remain available. `population` accepts `5–19` or `5-19`; `case_classification` must establish `confirmed`; `location` must establish `Antipolo City`; `dataset_type` must establish `real` for thesis eligibility. Other/unestablished classifications and populations remain technical. Mixed real/synthetic row classifications prevent activation.

The internal metadata structure supports `source_system`, `source_file`, `provenance`, `source_date`, `date_extracted`, `dataset_version`, `notes`, `reporting_status`, `approved_diseases`, `year_lengths`, and `weekly_protocol`. The normal UI has no JSON editor. Optional source-information dropdowns/text fields collect missing population, classification, source, reporting status, dataset type, location and source reference. Optional per-year calendar dropdowns start at Not specified. Established source facts are displayed rather than silently overwritten. Source assertions and references are not independently authenticated. Upload time and file identity are recorded automatically; population, confirmed status, source system and completeness are not inferred from workbook shape.

`reporting_status` is conservative: only `complete` counts enter training. `incomplete`, `provisional`, blank and unknown statuses remain visible but are excluded. Row status overrides dataset status. A dataset-level `complete` declaration should only be used when supported for all rows without explicit overrides.

`year_lengths` maps source reporting years to 52 or 53, for example `{"2025": 53}` **only if that is established by the source calendar**. ISO/calendar-week assumptions are not substituted. A supplied week 53 is preserved even when it conflicts with metadata; the conflict must be resolved before activation. Unknown year boundaries prevent constructing a multi-year training index. If future year lengths are unknown, a forecast can still carry 52 horizon offsets, but unresolved year/week labels stay null, carry a warning, and cannot be issued as a reconcilable prospective snapshot.

## Missingness and eligibility

Missing weeks are represented as missing positions in the model sequence, without fabricating source rows. Explicit zero cases remain zero. Blank counts remain missing. Gaps and exact affected weeks are listed and exported. Gaps alone do not block activation or modeling. SARIMAX can use its state-space missing-observation handling; this is explicitly configured and does not supply invented observations. NNAR uses only complete lag windows at their actual weekly positions. It never drops missing residuals and compresses the time axis. If usable windows are insufficient, Hybrid is unavailable while a successful SARIMA-only forecast remains separately available.

Thesis eligibility requires established population, location, confirmed classification, real weekly data, CESU/PIDSAR source/provenance, approved disease scope, valid keys, and no unresolved duplicates/label errors. The metadata `weekly_protocol` must include `approved: true`, an `approval_reference`, and an approved positive `minimum_complete_weeks`; each disease must meet that history requirement. With gaps, `gap_evaluation_approval` must document their formal-evaluation treatment. With week 53, `week53_approval` is required. These gates do not claim that an adviser has already approved any protocol.

Dataset eligibility and output eligibility are separate. An otherwise eligible dataset run with an unapproved model configuration produces technical outputs. No metric combines populations, datasets, synthetic and real evidence, or evaluation contexts.

## Model protocol — pending until explicitly supplied

The default is **Exploratory Weekly Configuration v0.1 ? Technical / Retrospective Evaluation Only**, authorized in Decisions 44?45. It installs the exact 16 candidates in `dashboard/weekly/protocol.py`, seasonality 52, NNAR lags 1/2/3/4/52, 3 hidden nodes, 2,000 NNAR iterations, seed 42, minimum 156 usable training observations, and a final-52-position holdout. Missing values use state-space handling; valid week 53 stays in sequence. Final adviser approval is not implied. Administrators may override via `WEEKLY_MODEL_CONFIG`; an explicitly empty/incomplete override still fails transparently.

Documented implementation safeguards for unspecified details: no trend, 53-position residual burn, at least 52 complete residual training examples, residual diagnostic lag 52, SARIMA limit 300 iterations, and existing ReLU/standard-scaler/LBFGS/alpha=1 NNAR behavior. These are technical choices, not final statistical rules. The 156-observation minimum applies independently to each fit, including the pre-holdout training window.

Administrators may separately set `WEEKLY_RESEARCH_CONFIG` to a documented study-requirements JSON file. Only `approved_diseases` and `weekly_protocol` are allowed there. It cannot inject population, case classification, completeness or other unknown source facts. Without documented study requirements, thesis eligibility remains pending. Configuration files are operator-managed research records, not proof of actual adviser approval.

The schema is in `dashboard/weekly/model.py::PENDING_CONFIG`:

| Field | Meaning |
| --- | --- |
| `version`, `approved`, `approval_reference` | Explicit protocol identity and documented approval status |
| `candidates` | Permitted objects with integer `order: [p,d,q]`, `seasonal_order: [P,D,Q,s]`, optional statsmodels `trend` |
| `nnar_lags` | Explicit positive weekly residual lag offsets; no monthly inheritance |
| `hidden_nodes`, `minimum_residual_examples` | Explicit network size and usable-window requirement |
| `minimum_training_weeks`, `residual_burn` | Complete observation requirement and initialization exclusion |
| `diagnostic_lag` | Explicit ACF/PACF and residual diagnostic lag |
| `holdout_weeks` | Null = no evaluation; explicit 1–52 = chronological retrospective holdout, not an approved final study design |
| `missing_policy` | `state_space` or explicit `reject`; no imputation option |
| `week53_policy` | `pending` or explicitly chosen `preserve_sequence`; no merge/remap option |
| `maxiter`, `nnar_maxiter`, `alpha`, `seed` | Replaceable numerical fitting controls |
| `uncertainty_method` | Currently `training_residual_rmse`; provisional |

The 64-candidate limit is an execution safeguard, not a statistical search grid. Seasonal period 52 and the 52-position holdout are explicitly authorized exploratory choices; they do not resolve calendar variability or establish final methodology. Test fixtures contain artificial configurations solely to verify code and do not establish a recommended or approved protocol.

Each model run fits the explicitly permitted SARIMA candidates and records convergence, AIC, fitted parameters and residual diagnostics. ADF and ACF/PACF are descriptive training-window diagnostics; they do not silently expand the candidate set. On gapped data those diagnostics are explicitly unavailable rather than computed on compressed observations. Candidates use the configured common likelihood burn. The lowest-AIC valid SARIMA is the separately labeled comparison. The Hybrid attempts NNAR on candidate residuals in AIC order, using only candidates in that supplied mechanism. If every Hybrid attempt fails, status is **Hybrid unavailable** with diagnostics. It is never replaced, interpolated or relabeled from SARIMA-only.

SARIMA + NNAR residual forecasts are clipped at zero; neither source counts nor evaluation observations are altered. A complete run creates **52 weekly forecast points**. The view slider only slices this same result; it does not call training. Cache keys include the entire dataset content and metadata, source identity, population, classification, frequency, disease, time coverage, full model configuration and implementation version. Activation invalidates the current result. Cache storage is browser-session scoped.

## Evaluation and uncertainty

Retrospective holdout fits only pre-holdout observations. Both models use the exact same holdout positions and finite actual-value mask; missing actuals are counted explicitly. Candidate selection, scalers and NNAR are fit within that training window. No future residuals enter recursive prediction. Weekly rolling/fold/origin designs remain pending; this revision provides a configurable single chronological holdout, not a claim that the final evaluation protocol is settled. Historical 2025 testing remains retrospective.

MAE and RMSE include zero-case observations. MAPE uses nonzero actuals only and reports `mape_n`; it is undefined when all actuals are zero. WAPE divides total absolute error by total absolute actual count and is undefined for a zero total. Missing or unavailable model evaluations are not fabricated. Main Forecast displays MAE/WAPE; Advanced Details and exports retain MAE/RMSE/MAPE/WAPE and evaluation-period coverage.

The displayed range is **Hybrid ± training SARIMA residual RMSE**, with the lower bound clipped to zero. This is provisional, uncalibrated error shading; it does not have claimed coverage and is not a formal 95% interval. Its calculation is disclosed in Advanced Details and exports. Replacing it with a validated method remains an explicit future protocol change.

## Historical display and exports

Weekly charts retain gaps and distinguish incomplete/unknown source points. Optional monthly/quarterly charts sum whole weekly counts by **source-established `week_start_date`**. Without those dates, the app explains why it cannot safely form calendar summaries. These summaries are display-only; missing/blank observations are not zero-filled, and potentially incomplete totals are labeled. Source week 53 remains unchanged.

CSV exports include observations and available forecasts, disease/year/week/horizon index, population/classification/source/type, dataset identity, model/config/version, model status and failure reason, warnings, eligibility context, metrics/evaluation period, and provisional range details. Complete evidence JSON also includes source records, quality details, full diagnostics and the lifecycle audit. CSV blank counts remain blank.

## Prospective support — not yet completed

The **Issue forecast snapshot** action stores original values, forecast issue timestamp, model/protocol, dataset and context in a SHA-256-addressed file created with exclusive creation. Reconciliation loads and verifies that original content hash, checks dataset context, matches disease/year/week, and records eventual actuals and per-horizon/model metrics. Incomplete actuals remain visible but unscored. Each reporting-delay revision creates a new file; no application operation overwrites the original forecast or an earlier revision.

Files live in `evidence/weekly_snapshots` or `WEEKLY_SNAPSHOT_DIR`. Deployments must provide durable writable storage and suitable access controls. This prototype has no authentication or external immutable-storage service; local administrators can edit files, with original snapshot tampering detected by hash verification. Researchers must verify that issue dates preceded outcomes and that protocols were approved before claiming prospective validation. The UI does not claim it is completed.

## Verification and historical boundaries

Run `python -m pytest -q` and `python -m pyflakes dashboard/weekly`. `tests/test_weekly.py` covers the weekly integrity and lifecycle rules, real SARIMA/NNAR execution on synthetic data, failure paths, 52 points, chronology, exports, and append-only reconciliation. `tests/test_transformation.py` covers source recognition, wide and long formats, ambiguities, explicit mappings, provenance, unknown facts, review/activation/cancellation, calendar declarations and study/source isolation. Existing monthly tests are retained as historical regressions; importing their callback modules during tests is not evidence that those routes are served in normal startup.

`python tests/browser_revision39.py` runs the real Edge/Playwright workflow, using a local test server and an explicitly synthetic-only protocol fixture. Playwright may be installed locally with `python -m pip install --target .browser-tools playwright`; the script uses installed Microsoft Edge. Screenshots and interaction results are saved under `evidence/revision39`. This protocol is not installed as a production default and does not establish research methodology.

Normal `app.py` imports only `dashboard.weekly.ui` for its layout/callbacks. Earlier `dashboard/data`, `dashboard/modeling`, `dashboard/ui`, `dashboard/callbacks` modules remain preserved for historical evidence/regression use; the weekly code shares only the general metric calculation and upload size setting. Pre-weekly README, architecture and model-evaluation documentation are preserved under `docs/historical-pre-weekly`. Earlier handoffs/manuscript/audit/reconciliation files describe historical evidence, not the current operational contract. No seasonal-naive or fixed historical MAPE appears in the weekly UI. No epidemic-threshold feature is implemented.


## Revision 45 evidence and decisions

Completeness declarations require a CESU/source reference. Calendar declarations require a calendar reference. Blank counts may be individually marked confirmed zero, missing, corrected source value, or nonexistent week with evidence; nonexistent-week exclusion additionally requires blank week 53 in a documented 52-week year. Original rows and decisions are retained in transformation history and exported metadata. Re-preparation reapplies decisions. Source-supplied row statuses still take precedence over a dataset-level status.

Advanced Details includes MAE/RMSE/MAPE/WAPE for holdout prefixes 1?4, 1?13, 1?26, and 1?52, with scored/missing counts and identical actual positions for both models. Candidate records retain convergence, finite AIC where available, diagnostics, and failure reasons. See REVISION45_REPORT.md.
