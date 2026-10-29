# Forecast methodology reconciliation — 17 October 2026

The statistical protocol below remains in force. The current one-action interface,
automatic research selection and historical-performance reuse are described in
[Guided forecasting](GUIDED_FORECAST.md).

## Sample forecasting added at the user's request

The fixed-settings demonstration is now **Advanced Options → Quick Preview — Fixed Settings**.
Use **Data → Try Synthetic / Demo Data → Confirm & Use
Data**, then open **Forecast** and click that action. Reviewed uploaded weekly
data can also be used. The built-in demo now contains 312 synthetic weekly
observations, sufficient for the shared estimator's burn and residual requirements.

Sample mode uses a fixed, untuned SARIMA(1,0,0)(1,0,0)52 with NNAR lag 2,
two hidden nodes, alpha 1.0 and seed 42. It uses the same fitting, convergence,
missing-position, recursion and nonnegative-output code as the research workflow.
It does not perform parameter search, claim disease-specific selection or produce
research performance metrics. Results, exports and reporting context explicitly
state **Quick Preview — Fixed Settings — Unvalidated demonstration forecast**.

For sample mode only, unknown reporting status may be included as supplied;
unknown historical calendar lengths assume 53 when a Week 53 row is supplied,
otherwise 52. These assumptions are logged without rewriting source metadata.
Explicitly incomplete observations remain excluded. Invalid counts, duplicate
records, existing calendar conflicts and insufficient history still fail. Zeros
and missing observations retain their values and positions. Sample assumptions do
not qualify data or configurations for the research workflow described below.

Verification: 310 regression tests passed, and a headless browser produced a real
52-week sample hybrid forecast using the new button, with no browser errors.

## Research workflow status

Implementation is ready for validation on eligible research data. Disease-specific
selection and final-test results are **not available**. The user confirmed that no
validated ages 5–19, confirmed-case dataset is available yet. The repository workbook
has unverified population/classification and a combined Measles–Rubella category;
it cannot be relabeled as Measles or used as thesis-valid evidence. No manuscript
claims were edited. Earlier deployed settings are archived in
`config/weekly_model_per_disease.legacy.json` and are not used as fallback models.

| Disease | Training / validation / test periods | Selected SARIMA | Selected NNAR | Validation and final-test metrics |
|---|---|---|---|---|
| Dengue | Pending eligible data | Pending corrected search | Pending corrected search | Not computed |
| Leptospirosis | Pending eligible data | Pending corrected search | Pending corrected search | Not computed |
| Measles | Pending eligible data | Pending corrected search | Pending corrected search | Not computed |

## Data and split

Use the validated active weekly dataset, disease-specific confirmed cases aged
5–19, with source provenance, reporting year/week and case count. The existing
source-evidence eligibility gate remains in force. Offline selection revalidates
records rather than trusting a JSON eligibility flag. Invalid counts, unresolved
duplicates and insufficient history fail explicitly. Genuine zeros remain zero.
Missing positions, including trailing complete-but-unreported positions, remain
missing. Incomplete reporting is excluded without compressing internal time gaps.
Legitimate Week 53 remains a chronological position; annual seasonality is 52.

Final test = final 52 chronological positions; validation = preceding 52;
training = all earlier positions. Minimum training history is 156 observed weeks;
at least 52 usable post-burn NNAR samples are also required. No shuffling,
imputation, zero replacement or rounding before metrics occurs.

## Shared estimators and selection

The research model remains **Hybrid SARIMA–NNAR**, with SARIMA-only as the formal
comparison. The statsmodels class is named `SARIMAX`; no `exog` is supplied, so
this implementation fits SARIMA, without external regressors.

`dashboard/weekly/estimators.py` is shared by offline selection, final testing and
operational fitting. SARIMA uses constrained stationarity/invertibility, no trend,
L-BFGS (300 iterations), levels with `simple_differencing=False`, approximate
diffuse initialization (variance 1e6), and state-space missing-value handling.
Nonconvergence, nonfinite parameters/likelihood/forecasts and insufficient history
exclude candidates with recorded failure reasons. There is no replacement model.

The 144-candidate grid is p/q = 0,1,2; d/D = 0,1; P/Q = 0,1; s = 52.
All use **108 initial positions excluded from the likelihood**, equal to the
maximum state dimension in this grid, with identical observed positions thereafter.
The likelihood is on the same undifferenced observed scale for every candidate.
Metadata records AIC, log likelihood, parameter count, burn, effective observed
count and positional count, convergence/status and failures. Incomparable bases
cannot be ranked. The same burn and initialization apply in deployment.

The ten successful candidates with lowest training AIC form a predetermined
shortlist. Selection then minimizes nonnegative 52-week validation SARIMA RMSE.
RMSE ties (`rtol=1e-6`, `atol=1e-8`) use MAE, then supporting MAPE. AIC measures
training fit/complexity; it is not forecast accuracy. All comparisons use the same
finite-actual mask; a nonfinite forecast is a failure rather than a smaller mask.

The selected training-only SARIMA generates residuals. The first 108 residual
positions are unusable; remaining gaps are preserved. Only samples with finite
targets and all required finite lagged inputs enter NNAR. StandardScaler fits
those training inputs only; targets are unscaled. No validation observation enters
SARIMA, residual generation, scaling or NNAR fitting.

NNAR uses one ReLU hidden layer and scikit-learn MLPRegressor's squared-error loss
with L-BFGS (2,000 iterations). It is an autoregressive MLP, not an exact R nnetar
recreation. Search lags: 2,4,6,8,13,26; hidden nodes: 2,4,8,12; alpha:
0.001,0.01,0.1,1.0. Each of 96 configurations uses fixed seeds 42,137,2026.
All three must converge. Rank by median validation **Hybrid case-count** RMSE,
then median MAE and supporting median MAPE. Preserve all seed outcomes. Production
always uses seed 42; it is not chosen after looking at the test set.

