# FINAL CODING-AGENT HANDOFF
## Antipolo Weekly Infectious Disease Forecasting System
### Consolidated approved revisions through Revision 45
### Date: 3 October 2026

---

# 1. PURPOSE

Continue development of the Antipolo infectious-disease forecasting system using the approved weekly research and software design.

The primary research objective is to forecast **weekly reportable infectious-disease case counts among individuals aged 5–19 in Antipolo City** for public-school preparedness.

The system may also support technical or exploratory datasets, including all-age data, but these must remain clearly separated from final thesis evidence.

This handoff consolidates the currently approved behavior.

Do not revert to the previous monthly workflow.

---

# 2. CURRENT HIGH-LEVEL STATUS

The following major areas are already implemented or substantially implemented:

- weekly data pipeline
- multi-sheet workbook support
- automatic source transformation
- worksheet Include/Exclude controls
- transformation review
- weekly historical views
- 52-week forecasting architecture
- Hybrid SARIMA–NNAR primary model structure
- SARIMA-only comparison
- provenance
- data-quality warnings
- thesis-eligibility infrastructure
- retrospective/prospective separation
- simplified user-facing navigation
- synthetic/demo isolation
- expanded automated testing

The next work should refine and integrate the decisions below without rebuilding the system unnecessarily.

---

# 3. PRIMARY DATA FREQUENCY

The core modeling frequency is:

**Weekly morbidity observations**

Do not aggregate data to monthly frequency before fitting the model.

Internal primary observation structure:

- Disease
- Reporting Year
- Morbidity Week
- Case Count

Monthly and quarterly values may be generated for dashboard presentation only.

They must not change the underlying weekly model.

---

# 4. FORECAST HORIZON

Generate one forecast trajectory extending up to:

**52 weekly forecast points**

Allow the user to view:

- 4 weeks
- 13 weeks
- 26 weeks
- 52 weeks

Changing the display horizon must not retrain the model solely because the visualization window changed.

Suggested interpretation:

- 1–4 weeks: near term
- 5–13 weeks: short term
- 14–26 weeks: medium term
- 27–52 weeks: annual planning view

---

# 5. PRIMARY RESEARCH POPULATION

The final thesis population is:

**Ages 5–19**

Existing all-age data remains usable for:

- technical testing
- retrospective evaluation
- pipeline verification
- exploratory modeling

But all-age results must never be represented as validation of the ages 5–19 thesis objective.

---

# 6. EVALUATION CONTEXTS

Maintain two separate contexts.

## Technical / Retrospective Evaluation

May include:

- existing all-age historical datasets
- exploratory model configurations
- historical testing

## Final Thesis Evaluation

Requires an eligible dataset with established:

- ages 5–19 population
- confirmed-only classification
- weekly case counts
- approved disease coverage
- CESU/PIDSAR provenance
- appropriate reporting completeness
- approved methodology

Never merge the performance metrics from these two contexts.

---

# 7. HISTORICAL 2025 EVALUATION

Continue describing the previous historical testing as:

**Retrospective evaluation**

Do not call it prospective validation.

A future prospective-validation workflow remains a separate research stage.

---

# 8. PRIMARY DATA SOURCE

Primary research data:

**CESU/PIDSAR disease-specific surveillance records**

Use the project's approved terminology.

FHSIS may remain:

- contextual
- secondary
- reference-only

Do not treat FHSIS Top 5 summaries as equivalent to the disease-specific surveillance dataset.

---

# 9. CASE CLASSIFICATION

Final thesis data requires:

**Confirmed cases only**

Do not automatically broaden this to:

- suspected
- probable
- mixed classification

If confirmed-only status cannot be established, the dataset may still be used technically but must not be marked eligible for final thesis evaluation.

---

# 10. DISEASE LABELS

Support:

- Measles
- Measles-Rubella

as distinct categories where the source distinguishes them.

Never automatically merge them.

Preserve source terminology.

---

# 11. RESEARCH SCOPE VS SOFTWARE CAPABILITY

The software may technically support additional diseases.

That does not automatically expand the formal thesis disease scope.

Keep separate:

**Software-supported disease**

versus

**Thesis-approved disease**

---

# 12. PRIMARY MODEL

Primary forecast:

**Hybrid SARIMA–NNAR**

Comparison:

**SARIMA-only**

The Hybrid forecast is the primary modeled output.

SARIMA-only must remain visibly separate.

---

