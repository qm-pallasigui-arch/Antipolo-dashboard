# Weekly surveillance system — operational contract

The research objective is weekly reportable infectious disease case counts among individuals aged **5–19 in Antipolo City**, using **confirmed-only CESU/PIDSAR** surveillance. FHSIS is contextual/reference material, not an equivalent modeling source. All-age, unverified, or out-of-scope sources remain usable as **Technical / Retrospective Evaluation**. Synthetic datasets are **Synthetic / Demo Data** and cannot supply thesis evidence. Measles and Measles-Rubella retain distinct source labels.

## Use the application

Run `python app.py`, then open the displayed local URL. The application starts without active data. Open **Data**, choose a CSV/XLSX, and wait for automatic file preparation. The **Review Data Transformation** popup compares original and prepared data, explains mappings and warnings, and offers **Confirm & Use Data** or **Cancel**. Ambiguous layouts use column dropdowns with sample values. Neither upload nor preparation replaces active data. Confirmation returns to Overview. The demo button also stages data for review. Reset clears the active context, retaining lifecycle history in the browser session.

The sections are Overview, Forecast, Historical Trends, Data, and About the Model. Overview presents the current source, selected disease, complete week, direction, data status and eligibility. Forecast emphasizes Hybrid SARIMA–NNAR, its separate SARIMA-only comparison, final 52-week MAE/RMSE/MAPE and cautious interpretation. The display ranges are 4, 13, 26 or 52 weeks from one forecast path. Detailed diagnostics and all three metrics appear under About the Model → Advanced Details, collapsed by default. Historical range filters use reporting year/week to avoid guessing calendar dates.

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

## Decision 90 model protocol

The authoritative methodology is [the final specification](docs/FINAL_WEEKLY_IMPLEMENTATION_SPEC.md), supplemented by the user's 10 October 2026 shortlist-union and MAPE clarification. `dashboard/weekly/selection.py::approved_configuration` is the production default. `WEEKLY_MODEL_CONFIG` may supply the same protocol with adjusted numerical iteration limits or diagnostic lag; altered methodological fields are rejected. The old exploratory functions remain available only for historical tests/offline compatibility.

The fixed SARIMA grid contains 144 combinations: p,q in {0,1,2}; d,P,D,Q in {0,1}; seasonal period 52. Every candidate must converge with finite parameters, AIC, and forecasts. Whiteness diagnostics do not determine eligibility. Source-supported week 53 stays a separate chronological position; seasonal period 52 is an annual-seasonality approximation.

There are exactly three expanding 52-week validation windows followed by an untouched 52-position holdout. At least 156 initial calendar positions are required, so the sequence needs at least 364 positions. Missing counts remain missing and incomplete reports are excluded from fitting. Terminal complete-but-blank reports retain their calendar positions.

At each validation cutoff, the full SARIMA grid is fitted on that cutoff's history. Valid candidates within delta AIC 4 form a shortlist, bounded to 3–5 where possible (top three if needed). Take the union across the three shortlists, then independently refit every union candidate at every cutoff. Only candidates with valid forecasts and metrics in all three windows can enter ranking. No holdout values enter selection.

NNAR evaluates consecutive lag windows 3,6,12,26,52 and hidden node counts 2,3,5,8 for each valid union SARIMA configuration. Each window derives residuals from its own SARIMA refit. Only complete residual windows train the network, with at least 52 samples; exclusions are counted. Logistic hidden activation and linear output permit negative residual corrections. StandardScaler is fitted on the training lag matrix. Five deterministic initializations use seeds 42–46; the converged fit with lowest training loss is retained. Residual predictions recurse through all 52 future positions.

RMSE and MAE are averaged equally across three windows. MAPE is averaged equally over only windows containing nonzero actuals; its window and observation coverage are retained. If no window has applicable MAPE, rank on RMSE and MAE only and flag the omission. Otherwise rank on all three metrics. Equal metric values receive average ranks. Tie breakers follow the specification. Cross-window AIC tie-breaking uses the arithmetic mean of the three cutoff-specific AICs. NNAR simplicity uses parameter count, then lag window, then hidden nodes; remaining exact ties use deterministic order identity.

SARIMA-only and Hybrid winners are locked independently. Refit those configurations on all pre-holdout history and forecast the holdout once, then refit the same locks on the full eligible history for the operational 52-week path. Refit failure never chooses another configuration. Holdout scores and predictions remain separate from operational results. The four display horizons slice the same future path.

## Scoring and limitations

Official forecasts and scores use max(0, raw forecast). Hybrid clipping happens after raw SARIMA plus signed NNAR correction. Raw paths remain in detailed evidence. No residual weighting coefficient is applied; NNAR alpha is library L2 regularization only.

Both models use identical finite-actual scoring positions. RMSE/MAE include genuine zeros; MAPE excludes only zero actuals, with counts reported. Missing actuals are excluded from all metrics. WAPE is absent. Advanced Details includes 4/13/26/52-week holdout-prefix metrics and selection coverage.

