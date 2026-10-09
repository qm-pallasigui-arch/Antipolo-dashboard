# Antipolo Infectious Disease Forecasting System
## Final Coding-Agent Implementation Specification

### Status

This document is the authoritative implementation handoff for the updated weekly forecasting pipeline.

It incorporates the finalized methodology decisions through **Decision 90** together with the previously approved dashboard/data workflow rules.

Do not silently reinterpret, simplify, substitute, or expand these rules. Where this document explicitly says a value remains implementation-defined, do not convert that into a new methodological assumption.

---

# 1. System Purpose and Research Scope

The application is a web-based infectious-disease forecasting dashboard for Antipolo City.

Primary research population:

- ages **5–19**
- city-wide school-aged individuals
- intended to support public-school preparedness
- does not imply cases were necessarily acquired in schools or that all cases are confirmed public-school enrollees

Primary diseases:

- Dengue
- Leptospirosis
- Measles

The software may also distinguish **Measles-Rubella** when the source dataset distinctly identifies it.

Primary modeling frequency:

- **weekly morbidity counts**

Primary research period:

- **2016–2025**

Primary source:

- CESU/PIDSAR disease-specific surveillance records

Secondary/reference source:

- FHSIS morbidity summaries

Research eligibility requires:

- weekly data
- ages 5–19
- confirmed-only cases
- valid disease identification
- valid year/week structure
- no unresolved duplicates
- no silent missing-to-zero conversion
- sufficient historical observations for the approved evaluation design

---

# 2. Production Data Architecture

## 2.1 Production modeling source

The forecasting engine must consume only the application's validated **Active Dataset**.

Production flow:

> Upload → Transform → Validate → Review → Confirm & Use Data → Active Dataset → Forecasting Engine

The model must not independently parse raw production files in a way that bypasses the Data module.

A standalone CSV/XLSX loader may remain only for:

- offline research
- development
- testing
- reproducibility utilities

It must not redefine or bypass the production rules for:

- missing values
- zero values
- Week 53
- provenance
- validation
- source transformation
- eligibility

---

# 3. Upload and Transformation Rules

Accepted source formats may include:

- CSV
- XLSX

The user is not required to upload an already canonical four-column file.

The application should transform supported source layouts into the internal weekly canonical structure.

Core internal fields include at minimum:

- disease
- reporting year
- morbidity week
- case count

Additional provenance/metadata should be preserved where available.

For multi-sheet workbooks:

- inspect worksheets
- allow Include / Exclude
- obvious Notes / README / Summary sheets may be suggested for exclusion
- included disease worksheets are reviewed independently
- worksheet name may provide disease identity
- wide week-by-year tables may be unfolded automatically
- ambiguous layouts require guided field mapping
- unresolved required fields must block activation

Do not use mock data to fill real uploaded datasets.

Do not combine synthetic/demo records with real research data.

---

# 4. Missing Values and Zero Counts

## 4.1 Genuine zero

A genuine zero-case week must remain exactly:

> `0`

Do not globally transform:

> `0 → 0.5`

Do not transform:

> `0 → 1`

Do not use another arbitrary replacement.

Zero is a real epidemiological observation and must remain unchanged in:

- source representation
- validated dataset
- model input

---

## 4.2 Missing is not zero

Missing/unreported values must remain distinguishable from genuine zero counts.

Never silently:

- fill missing with zero
- compress missing weeks out of the calendar
- substitute another case count without source evidence

---

## 4.3 Resolving historical blanks

Historical blank case counts must be resolved individually using source evidence as one of:

- confirmed zero
- missing/unreported
- corrected source value
- confirmed nonexistent reporting week under the source reporting calendar

No blanket autofill is allowed.

---

# 5. Weekly Calendar and Indexing

The modeling series must preserve true morbidity-week chronology.

Do not use simple row position as the time index when doing so would compress gaps.

A missing week must remain an explicit calendar gap.

Therefore:

- lag 1 = previous morbidity-week position
- lag 52 = actual 52-week separation
- not “52 available rows earlier”

All model preparation must preserve this distinction.

---

# 6. Week 53

Legitimate Week 53 observations must be preserved when supported by the documented CESU/source reporting calendar.

For a legitimate Week 53:

- preserve it as an additional chronological observation
- do not merge it into Week 52
- do not remap it
- do not discard it
- do not automatically convert it to zero