# 13. SEASONAL-NAIVE MODEL

Do not show seasonal naive as a normal user-facing benchmark.

Historical seasonal-naive evidence may remain preserved in audit/development records.

Do not delete historical evidence.

---

# 14. HYBRID FAILURE

Never silently replace Hybrid with SARIMA-only.

If Hybrid cannot be generated:

1. Try only the permitted SARIMA candidate configurations.
2. If Hybrid remains unavailable, show:

**Hybrid unavailable**

3. Provide a reason where possible.
4. SARIMA-only may still remain visible separately.
5. Never relabel SARIMA as Hybrid.
6. Never fabricate Hybrid output.
7. Preserve failure status in exports and advanced model information.

---

# 15. WEEKLY DATA QUALITY

Detect and report:

- invalid morbidity weeks
- duplicates
- missing weeks
- explicit zero-case observations
- blank/unreported counts
- week 53
- inconsistent disease labels
- population conflicts
- classification conflicts
- source/provenance issues

Critical rule:

**Missing ≠ zero**

Never silently convert missing observations to zero.

---

# 16. INTERNAL MISSING WEEKS

Internal weekly gaps may still allow forecasting where technically possible.

Rules:

- keep them missing
- do not automatically interpolate
- do not convert them to zero
- show warnings
- expose affected weeks
- preserve them in source evidence

Do not invent an imputation method.

---

# 17. WEEK 53

Preserve week 53 exactly as supplied.

Never automatically:

- remove it
- merge it into week 52
- move it to another reporting year
- turn it into zero

A valid reporting-calendar definition must ultimately establish whether each year contains 52 or 53 weeks.

---

# 18. DECISION 43 — REPORTING CALENDAR

Require documented source/CESU evidence establishing whether each reporting year uses:

- 52 morbidity weeks
- or 53 morbidity weeks

Then:

- valid week 53 remains
- conflicting week 53 is flagged
- nonexistent week 53 may only be excluded when supported by the source calendar
- blanks are not automatically treated as zero

Store year-length information as dataset/calendar metadata.

---

# 19. REPORTING DELAYS

Expose data freshness.

Where available show:

- latest reporting week
- latest complete reporting week
- reporting status
- source/extraction date
- late-report warning

Do not automatically assume a recent low count represents a genuine decline.

---

# 20. RECENT INCOMPLETE WEEKS

Recent observations marked potentially incomplete must not automatically enter training.

They should:

- remain visible
- remain in source evidence
- show their reporting status
- be identified as excluded from training

---

# 21. DECISION 41 — HISTORICAL REPORTING COMPLETENESS

Allow a dataset-level setting:

**Historical reporting period complete**

but only when supported by CESU/source documentation.

If confirmed at the dataset level, historical observations do not need individual completeness flags.

Do not infer this automatically merely because the data are old.

If source confirmation does not exist:

**Reporting completeness remains unknown.**

---

# 22. DECISION 42 — BLANK CASE COUNTS

The currently identified blank observations must be resolved individually using source evidence.

Allowed resolution:

- Confirmed zero
- Unreported / missing
- Nonexistent reporting week
- Corrected source value

Never automatically fill blank values.

Preserve the original uploaded evidence after correction.

---

# 23. STRUCTURED MODEL INPUT

Modeling input may be:

- CSV
- XLSX

PDF files remain:

- source evidence
- provenance
- reference documents

Do not use direct PDF extraction as the production modeling workflow.

---

# 24. INTERNAL CANONICAL FORMAT

Internally normalize observations to:

```text
disease
year
morbidity_week
case_count
```

This is an **internal normalized representation**.

It is not a required user-upload structure.

---

# 25. AUTOMATIC UPLOAD TRANSFORMATION

The upload system must accept recognizable source formats and transform them automatically.

Support:

- canonical long tables
- aliased long tables
- wide week-by-year tables
- disease-specific worksheets
- multi-sheet XLSX files

Do not reject recognizable source files merely because they do not already have the canonical four internal column names.

---

# 26. MULTI-SHEET WORKBOOK WORKFLOW

Each worksheet should be handled as a separate review unit.

At workbook review, show each worksheet with:

- worksheet name
- inferred type
- inferred disease if available
- row count
- status
- Include / Exclude

Only included worksheets should gate confirmation.

---

# 27. NON-DATA WORKSHEETS

Allow users to exclude worksheets such as:

- Notes
- README
- Instructions
- Summary
- documentation sheets