No uncertainty band or interval is generated by the production protocol or displayed/exported by the dashboard. Recursive residual errors may accumulate with horizon. Results are retrospective evaluation, not completed prospective validation.

The supplementary DM field is retained with an explicit applicability state. This design produces one fixed-origin path across horizons 1–52, not repeated errors at a common horizon. No mixed-horizon DM variance/loss protocol was supplied or existed in the prior implementation; no statistic or p-value is invented. Its unavailable state does not affect selection.

The full selection is computationally intensive (432 screening SARIMA fits, up to 45 union refits, up to 4,500 NNAR initializations, plus final refits). Generation runs in a separate background process with a persistent queue/cache, progress polling, and cancellation. A persistent remote worker serves Vercel deployments. See [forecast jobs](docs/FORECAST_JOBS.md). No smaller statistical grid is substituted.

Dataset/model signatures include records, metadata, disease, configuration and implementation version. Stale cached results are rejected after dataset or protocol changes. The default study requirements record Decision 90 approval of the disease scope and missing/week-53 treatment, but never invent population, source reporting completeness, case classification, or calendar lengths.

## Historical display and exports

Weekly charts retain gaps and distinguish incomplete/unknown source points. Optional monthly/quarterly charts sum whole weekly counts by **source-established `week_start_date`**. Without those dates, the app explains why it cannot safely form calendar summaries. These summaries are display-only; missing/blank observations are not zero-filled, and potentially incomplete totals are labeled. Source week 53 remains unchanged.

CSV exports include observations and available forecasts, disease/year/week/horizon index, population/classification/source/type, dataset identity, model/config/version, model status and failure reason, warnings, eligibility context, metrics/evaluation period. Complete evidence JSON also includes source records, quality details, full diagnostics and the lifecycle audit. CSV blank counts remain blank.

## Prospective support — not yet completed

The **Issue forecast snapshot** action stores original values, forecast issue timestamp, model/protocol, dataset and context in a SHA-256-addressed file created with exclusive creation. Reconciliation loads and verifies that original content hash, checks dataset context, matches disease/year/week, and records eventual actuals and per-horizon/model metrics. Incomplete actuals remain visible but unscored. Each reporting-delay revision creates a new file; no application operation overwrites the original forecast or an earlier revision.

Files live in `evidence/weekly_snapshots` or `WEEKLY_SNAPSHOT_DIR`. Deployments must provide durable writable storage and suitable access controls. This prototype has no authentication or external immutable-storage service; local administrators can edit files, with original snapshot tampering detected by hash verification. Researchers must verify that issue dates preceded outcomes and that protocols were approved before claiming prospective validation. The UI does not claim it is completed.

## Verification and historical boundaries

Run `python -m pytest -q` and `python -m pyflakes dashboard/weekly`. `tests/test_weekly.py` covers the weekly integrity and lifecycle rules, real SARIMA/NNAR execution on synthetic data, failure paths, 52 points, chronology, exports, and append-only reconciliation. `tests/test_transformation.py` covers source recognition, wide and long formats, ambiguities, explicit mappings, provenance, unknown facts, review/activation/cancellation, calendar declarations and study/source isolation. Existing monthly tests are retained as historical regressions; importing their callback modules during tests is not evidence that those routes are served in normal startup.

The historical `tests/browser_revision39.py` script records the earlier Edge/Playwright workflow, using a local test server and an explicitly synthetic-only protocol fixture. Playwright may be installed locally with `python -m pip install --target .browser-tools playwright`; the script uses installed Microsoft Edge. Screenshots and interaction results are saved under `evidence/revision39`. This protocol is not installed as a production default and does not establish research methodology.

Normal `app.py` imports only `dashboard.weekly.ui` for its layout/callbacks. Earlier `dashboard/data`, `dashboard/modeling`, `dashboard/ui`, `dashboard/callbacks` modules remain preserved for historical evidence/regression use; the weekly code shares only the general metric calculation and upload size setting. Pre-weekly README, architecture and model-evaluation documentation are preserved under `docs/historical-pre-weekly`. Earlier handoffs/manuscript/audit/reconciliation files describe historical evidence, not the current operational contract. No seasonal-naive or fixed historical MAPE appears in the weekly UI. No epidemic-threshold feature is implemented.


## Revision 45 evidence and decisions

Completeness declarations require a CESU/source reference. Calendar declarations require a calendar reference. Blank counts may be individually marked confirmed zero, missing, corrected source value, or nonexistent week with evidence; nonexistent-week exclusion additionally requires blank week 53 in a documented 52-week year. Original rows and decisions are retained in transformation history and exported metadata. Re-preparation reapplies decisions. Source-supplied row statuses still take precedence over a dataset-level status.

Advanced Details includes MAE/RMSE/MAPE for holdout prefixes 1–4, 1–13, 1–26, and 1–52, with scored/missing counts and identical actual positions for both models. Candidate records retain convergence, finite AIC where available, diagnostics, and failure reasons. See REVISION45_REPORT.md.