The SARIMA seasonal period remains:

> `m = 52`

This must be documented as a modeling approximation for annual weekly seasonality.

It must **not** be described as proof that every reporting year contains exactly 52 observations.

---

# 7. Recent Incomplete Reporting

Potentially incomplete recent reporting weeks must not be treated as complete observations for model training merely because they exist in the file.

Where recent periods are identified as incomplete:

- exclude them from training
- show a data-quality warning
- retain provenance
- do not silently modify their counts

A dataset-level:

> Historical reporting period complete

status may be used only when CESU/source documentation supports that conclusion.

Do not infer historical completeness solely from age of the data.

---

# 8. Modeling Architecture

Primary prediction model:

> **Hybrid SARIMA–NNAR**

Formal comparison model:

> **SARIMA-only**

Internal technical/audit benchmark:

> **Seasonal naive**

Seasonal naive must not appear as a normal user-facing forecast alternative.

It may remain available internally for:

- sanity checking
- technical auditing
- model-development diagnostics

The application must never silently fall back from Hybrid to another model while continuing to label the output Hybrid.

If Hybrid cannot be produced, show an explicit unavailable/failure state.

---

# 9. Overall Evaluation Structure

Use chronological evaluation only.

The approved formal structure is:

1. initial training history
2. three fixed internal validation windows
3. final untouched 52-week holdout
4. final retrospective evaluation
5. operational future refit and forecast

Do not randomly shuffle time-series observations.

---

# 10. Minimum Initial Training History

Before the first internal validation block, require at least:

> **156 weeks**

of initial training history.

If the disease series does not satisfy this requirement:

- formal thesis evaluation is unavailable
- do not shorten the approved validation design automatically
- do not silently reduce the required history

---

# 11. Internal Validation Design

Use exactly:

> **3 internal validation windows**

Each validation window is:

> **52 weeks**

Validation uses an:

> **expanding-window design**

For every validation window:

1. use all history available before that validation block
2. refit SARIMA using only that historical data
3. derive residuals only from that window-specific SARIMA fit
4. fit/evaluate NNAR from eligible residual data
5. evaluate forecasts on the following 52-week validation block

The training window grows for subsequent validation blocks.

Do not reuse a SARIMA fit trained using future validation observations.

---

# 12. Leakage Prevention

Every internal validation window requires its own SARIMA refit.

Do not:

- fit SARIMA on the full pre-holdout series and reuse those residuals for earlier validation windows
- derive NNAR training residuals from a model that had access to future validation observations

Residual generation must respect each validation cutoff.

This is mandatory.

---

# 13. Final Holdout

The final retrospective test set is fixed at:

> **the last 52 morbidity-week observations in the preserved chronological sequence**

The final holdout must remain untouched during:

- SARIMA selection
- NNAR selection
- hyperparameter ranking
- validation
- configuration tuning

Do not inspect final holdout performance to select the model.

---

# 14. SARIMA Seasonal Period

For all diseases:

> `m = 52`

The same seasonal period is used across the study.

Disease-specific SARIMA orders may differ.

---

# 15. Fixed SARIMA Candidate Grid

Use the same predefined candidate space across all diseases:

```text
p ∈ {0, 1, 2}
d ∈ {0, 1}
q ∈ {0, 1, 2}

P ∈ {0, 1}
D ∈ {0, 1}
Q ∈ {0, 1}

m = 52
```

Do not use a different candidate grid for Dengue, Leptospirosis, or Measles during final thesis evaluation.

Development-only fast/standard/full modes may exist internally, but the formal thesis evaluation must use the fixed grid above.

---

# 16. SARIMA Candidate Validity

For every candidate fit:

- attempt the predefined model fit
- check for successful fitting/convergence
- reject invalid/non-finite output
- reject invalid/non-finite forecasts
- record the reason for candidate failure

A failed candidate:

- must be logged
- must be excluded from AIC shortlisting
- must not be treated as a valid model

Continue evaluating remaining valid candidates.

If no valid SARIMA candidates remain:

- SARIMA-only is unavailable
- Hybrid is unavailable
- show an explicit failure state and reason

Do not fabricate a fallback SARIMA configuration.

---

# 17. SARIMA Residual Diagnostics

Residual diagnostics such as:

- Ljung–Box
- ADF
- KPSS
- related technical diagnostics already supported by the pipeline

may be retained and recorded.

Residual whiteness is:

> **diagnostic only**

Do not require intentionally non-white residuals.

Do not prefer a weaker SARIMA solely to create residual structure for NNAR.

A statistically acceptable SARIMA may proceed to Hybrid evaluation.

---

# 18. SARIMA AIC Shortlist

After removing invalid candidates:

1. identify the best valid AIC
2. include candidates with:

> `ΔAIC ≤ 4`

Shortlist constraints:

- minimum shortlist size: **3**
- maximum shortlist size: **5**

If fewer than 3 candidates satisfy ΔAIC ≤ 4:

> use the top 3 valid candidates by AIC

If more than 5 satisfy the rule:

> retain the best 5 by AIC

---

# 19. SARIMA Selection

AIC creates the shortlist.

AIC does **not** directly determine the final winner.

Shortlisted SARIMA candidates must be evaluated across the approved leakage-free validation windows.

For each candidate calculate arithmetic mean validation:

- RMSE
- MAE
- MAPE

across the three windows.

Rank candidates separately on:

- mean RMSE
- mean MAE
- mean MAPE

Calculate average rank across those three measures.

SARIMA selection priority:

1. lowest average validation rank
2. if tied: lower mean RMSE
3. if still tied: lower mean MAE
4. if still tied: lower mean MAPE
5. if still tied: lower AIC
6. if still tied: simpler SARIMA with fewer total AR/MA terms

The final selected SARIMA order may differ by disease.

---

# 20. SARIMA Missing-Observation Handling

Preserve missing weekly observations as explicit missing values.

Where supported by the SARIMA implementation, use state-space/Kalman-filter missing-observation handling.

Do not impute model-input case counts merely so SARIMA can fit.

Record:

- number of missing observations
- their effect on eligible scoring coverage where applicable

The source dataset remains unchanged.

---

# 21. NNAR Role

NNAR models the residual component remaining after SARIMA.

The conceptual model is:

> observed series = SARIMA linear/seasonal component + nonlinear residual component

NNAR predicts SARIMA residuals.

Its output must therefore remain capable of being:

- positive
- zero
- negative

Do not force the NNAR residual output itself to be non-negative.

---

# 22. NNAR Candidate Grid

Use fixed bounded NNAR candidates across diseases.

Residual lag-window candidates:

```text
3
6
12
26
52
```

Hidden-node candidates:

```text
2
3
5
8
```

The same candidate grid is used for all diseases.

Disease-specific winning NNAR configurations are allowed.

---

# 23. NNAR Lag Semantics

Each lag candidate represents a:

> **consecutive residual-history window**

Examples:

```text
lag window 3  = t-1, t-2, t-3
lag window 6  = t-1 through t-6
lag window 12 = t-1 through t-12
lag window 26 = t-1 through t-26
lag window 52 = t-1 through t-52
```

Lag positions must refer to actual morbidity-week positions.

Do not reinterpret these as merely the previous N available rows.

---

# 24. NNAR Missing-Lag Rule

NNAR may train only on:

> **complete residual lag windows**

For a candidate training sample:

- target residual must exist
- every required lag residual must exist
- all lag values must correspond to their exact morbidity-week positions

If any required residual is missing:

> skip that training sample

Do not:

- impute the residual
- replace it with zero
- compress the sequence
- use the next available observation as the required lag

Report the number of candidate training windows excluded due to incompleteness.

---

# 25. Minimum NNAR Training Samples

Each NNAR configuration requires at least:

> **52 complete residual training windows**

If fewer than 52 complete windows remain:

> mark that NNAR/Hybrid configuration unavailable due to insufficient complete residual windows

Do not fit it merely because the underlying library technically permits fitting on fewer samples.

---

# 26. NNAR Architecture

Hidden activation:

> **sigmoid / logistic**

Output activation:

> **linear**

The linear output is required because SARIMA residuals can legitimately be negative.

---

# 27. NNAR Training Reproducibility

Use a:

> **fixed documented random seed**

For every NNAR candidate configuration:

- train **5 times**
- use deterministic initializations derived from the fixed project seed
- retain the fit with the lowest training loss

Apply this same rule consistently across:

- diseases
- validation windows
- final refits

The exact project seed must be stable and recorded in model metadata.