Recognizable non-data worksheets should preferably be suggested as:

**Excluded**

but the user may reverse the choice.

A Notes sheet must never prevent the rest of the workbook from being activated.

---

# 28. WORKSHEET REVIEW

For each included worksheet, clearly show:

**Reviewing worksheet: [worksheet name]**

For disease sheets, ideally use a tab/card structure such as:

- Dengue
- Leptospirosis
- Measles-Rubella

Each worksheet receives its own transformation preview and warnings.

---

# 29. BEFORE / AFTER TRANSFORMATION REVIEW

After upload and transformation, open:

**Review Data Transformation**

Show:

## Original Uploaded Data

- source filename
- worksheet name
- original headings
- original row count
- first sample rows

## Prepared Weekly Data

- Disease
- Year
- Morbidity Week
- Case Count
- transformed observation count
- sample transformed rows

---

# 30. TRANSFORMATION EXPLANATION

Include a plain-language:

**What changed?**

Examples:

- Disease detected from worksheet name
- Year columns unfolded
- Week column identified
- Case counts retained
- Total rows excluded from modeling
- Empty rows excluded
- Week 53 preserved
- Blank values preserved as missing
- Unused columns retained in source evidence

Do not show raw transformation JSON.

---

# 31. MANUAL FIELD MAPPING

When automatic matching is uncertain, show:

**We could not identify all required fields automatically. Please help us match the columns.**

Only request genuinely unresolved fields.

Required fields should:

- show a red border if unresolved
- show `Required`
- include short guidance

Example:

**Morbidity Week \***  
Select the column containing weekly reporting numbers such as 1–52/53.

---

# 32. FIELD-AWARE MAPPING DROPDOWNS

Do not display every source column indiscriminately.

Filter options by plausible field.

### Disease

Prefer:

- worksheet name
- Disease
- Diagnosis
- Condition
- categorical/text fields

Do not normally show year columns such as:

`2025 — 0,1,1`

as disease choices.

### Year

Prefer:

- Reporting Year
- Year
- year-like values/headings

### Morbidity Week

Prefer:

- Week
- Week No
- Morbidity Week
- MW
- numeric fields compatible with week values

### Case Count

Prefer numeric count-like columns.

Sample values may be shown when useful, but not as unnecessary clutter.

---

# 33. WIDE WEEK-BY-YEAR TABLES

Recognize layouts such as:

| Week | 2023 | 2024 | 2025 |
|---|---:|---:|---:|

Automatically transform them into weekly long-form observations.

Do not ask users to map every year column individually.

Never sum values across years.

Show:

**Year columns detected: 2023, 2024, 2025**

and explain that they were unfolded into weekly records.

---

# 34. DISEASE FROM WORKSHEET NAME

If a worksheet is clearly named:

`Leptospirosis`

the system may use:

**Disease = Leptospirosis**

without forcing manual selection.

Provide a small `Change` action if needed.

If the worksheet name conflicts with a disease column:

- show the conflict
- require a user choice
- do not silently resolve it

---

# 35. INVALID-WEEK FOOTERS

Recognized totals/verification footer rows may be excluded automatically from modeling.

Requirements:

- retain them in original source evidence
- disclose what was excluded
- explain why
- do not mistake them for real morbidity weeks

Unknown invalid-week rows must remain blocked until reviewed.

---

# 36. UPLOAD ACTIVATION

Upload must not immediately replace the active dataset.

Required flow:

**Upload**

→ **Transform**

→ **Review**

→ **Confirm & Use Data**

Only confirmation activates the replacement.

Cancel must preserve the existing active dataset.

---

# 37. TRANSFORMATION HISTORY

After activation, allow:

**View Transformation Details**

The user should be able to inspect later:

- original source
- prepared data
- mappings
- exclusions
- warnings

without repeating the upload.

---

# 38. DATASET PROVENANCE

Preserve:

- source file
- worksheet
- upload date
- source organization/system
- transformation behavior
- population
- classification
- reporting status
- dataset type
- validation status
- thesis eligibility

Do not fabricate missing provenance.

---

# 39. DATASET AUDIT TRAIL

Preserve lifecycle events such as:

- Uploaded
- Prepared
- Reviewed
- Confirmed
- Activated
- Replaced
- Reset

Normal users should not see raw internal audit objects.

---

# 40. THESIS ELIGIBILITY

Simple user-facing statuses:

- Eligible for Thesis Evaluation
- Technical / Exploratory Only
- Needs More Information