Recursive forecasts append predicted residuals; they never consume future actual
residuals. Hybrid = raw SARIMA forecast + residual correction, then clip at zero.
The standalone SARIMA forecast is independently clipped at zero. NNAR improvement
compares hybrid and baseline case errors, never residual error and case error.

## Diagnostics, lock and evaluation

ADF is only a stationarity diagnostic. Persist statistic, p-value, chosen ADF lags
and sample count; AIC inside ADF selects its regression lag length. Constant,
gapped or invalid data return unavailable, without compressing observations.

Ljung–Box uses `model_df = p+q+P+Q`, at lags 13,26,52 when lag exceeds model_df
and at least twice that lag remains. Gapped or constant residuals produce an
explicit unavailable diagnostic. Record Q, p-value, lag, degrees of freedom and
sample count. A p-value proves neither independence nor NNAR improvement.

Persist the complete lock, SHA-256 configuration ID, training/validation data
fingerprint, period boundaries, run ID, timestamp and selected diagnostics before
touching final-test values. Final evaluation verifies that lock and source prefix,
refits on training + validation, forecasts 52 final-test positions and reports both
models on identical observations. Configuration hashes before and after must match.
No test-dependent retuning is permitted, including when the hybrid loses.

RMSE/MAE include zero actuals; MAPE excludes them. All metrics exclude missing
actuals. Report total test positions, observed scored count, missing exclusions,
MAPE-valid count and zero exclusions. Percentage errors remain supporting evidence;
there is no 32.22% pass/fail threshold. Full precision is used before display.
The guided **Generate Forecast** action automatically evaluates or reuses compatible
historical performance before future forecasting. Historical evaluation must use the same
selection periods; newly appended history is for operational refitting, not for
quietly moving the historical test boundary.

## Operational forecast and progress

Load one disease lock and refit both stages on **all eligible history**. Generate
one future 52-week path; 4/13/26/52 views slice it without refitting. Unvalidated
uncertainty bands are disabled, including bands in older cached chart results.
Reporting remains a downstream consumer of forecast output.

Background threads execute model work. SQLite status records coordinate duplicate
requests across local web workers, with a heartbeat for interrupted workers and
one-second UI polling. Real backend events report eligibility, configuration,
history, SARIMA, residuals, NNAR, recursion, combination and saving. Historical
evaluation has its own heading, boundaries/refit/test/metrics sequence. No elapsed
time estimate or simulated percentage is used. Buttons are disabled while active;
failure restores them, identifies the last executed stage and preserves the prior
result. Completed logs stay in a collapsible details view. Stale dataset/disease
jobs cannot attach their results to a different active view. Warnings are separate.

Stored run metadata includes run ID, disease, dataset ID, model/configuration IDs,
start/completion timestamps, status/stage, per-stage timestamps/statuses, warnings,
failure reason and forecast start/end/horizon. Technical exceptions stay in backend
logs; user-facing errors are restricted to safe model-domain messages.

## Reproduction when data becomes available

Export the validated active dataset JSON (including `records`, `metadata`,
`quality`, `eligible` and source references), then run:

```powershell
python SARIMANNAR/residual_search.py --dataset eligible-dataset.json --output evidence/corrected-selection --install
```

This runs all three diseases unless `--disease` is supplied. Each output directory
contains checkpointed `search.json`, immutable `locked.json`, `evaluation.json`
with actuals/predictions and metrics, and `methodology.md` with the requested
parameter/period/performance comparison. Installation occurs only after all
requested searches and final evaluations succeed. The legacy CSV/config CLI is
superseded; historical `rs_*`, `rt_*` and `pin_*` artifacts are not corrected evidence.

## Verification and limitations

Regression tests include genuine SARIMA and NNAR estimator execution on fabricated
fixtures, independent statsmodels Ljung–Box comparisons, wrong-target and leakage
guards, sample/scaler/recursive checks, lock immutability, all-history operational
refits and job success/failure/duplicate/stale-result behavior. Browser checks use
explicitly simulated fits to test responsiveness and rendering; they are not model
performance evidence. See `evidence/methodology-tests-final.txt` and
`evidence/forecast-progress-browser/checks.json` when generated.

Verification completed: the full suite passed 303 tests. A subsequent focused run
passed 22 tests, including additional stale-run and unavailable-configuration
cases. Pyflakes and `git diff --check` passed. Headless Edge verified progress,
success, explicit performance computation, restored controls, accessible completed
logs and preservation of prior output after a simulated fitting failure, with no
browser errors. These are software checks, not disease performance results.

No eligible disease search has been run, no winner is preselected and no final-test
performance is claimed. The ten-model AIC shortlist, common initialization/burn,
single validation block and three seeds are fixed methodological choices with
finite search coverage. No calibrated intervals or prospective validation exist.
Algorithmic exclusion cannot erase prior human exposure to historical data.

The job store requires a writable persistent filesystem and a long-lived Python
process. SQLite coordinates a single host; multi-host/serverless deployments need
a durable shared job service. Worker restarts are surfaced as interrupted jobs,
not silently resumed model fits. The polling UI is not a distributed task queue.

Implementation references: [statsmodels SARIMAX](https://www.statsmodels.org/stable/generated/statsmodels.tsa.statespace.sarimax.SARIMAX.html)
and [Ljung–Box implementation](https://github.com/statsmodels/statsmodels/blob/main/statsmodels/stats/diagnostic.py).