Do not vary the seed opportunistically between runs.

If the existing codebase already defines the project's fixed seed, retain it unless explicitly changed at project level.

---

# 28. NNAR Multi-Step Forecasting

Use:

> **recursive residual forecasting**

Procedure:

1. predict residual for the next week
2. use that predicted residual as a required lag for subsequent steps
3. continue recursively until the requested forecast horizon is complete

Support the full:

> **52-week path**

Document as a limitation that recursive residual forecasts may accumulate error at longer horizons.

---

# 29. Hybrid Combination

The Hybrid model is strictly:

> **Hybrid forecast = SARIMA forecast + NNAR residual forecast**

Do not add a tunable weighting coefficient.

Do not use:

> SARIMA + α × NNAR

unless the methodology is formally changed in the future.

Do not average SARIMA and NNAR as independent case-count forecasts.

NNAR is a residual correction.

---

# 30. Forecast Non-Negativity

SARIMA and NNAR internals may mathematically produce negative values.

Preserve raw unconstrained values internally for diagnostics.

For official case-count forecast output:

```text
displayed_forecast = max(0, raw_forecast)
```

Apply this to:

- final Hybrid forecast
- user-facing SARIMA-only forecast

For Hybrid, clipping occurs:

> after SARIMA + NNAR residual combination

Do not independently clip NNAR residual corrections before combining them.

---

# 31. Metrics Use Clipped Forecasts

Official model evaluation must use the same non-negative forecast values that the user-facing system presents.

Therefore calculate official metrics from:

> `max(0, raw forecast)`

Raw forecasts may remain available internally for technical diagnostics.

Do not calculate the official thesis metrics from raw negative case forecasts while displaying clipped forecasts to users.

---

# 32. Approved Evaluation Metrics

Official primary evaluation measures are:

- **RMSE**
- **MAE**
- **MAPE**

Do not add WAPE to the official comparison unless separately re-approved.

This supersedes earlier drafts that included WAPE.

---

# 33. MAPE and Zero Actuals

When:

> actual case count = 0

ordinary MAPE is undefined.

For MAPE only:

- exclude zero-actual positions
- do not modify zero actuals
- do not add epsilon/0.5/1 replacements

Zero-actual positions remain included in:

- RMSE
- MAE

For every MAPE result, record:

- number of valid MAPE observations
- number of zero-actual observations excluded

---

# 34. Missing Actuals During Scoring

If the actual observed value is missing:

- exclude that position from RMSE
- exclude that position from MAE
- exclude that position from MAPE

Hybrid and SARIMA-only must be compared using the:

> **same valid scoring positions**

Do not give each model a different evaluation subset.

Record:

- total holdout/window size
- missing actuals excluded
- final RMSE/MAE scored count
- zero actuals excluded from MAPE
- final MAPE-valid count

---

# 35. Validation Metric Aggregation

For each candidate configuration:

1. calculate RMSE, MAE, MAPE for each validation window
2. compute the arithmetic mean of RMSE across the three windows
3. compute the arithmetic mean of MAE across the three windows
4. compute the arithmetic mean of MAPE across the three windows

These mean metrics are then used for model ranking.

Do not combine all validation observations into one unstructured metric if doing so changes the approved equal-window averaging rule.

---

# 36. Hybrid Model Selection

For each Hybrid candidate:

1. calculate mean validation RMSE
2. calculate mean validation MAE
3. calculate mean validation MAPE
4. rank all candidates separately on each metric
5. calculate each candidate's average of the three ranks
6. choose the lowest average rank

Do not use arbitrary metric weights.

---

# 37. Hybrid Tie-Breaking

If two or more Hybrid configurations have the same average rank:

1. lower mean RMSE
2. lower mean MAE
3. lower mean MAPE
4. if still tied, choose the simpler NNAR configuration

The implementation must make the definition of the final simplicity comparison deterministic and record the chosen configuration.

Do not resolve ties randomly.

---

# 38. Final Pre-Holdout Refit

After model selection using the three validation windows:

- lock the selected SARIMA configuration
- lock the selected NNAR configuration
- do not use the final holdout to change those configurations

Then refit:

- selected SARIMA-only
- selected Hybrid SARIMA–NNAR

using:

> all available eligible pre-holdout data

Forecast the untouched final 52-week holdout once.