Clicking the status may explain why.

Example:

**Needs More Information**
- Ages 5–19 not established
- Confirmed-only status not established

---

# 41. SYNTHETIC DATA

Keep synthetic/demo data available for testing and demonstrations.

Label clearly:

**Synthetic / Demo Data**

Rules:

- cannot qualify for thesis evaluation
- metrics remain separate
- cannot be mixed into an active real research dataset
- cannot support Antipolo research conclusions

---

# 42. CACHE ISOLATION

Cache/model-result signatures must account for material context including:

- dataset
- source
- disease
- population
- classification
- frequency
- date coverage
- configuration
- model version

Never reuse a forecast belonging to a different dataset context.

---

# 43. USER-FACING NAVIGATION

Normal navigation should be:

1. **Overview**
2. **Forecast**
3. **Historical Trends**
4. **Data**
5. **About the Model**

Do not expose developer-oriented names.

---

# 44. OVERVIEW

Keep Overview simple.

Show:

- active dataset
- disease
- latest complete week
- data status
- concise forecast direction/status
- thesis eligibility
- important warnings

Do not overload it with diagnostics.

---

# 45. FORECAST VIEW

Show:

- Hybrid SARIMA–NNAR
- SARIMA-only comparison
- observed history
- forecast trajectory
- uncertainty range
- horizon selector
- MAE
- WAPE
- plain-language interpretation

If no valid forecast is available:

show that explicitly.

Never invent a forecast or metric.

---

# 46. HISTORICAL TRENDS

Allow:

- Weekly
- Monthly
- Quarterly

These are visualization modes only.

Monthly/quarterly views require valid source-calendar dates where necessary.

If calendar information is unavailable, explain why the summary cannot be generated rather than inventing dates.

---

# 47. DATA PAGE

Primary actions:

- Upload Data
- Current Dataset
- View Data Summary
- View Transformation
- Replace Dataset
- Reset Dataset

Keep technical details behind expandable sections.

---

# 48. ABOUT THE MODEL

Explain first in plain language:

- what SARIMA does
- what NNAR does
- how Hybrid works
- why SARIMA-only is also shown
- what performance metrics mean
- known limitations

Advanced model diagnostics remain collapsible.

---

# 49. REMOVE DEVELOPER-FACING UI

Do not expose normal-user controls such as:

- raw JSON editors
- pre-weekly JSON
- metadata dash
- weekly-notice
- component IDs
- callback IDs
- cache hashes
- implementation-state objects
- raw Python/config dictionaries

These may remain internal.

---

# 50. PROGRESSIVE DISCLOSURE

Normal user sees:

- result
- warning
- explanation
- action

Advanced user may expand:

- model diagnostics
- parameter details
- provenance
- transformation mappings
- evaluation details

Research transparency does not require exposing engineering internals.

---

# 51. GUIDANCE TEXT

Use concise instructional text.

Example Upload guidance:

> Upload your weekly disease records. The system will prepare the file automatically and show what changed before using it.

Example missing-data guidance:

> Missing weeks are preserved as missing and are not automatically counted as zero cases.

Example Forecast guidance:

> Choose how far ahead you want to view the forecast. Changing the view does not retrain the underlying model.

---

# 52. FORECAST LANGUAGE

Use cautious projection wording.

Acceptable:

- projected to increase
- projected to decrease
- projected to remain stable
- highest projected level
- model-based projection

Avoid:

- outbreak will occur
- cases will definitely increase
- system detected an outbreak
- resources must be deployed

The system forecasts; it does not issue mandatory public-health decisions.

---

# 53. EPIDEMIC THRESHOLDS

Do not implement an epidemic-threshold comparison feature.

Do not add:

- threshold alerts
- threshold crossing status
- outbreak declaration logic

unless later approved.

---

# 54. PERFORMANCE METRICS

Keep:

- MAE
- RMSE
- MAPE
- WAPE

Main Forecast view:

- MAE
- WAPE

Advanced details:

- MAE
- RMSE
- MAPE
- WAPE

Never divide by zero.

Undefined metrics must show as unavailable/undefined rather than fabricated.

Hybrid and SARIMA-only must use the same scoring positions.

---

# 55. REMOVE 32.22% MAIN-UI REFERENCE

The old fixed:

**32.22% MAPE**

must not appear as a live operational performance indicator.

It may remain documented historically only if provenance can be established.

---