Calculate official final:

- RMSE
- MAE
- MAPE

using the approved scoring rules.

---

# 39. Diebold–Mariano Test

Retain the Diebold–Mariano test as:

> **supplementary statistical comparison**

It is not the primary model-selection criterion.

Its principal use is comparing:

- Hybrid
- SARIMA-only

over a sufficiently long evaluation period, particularly the final holdout where appropriate.

Do not let the DM test override the approved validation-selection procedure.

---

# 40. Seasonal Naive Benchmark

Seasonal naive may remain as an internal technical benchmark.

It is not:

- the primary model
- the formal user-facing comparison
- a normal dashboard forecast option

Normal user-facing comparison remains:

> Hybrid SARIMA–NNAR vs SARIMA-only

---

# 41. Removal of Arbitrary Case-Strata Threshold

Remove any fixed evaluation split such as:

> low/high cases separated at 70

Do not use a hard-coded threshold of 70.

Official evaluation focuses on overall:

- RMSE
- MAE
- MAPE

unless a future research question explicitly justifies stratified evaluation.

---

# 42. Final Retrospective Evaluation

The final holdout represents:

> retrospective out-of-sample evaluation

It must not be described as completed prospective validation.

The system may report:

- final 52-week RMSE
- final 52-week MAE
- final 52-week MAPE
- supplementary DM comparison
- scoring coverage

All wording should avoid implying future deployment accuracy has already been prospectively validated.

---

# 43. Operational Future Forecast

After final retrospective evaluation:

1. keep the selected model configuration locked
2. do not rerun model selection based on final holdout results
3. refit the same locked configuration using the full eligible historical dataset
4. include the historical period previously serving as the holdout once its actual outcomes are known
5. generate a new operational future 52-week forecast

The retrospective holdout metrics remain unchanged.

Do not overwrite them with operational forecast results.

---

# 44. Forecast Horizon

Generate one continuous:

> **52-week future forecast path**

The dashboard supports views of:

- 4 weeks
- 13 weeks
- 26 weeks
- 52 weeks

These are slices of the same generated 52-week path.

Do not retrain or rerun model selection merely because the user switches from 4 to 13 to 26 to 52 weeks.

---

# 45. Horizon-Specific Historical Metrics

Main Forecast page:

show the primary final:

- 52-week RMSE
- 52-week MAE
- 52-week MAPE

Advanced Details may additionally show retrospective metrics at:

- 4 weeks
- 13 weeks
- 26 weeks
- 52 weeks

These are evaluation summaries, not separate fitted models.

---

# 46. Forecast Uncertainty

Do **not** currently display:

- residual-RMSE shading
- provisional uncertainty ranges
- pseudo confidence intervals
- unvalidated 95% prediction intervals

The uncertainty visualization has been removed until a formal validated uncertainty methodology is separately approved.

No uncertainty band should appear in the current integrated system.

---

# 47. Disease-Specific Winners

The framework is identical across diseases.

The following remain fixed across diseases:

- SARIMA candidate grid
- seasonal period m=52
- validation structure
- validation window lengths
- holdout length
- NNAR candidate grid
- activation architecture
- metric definitions
- selection rules
- scoring rules

However, the actual winning:

- SARIMA order
- NNAR lag-window size
- NNAR hidden-node count

may differ for each disease based on validation results.

This is expected and allowed.

---

# 48. Forecast Failure States

Do not silently substitute models.

Examples of explicit unavailable states include:

### No valid SARIMA
> Forecast unavailable — no valid SARIMA candidate remained after model fitting and validation checks.

### Insufficient NNAR windows
> Hybrid unavailable — insufficient complete NNAR residual windows.

### Insufficient history
> Formal forecasting evaluation unavailable — insufficient initial historical observations for the approved validation design.

### Missing active dataset
> Forecast unavailable — no validated Active Dataset is currently selected.

SARIMA-only may remain available when Hybrid specifically fails, provided SARIMA itself remains valid.

Never relabel SARIMA-only output as Hybrid.

---

# 49. Dashboard Module Structure

Normal dashboard modules remain:

1. Overview
2. Forecast
3. Historical Trends
4. Data
5. About the Model

---

# 50. Overview Module

The Overview should summarize:

- active dataset
- disease
- latest reporting information
- data-quality status
- research eligibility
- important warnings
- forecast availability/status

It must not:

- retrain models by itself
- declare an outbreak
- make deterministic claims about future disease activity

---

# 51. Forecast Module

The Forecast module should:

1. read the Active Dataset
2. verify dataset availability
3. allow disease selection
4. prepare eligible weekly observations
5. exclude recent incomplete reporting where applicable
6. check minimum history
7. execute the approved model-selection/evaluation protocol when required
8. generate Hybrid and SARIMA-only outputs
9. display the operational 52-week path
10. support 4/13/26/52-week views
11. display primary metrics appropriately
12. provide cautious plain-language interpretation

Do not show an uncertainty band.

Do not show seasonal naive as a normal forecast option.

---

# 52. Historical Trends Module

Support:

- weekly display from original weekly observations
- optional monthly aggregation
- optional quarterly aggregation

Monthly/quarterly aggregation is:

> display-only

It does not replace the weekly modeling input.

Calendar aggregation requires valid calendar/week-date information.

If calendar conversion is unavailable or ambiguous, explain that the summary cannot be produced rather than inventing dates.

---

# 53. Data Module

The Data module owns:

- upload
- source inspection
- worksheet selection
- transformation
- field mapping
- validation
- Before → After transformation review
- dataset activation

Before activation, show:

> Confirm & Use Data

If the user cancels:

- preserve the previous Active Dataset
- do not activate the new dataset

---

# 54. About the Model

Normal view should explain in plain language:

- Hybrid SARIMA–NNAR methodology
- SARIMA-only comparison
- evaluation metrics
- historical evaluation design
- important limitations

Advanced Details may expose:

- selected SARIMA order
- AIC information
- SARIMA candidate/failure diagnostics
- selected NNAR lag window
- hidden nodes
- activation
- seed/repeat rule
- training/validation/holdout ranges
- validation metrics
- horizon-specific metrics
- final holdout metrics
- scoring coverage
- DM-test result when applicable
- model-run status
- retrospective vs operational designation

Normal users should not need to inspect raw configuration JSON.

---

# 55. Reproducibility and Audit Metadata

For every completed disease/model run, record sufficient metadata to reconstruct and audit the run.

Required metadata includes:

- dataset identifier
- dataset version/signature
- disease
- model run timestamp
- population/scope metadata where available
- training range
- validation ranges
- final holdout range
- missing observation count
- zero observation count where relevant
- scoring coverage
- MAPE zero exclusions
- fixed SARIMA search grid
- candidate validity/failure information
- selected SARIMA order
- selected SARIMA AIC
- residual diagnostics
- fixed NNAR candidate grid
- selected lag window
- selected hidden-node count
- activation function
- fixed random seed
- five-fit NNAR rule
- validation RMSE
- validation MAE
- validation MAPE
- final holdout RMSE
- final holdout MAE
- final holdout MAPE
- 4/13/26/52-week evaluation metrics
- DM-test result when applicable
- final selected configuration
- forecast horizon
- whether run represents retrospective evaluation or operational future forecasting
- relevant failure/warning states

Expose a concise subset in:

> About the Model → Advanced Details

Retain full metadata in:

- technical logs
- technical export
- model-run audit data

---

# 56. Dataset and Model Cache Isolation

Cached results must be isolated using a dataset/model signature.

A forecast generated for one:

- dataset
- dataset version
- disease
- model configuration

must not be silently reused for a materially different one.

Changing the active dataset must not display stale model output from the prior dataset.

---

# 57. Data Provenance

Exports and technical model results should preserve enough provenance to establish:

- source dataset
- disease
- reporting period
- population scope
- case-classification status where available
- transformation status
- model configuration
- evaluation status

Do not strip provenance needed to distinguish:

- real research data
- retrospective all-age technical data
- synthetic/demo data

---

# 58. Synthetic / Demo Data

Synthetic or demo datasets may be supported for software demonstration.

They must be clearly labeled.

They must not count as research-eligible data.

They must not be blended with real CESU observations.

They must not contribute to thesis model-performance claims.

---

# 59. All-Age Data

All-age historical data may be retained for:

- retrospective technical evaluation
- software testing
- historical comparison

It does **not** validate the primary ages 5–19 research objective.

Keep all-age results separate from the thesis primary population.

---

# 60. Interpretation Rules