# 56. UNCERTAINTY RANGE

The current uncertainty visualization remains provisional.

Do not call it:

- 95% confidence interval
- 95% prediction interval

unless formally calibrated.

Use:

**Forecast uncertainty range**

or equivalent.

---

# 57. EXPORTS

Detailed exports should retain where applicable:

- disease
- year
- morbidity week
- observed/forecast
- case count
- population
- classification
- source
- dataset type
- model
- SARIMA configuration
- NNAR configuration
- horizon
- metrics
- warnings
- research eligibility
- configuration version

---

# 58. PROSPECTIVE VALIDATION

Preserve structural support for future prospective evaluation.

Store:

- forecast issue date
- original forecast
- forecast version
- later observed data
- subsequent revisions
- horizon-specific errors

Never overwrite the original forecast after outcomes become known.

Do not claim prospective validation has already been completed.

---

# 59. EXPLORATORY WEEKLY PROTOCOL — DECISIONS 44–45

The project has now approved running an exploratory technical configuration before final adviser approval.

Every result from this configuration must be labeled:

**Exploratory Weekly Configuration v0.1 — Technical / Retrospective Evaluation Only**

Do not represent this as the final adviser-approved methodology.

---

# 60. EXPLORATORY SARIMA SEASONALITY

Use provisional seasonal period:

```text
m = 52
```

This is an exploratory integer approximation for annual weekly seasonality.

Do not claim it resolves the full 52/53-week reporting-calendar issue.

---

# 61. EXPLORATORY SARIMA CANDIDATES

Use the following bounded candidate set:

```text
SARIMA(p,d,q)(P,D,Q)[52]

1.  (0,0,0)(0,1,1)[52]
2.  (1,0,0)(0,1,1)[52]
3.  (0,0,1)(0,1,1)[52]
4.  (1,0,1)(0,1,1)[52]
5.  (2,0,0)(0,1,1)[52]
6.  (0,0,2)(0,1,1)[52]

7.  (0,1,0)(0,1,1)[52]
8.  (1,1,0)(0,1,1)[52]
9.  (0,1,1)(0,1,1)[52]
10. (1,1,1)(0,1,1)[52]

11. (1,0,0)(1,0,0)[52]
12. (0,0,1)(0,0,1)[52]
13. (1,0,1)(1,0,0)[52]
14. (1,0,1)(0,0,1)[52]

15. (1,1,0)(1,0,0)[52]
16. (0,1,1)(0,0,1)[52]
```

For every candidate retain:

- fitted status
- convergence status
- AIC
- residual diagnostics
- failure reason where applicable

Do not silently discard failed candidates from the technical record.

For this exploratory configuration, select the lowest-AIC successful candidate subject to the currently implemented validity/convergence checks.

Do not describe this candidate list as final thesis methodology.

---

# 62. ADF / ACF / PACF

Continue calculating/displaying where available:

- ADF
- ACF
- PACF

Treat these as diagnostics.

Do not claim they automatically prove one unique correct SARIMA model.

---

# 63. EXPLORATORY NNAR

Use SARIMA residuals as the NNAR target.

Exploratory residual lags:

```text
1
2
3
4
52
```

Network:

```text
Hidden layers: 1
Hidden nodes: 3
Maximum iterations: 2000
Random seed: 42
Forecasting: recursive
```

Use the implementation's established activation/scaling behavior where appropriate, but ensure scaling is learned from training data only.

---

# 64. NNAR MISSING DATA

Only create NNAR training windows when:

- the target residual exists
- every required lag residual exists

Never compress the timeline across missing weeks.

If insufficient valid windows remain, return:

**Hybrid unavailable — insufficient complete residual lag windows.**

SARIMA-only may remain separately visible.

---

# 65. EXPLORATORY HOLDOUT

Use:

**Final 52 observations**

as the exploratory retrospective holdout.

Training uses observations before the holdout.

No future information may enter model fitting.

This is exploratory only.

Do not claim this is the final evaluation design.

---

# 66. HORIZON-SPECIFIC EXPLORATORY METRICS

Where sufficient observations exist, additionally report technical metrics for:

- weeks 1–4
- weeks 1–13
- weeks 1–26
- weeks 1–52

Hybrid and SARIMA-only must use identical scoring positions within each horizon.

These belong primarily under Advanced Details.

---

# 67. ROLLING-ORIGIN EVALUATION

Rolling-origin evaluation is not currently approved as implemented final methodology.