Forecast language should remain probabilistic/cautious.

Appropriate wording:

- projected increase
- projected decrease
- forecast indicates
- model estimates
- may support preparedness planning

Avoid:

- guaranteed outbreak
- certain spike
- will definitely increase
- causal claims unsupported by the model

The system forecasts reported case counts/trends.

It does not independently prove:

- causation
- outbreak declaration
- epidemic threshold exceedance
- school transmission

Epidemic-threshold comparison remains outside the approved application scope.

---

# 61. Required Implementation Order

The coding agent should integrate in this order:

### Phase 1 — Preserve existing application structure
Do not unnecessarily rewrite unrelated dashboard features.

### Phase 2 — Centralize model configuration
Create one authoritative configuration for:

- SARIMA grid
- m=52
- validation count/length
- holdout length
- NNAR lag grid
- hidden-node grid
- activation
- minimum complete windows
- repeat count
- fixed seed
- metrics

### Phase 3 — Fix time indexing
Ensure morbidity-week calendar positions are explicit and gaps are not compressed.

### Phase 4 — Fix missing/zero behavior
Remove any global zero replacement and any missing→zero behavior.

### Phase 5 — Implement leakage-free validation
Each validation window must have an independent SARIMA refit and residual derivation.

### Phase 6 — Implement SARIMA selection
Validity → AIC shortlist → validation ranking → deterministic tie-breaking.

### Phase 7 — Implement NNAR selection
Complete lag windows → minimum sample rule → fixed grid → five deterministic fits → validation ranking → tie-breaking.

### Phase 8 — Implement final Hybrid
SARIMA + recursive NNAR residual correction → final non-negative clipping.

### Phase 9 — Implement final holdout evaluation
Lock configuration → refit on all pre-holdout data → forecast final holdout once → official metrics.

### Phase 10 — Implement operational refit
Same locked model → full history → future 52-week path.

### Phase 11 — Update UI
Remove obsolete uncertainty visualization and seasonal-naive user-facing elements.

### Phase 12 — Add audit metadata
Ensure every run is reproducible and traceable.

---

# 62. Required Validation Tests

The coding agent must add or update automated tests covering at least the following.

## Data integrity

- zero remains zero
- missing remains missing
- no global 0→0.5 conversion
- Week 53 preserved
- missing week does not compress calendar index
- excluded/incomplete recent weeks are not silently used

## SARIMA

- exact candidate grid is used
- m=52
- failed candidates are logged and excluded
- ΔAIC shortlist rule works
- minimum shortlist size 3 where possible
- maximum shortlist size 5
- validation refit occurs independently per window
- final winner follows approved rank/tie logic

## NNAR

- exact lag candidates
- exact hidden-node candidates
- lag windows use true weekly positions
- incomplete lag windows are skipped
- at least 52 complete training windows required
- sigmoid hidden activation
- linear output
- five deterministic fits
- recursive multi-step residual forecasting

## Hybrid

- Hybrid = SARIMA + NNAR residual forecast
- no extra weighting coefficient
- negative residual corrections remain allowed
- clipping occurs after combination
- official metrics use clipped final forecasts

## Metrics

- RMSE includes zero-actual weeks
- MAE includes zero-actual weeks
- MAPE excludes zero-actual weeks
- missing actuals excluded from all metrics
- Hybrid and SARIMA use identical scoring positions
- WAPE absent from official model selection/evaluation

## Evaluation

- three validation windows
- each validation window 52 weeks
- expanding training
- minimum initial training 156 weeks
- final holdout 52 observations
- holdout untouched during model selection
- final model refit uses all eligible pre-holdout data
- operational future refit does not alter retrospective metrics

## UI

- no uncertainty band
- no seasonal-naive normal forecast option
- 4/13/26/52 views use one forecast path
- main page uses final 52-week metrics
- horizon metrics live in Advanced Details
- Hybrid unavailable state is explicit

## Reproducibility

- complete run metadata stored
- dataset/model signatures prevent stale cache reuse
- fixed seed recorded
- candidate failures recorded
- retrospective vs operational runs distinguishable

---

# 63. Non-Negotiable “Do Not” List

Do not:

- convert genuine zero counts to 0.5
- convert missing observations to zero
- compress time around missing morbidity weeks
- merge Week 53 into Week 52
- discard legitimate Week 53
- use the final holdout for hyperparameter selection
- reuse future-informed SARIMA residuals in earlier validation windows
- intentionally choose a poor/non-white SARIMA to help NNAR
- use arbitrary 70-case strata
- add WAPE back into official evaluation
- expose seasonal naive as a standard user model
- show an unvalidated uncertainty band
- weight the residual correction with an unapproved alpha
- fit NNAR on incomplete lag windows
- fit NNAR with fewer than 52 complete windows
- silently change the three 52-week validation windows
- silently shorten the 52-week holdout
- silently change the initial 156-week requirement
- silently switch models when Hybrid fails
- rerun model selection after observing final holdout performance
- call retrospective evaluation prospective validation
- let synthetic/all-age results validate the ages 5–19 research objective

---

# 64. Values Intentionally Not Newly Invented in This Handoff

Do not assume this handoff authorizes additional methodological decisions concerning:

- a new uncertainty/prediction interval method
- WAPE
- epidemic thresholds
- alternative Hybrid weighting
- new SARIMA grid bounds
- new NNAR candidate sizes
- alternative validation-window counts
- alternative holdout lengths
- arbitrary disease-incidence strata
- automatic missing-value imputation
- a new prospective-validation result

If implementation requires a low-level library-specific parameter not specified here, preserve the current stable implementation where possible and record it in technical configuration rather than treating it as a new thesis methodology choice.

---

# 65. Final Expected Modeling Flow

```text
Validated Active Dataset
        ↓
Select disease
        ↓
Preserve true morbidity-week calendar
        ↓
Keep zero = 0
Keep missing = missing
Preserve legitimate Week 53
        ↓
Check minimum initial history (156 weeks)
        ↓
Reserve final 52-observation holdout
        ↓
Run 3 expanding validation windows
(each 52 weeks)
        ↓
For each window:
    Fit valid SARIMA candidates
        ↓
    AIC shortlist
        ↓
    Evaluate shortlisted SARIMA models
        ↓
    Generate window-specific residuals
        ↓
    Build complete NNAR lag windows only
        ↓
    Evaluate fixed NNAR grid
        ↓
Aggregate RMSE / MAE / MAPE across 3 windows
        ↓
Select SARIMA configuration
Select NNAR configuration
        ↓
LOCK CONFIGURATION
        ↓
Refit SARIMA-only + Hybrid on all pre-holdout data
        ↓
Forecast untouched final 52-observation holdout
        ↓
Clip official forecasts to ≥ 0
        ↓
Evaluate RMSE / MAE / MAPE
+ supplementary DM test where applicable
        ↓
Store retrospective results
        ↓
Keep configuration locked
        ↓
Refit same configuration on full eligible history
        ↓
Generate one operational future 52-week path
        ↓
Display 4 / 13 / 26 / 52-week slices
        ↓
Store complete audit/reproducibility metadata
```

---

# 66. Definition of Done

The integration is complete only when all of the following are true:

- production forecasting uses Active Dataset rather than an independent production loader
- zero and missing semantics are correct
- true weekly indexing including Week 53 is preserved
- SARIMA selection is leakage-free
- NNAR selection is leakage-free
- candidate spaces match this specification exactly
- validation design matches this specification exactly
- final holdout remains untouched until final evaluation
- Hybrid uses additive residual correction only
- official metrics are RMSE, MAE, and MAPE only
- zero/missing scoring behavior is correct
- uncertainty band is removed
- operational forecasting uses locked selected configuration
- UI separates primary results from technical details
- reproducibility metadata is saved
- automated tests verify the critical rules above
- no older monthly/modeling assumptions remain in active forecasting logic
- no silent methodological fallback remains

This specification should be treated as the implementation source of truth for the current thesis forecasting pipeline.

## User clarification incorporated on 10 October 2026

1. Do not intersect the three AIC shortlists or freeze the first shortlist. Take the union of all SARIMA orders shortlisted in at least one window, then refit and score every union candidate across all three windows at their own training cutoffs. Only candidates with valid forecasts and metrics in every window may enter final ranking.
2. MAPE is not applicable for an all-zero validation window; RMSE and MAE remain valid. Average MAPE only across applicable windows and record coverage. If all three windows have undefined MAPE, rank using RMSE and MAE only and explicitly flag that MAPE was unavailable for selection.