Do not fabricate it.

The current exploratory protocol uses the supported single chronological holdout.

Rolling-origin evaluation may be added later after adviser approval.

---

# 68. EXPLORATORY MISSING-DATA POLICY

Source values remain unchanged.

SARIMA may use supported state-space missing-data handling where configured.

Never change missing source values to zero.

NNAR uses complete residual windows only.

Scoring excludes observations whose actual outcome is missing.

Record:

- number of excluded observations
- remaining scoring coverage

---

# 69. EXPLORATORY WEEK-53 POLICY

For exploratory runs use:

```text
week53_policy = preserve_sequence
seasonal_period = 52
```

Display a technical warning:

> Week 53 is preserved as an additional source observation. The exploratory annual seasonal period remains fixed at 52 and does not constitute final resolution of the 52/53-week calendar structure.

Do not merge or remove valid week-53 observations just to make the model run.

---

# 70. EXPLORATORY MINIMUM HISTORY

Use an exploratory minimum usable history of:

**156 observations**

approximately three 52-week cycles.

This is only a technical minimum, not proof that the series is statistically sufficient.

NNAR also requires adequate complete lag-52 residual windows.

---

# 71. REPRODUCIBILITY

Exploratory seed:

```text
42
```

Where stochastic components exist, record the seed in:

- model metadata
- exports
- technical results

---

# 72. NEGATIVE FORECASTS

Final case-count forecast values may be constrained to:

**minimum 0**

Preserve any relevant diagnostic information from the unconstrained modeling process internally if useful.

Do not display negative predicted disease counts to users.

---

# 73. EXPLORATORY UNCERTAINTY

Continue using the currently implemented training-residual-RMSE-based uncertainty shading if necessary.

It must remain labeled provisional.

Do not describe it as a calibrated 95% interval.

---

# 74. DATA READINESS BOUNDARY

Installing Exploratory Configuration v0.1 does not automatically make the currently uploaded dataset research-ready.

The system must continue respecting:

- reporting-completeness status
- blank-count warnings
- reporting-calendar status
- population
- classification
- source provenance

Do not fabricate these facts merely to enable forecasting.

Technical/exploratory runs may be allowed only where the current system's explicit technical eligibility rules permit them and must remain clearly labeled.

---

# 75. REQUIRED TEST COVERAGE

Maintain or expand automated coverage for:

## Transformation

- canonical long CSV
- aliased long CSV
- XLSX
- wide week × year
- disease worksheet inference
- multi-sheet workbook
- Notes exclusion
- Include/Exclude
- invalid footer handling
- blank preservation
- explicit zero preservation
- week 53 preservation
- manual mapping
- ambiguous mapping
- source conflicts

## UI

- active worksheet clearly named
- unresolved fields red/Required
- plausible mapping choices only
- excluded worksheet does not block confirmation
- Cancel preserves current dataset
- Confirm activates replacement
- transformation review can reopen
- no normal JSON editor
- no developer-facing component labels

## Modeling

- 52-week path
- 4/13/26/52 views
- no retraining solely from display horizon
- Hybrid primary
- SARIMA-only separate
- Hybrid failure explicit
- no silent substitution
- candidate failure status retained
- missing residual windows handled
- random seed preserved
- negative forecast clipping
- week-53 policy metadata
- holdout separation
- identical scoring positions

## Metrics

- MAE
- RMSE
- MAPE
- WAPE
- zero handling
- missing actual handling
- evaluation coverage
- undefined metrics

## Data integrity

- missing ≠ zero
- incomplete reporting exclusion
- source metadata
- population separation
- classification separation
- synthetic isolation
- cache isolation

---

# 76. VISUAL ACCEPTANCE

Continue real-browser testing.

Review at minimum:

- desktop
- mobile
- upload
- worksheet review
- transformation modal
- Overview
- Forecast
- Historical Trends
- Data
- About the Model
- error/warning states

No page-level horizontal overflow should occur.

Tables may scroll inside their own containers.

---

# 77. DOCUMENTATION

Update:

- README
- WEEKLY_SYSTEM documentation
- transformation documentation
- forecast/model documentation
- test report
- latest reconciliation report

Documentation must clearly distinguish:

### Implemented software behavior

from

### Exploratory modeling choices

from

### Final adviser-approved methodology

Do not describe exploratory settings as final methodology.

---

# 78. DO NOT IMPLEMENT / DO NOT CLAIM

Unless separately