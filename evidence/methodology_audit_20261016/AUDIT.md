# Methodology audit

**Needs revision. Coverage: partial empirical validation; source audit covers all five requested methods.** Application code and installed model settings were not changed. This audit distinguishes implemented calculations from evidence of predictive accuracy.

## Scope and implementation

`app.py` imports `dashboard.weekly.ui`; the live pipeline is `dashboard/weekly/model.py`. `dashboard/modeling/` is the historical monthly pipeline, not the operational route. `dashboard/weekly/settings.py` loads `config/weekly_model_per_disease.json` by default. Its three named diseases each have one permitted SARIMA specification, with NNAR sizes attributed to `SARIMANNAR/residual_search.py`. Consequently runtime AIC calculation does not perform a fresh multi-model search for those diseases.

| Method | Implemented? | Assessment |
|---|---|---|
| AIC | Yes, statsmodels `fit.aic` | Library calculation is genuine. Offline selection compares candidates with unequal likelihood burns, undermining the installed orders' selection basis. |
| ADF | Yes, statsmodels `adfuller(..., autolag='AIC')` | Valid raw-series unit-root diagnostic when data are complete and nonconstant. It does not choose weekly d/D or test the final differenced series. |
| Ljung–Box | Yes | Weekly and offline calls omit the fitted-model degrees-of-freedom adjustment. Offline calls additionally include initialization residuals. |
| SARIMA fitting | Yes, SARIMAX | Runtime enforces stationarity/invertibility, checks convergence and finite forecasts, and preserves missing positions. Offline settings differ materially. |
| NNAR fitting | Yes, custom autoregressive MLP | Runtime lag construction, training-only scaling and recursive forecasts are sound. Tuning contains a wrong-target error, inner-validation leakage and estimator mismatch. |

## Prioritized problems and proposed fixes

1. **High: NNAR tuning scores case forecasts against residuals.** In `SARIMANNAR/residual_search.py:524–548`, `tr_val` is a slice of SARIMA residuals. Both baseline forecasts and baseline-plus-neural forecasts are in case-count units, yet RMSE compares them with `tr_val`. The correct target for these two scores is `tvals[s:e]`. The `nnar_helps_baseline` flag also compares neural-only error with baseline error, rather than combined-model error with baseline error. This invalidates the tuning rankings and related improvement/rank-correlation claims used in the installed configuration.

   **Reproduction:** `check_stage2_target.py` executes the actual stage2 function bodies with inexpensive mocked fits: actual cases 100, perfect baseline 100, residual correction 0. Correct RMSE is 0; stage2 reports 100 for both baseline and hybrid. See `stage2_target_output.json`.

   **Fix proposed:** score baseline and clipped hybrid against actual cases; evaluate residual-only predictions against a clearly defined residual target if needed; derive the improvement flag from hybrid versus baseline. Regenerate the search outputs and installed settings after repairing the remaining tuning issues below. Changing one expression alone is insufficient.

2. **High: inner validation uses residuals fitted with validation observations.** Stage1 fits SARIMA on the whole outer training set (`residual_search.py:350–372`). Stage2 slices those cached residuals for earlier validation origins (`:518–528`). The baseline is refitted on each prefix, but its NNAR inputs come from another SARIMA that has already seen the inner validation periods. This is inner-validation leakage, even if the outer test is never passed directly to fitting.

   **Fix proposed:** at each validation origin, fit SARIMA on that prefix, discard initialization residuals, train the scaler and NNAR on those prefix residuals, and recursively predict the subsequent case counts. Freeze all settings before a genuinely untouched final test. Audit the offline search cutoffs against the app's last-52-week holdout before calling that holdout independent.

3. **High: offline AIC values use different observation windows.** `residual_search.py:357–361` disables stationarity/invertibility enforcement and leaves the likelihood burn at its model-dependent default. Higher seasonal orders can exclude many more initial observations from the likelihood. Sorting their AICs therefore does not provide a sound common-window comparison. The runtime fixes burn to 53, but its single pinned candidate cannot retrospectively repair offline selection.

   **Reproduction:** holding d=0 and D=1 fixed, changing seasonal P from 1 to 2 changes the default burn from 106 to 158. With the same 400 observations, only 294 versus 242 contribute to the likelihood. See `check_sarima_diagnostics.py` and `sarima_diagnostic_checks.json`.

   **Fix proposed:** establish a comparable likelihood basis and a documented differencing decision, then rerun the candidate search. Record log likelihood, parameter count, effective sample count and burn per candidate. Treat AIC as relative fit/complexity evidence, not measured forecast accuracy.

4. **High: tuning does not reproduce deployment.** Offline NNAR uses Adam, the sklearn default alpha (0.0001), and scaling of both inputs and targets (`residual_search.py:327–337`). Runtime uses L-BFGS, alpha 1, per-feature input scaling and an unscaled target (`weekly/model.py:159–164`). Offline SARIMA disables constraints, retains initialization residuals, and its input reader drops missing rows (`residual_search.py:193`). Runtime enables constraints, masks the first 53 residuals and retains missing week positions. The installed configuration itself acknowledges nine dropped Dengue observations in the search.

   **Fix proposed:** share the operational estimator and calendar/missing-data preparation with the tuning workflow. Retune lags and hidden width under the actual deployed pipeline. A custom ReLU autoregressive MLP is a valid NNAR-style model, but should not be described as an exact reproduction of another package's `nnetar` defaults or ensemble.

5. **Medium: Ljung–Box p-values are unadjusted.** `weekly/model.py:222` and `residual_search.py:366` omit `model_df`. For these fitted SARIMA residuals, use the appropriate estimated AR/MA parameter count, conventionally p+q+P+Q, with lag greater than that count. The default zero produces larger p-values. The statistic tests autocorrelation jointly through the selected lag; it does not test only lag 52. Rejection indicates remaining serial correlation, not proof that a neural network can learn it. Non-rejection does not prove independence or absence of nonlinear predictability.

   **Fix proposed:** adjust degrees of freedom, discard initialization residuals, preserve gaps, record statistic/lag/df/p-value, and review the diagnostic lag relative to residual sample size. The minimum 156-week history minus burn53 leaves only 103 residual positions, making the fixed lag52 diagnostic particularly weak as a routine rule.

6. **Limitations: ADF and uncertainty claims must match the code.** Weekly ADF runs on the raw series and stores only a p-value (`weekly/model.py:190`). Its `autolag='AIC'` chooses lag length for the ADF regression, not SARIMA orders. Candidate differencing is configured elsewhere. Gapped/constant series are honestly marked unavailable. Runtime uncertainty is explicitly hybrid plus/minus training SARIMA residual RMSE, not a calibrated prediction interval (`:249–252`). One retrospective origin cannot establish general predictive accuracy or superiority.

   **Fix proposed:** document the actual role of ADF; if stationarity-guided identification is intended, add a justified differencing procedure and transformed-series diagnostics. Compare against SARIMA and seasonal naive at multiple chronological origins, then assess final untouched performance. Calibrate uncertainty separately if probability coverage is to be claimed.

## What passed inspection

The live runtime uses actual statistical estimators, not placeholders. Missing observations remain positional; NNAR uses complete lag examples without compressing gaps; feature scaling is trained on training data; future residuals are predicted recursively; failure remains explicit; SARIMA-only stays separately labelled. Retrospective metric arithmetic compares case predictions with actual cases using the same finite-observation mask for both models. The wrong-target defect is in offline tuning, not that runtime metric calculation.

Historical monthly code correctly supplies Ljung–Box model degrees of freedom. Its ADF logic differs from weekly logic, and it tolerates neural convergence warnings. Monthly tests therefore cannot certify weekly methodology.

## Verification and limits

- Ran weekly and revision45 suites: **93 passed; 1 fixture setup error** due to denied access to pytest's temporary directory. A targeted retry with a workspace temporary directory hit the same permissions issue. This is not a model assertion failure.
- Independently reran the wrong-target reproduction successfully. A converged small synthetic SARIMA fit also matched independent AIC and Ljung–Box Q arithmetic exactly. Its unadjusted p-value was 0.932446 versus 0.843334 with model degrees of freedom, matching an independent chi-square calculation. These are arithmetic checks, not real-data accuracy estimates.
- Inspected active entrypoint, protocol resolution, deployed config, weekly fitting/evaluation, monthly comparators, offline search and archived tuning outputs.
- Did not rerun the full disease search, certify the source workbook, or validate current real-data forecast accuracy. Search configs reference a `tradeoffanalysis` source directory absent from this checkout. No browser or visual audit was needed for this methodology scope and none is claimed.
- No production fixes applied: corrected settings require coherent repair and a verified rerun of the search, not speculative replacements. Historical outputs are preserved as evidence.

## Scoped quality scorecards

Counts refer to the five requested method components, not an accuracy percentage or exhaustive numerical verification. Categories can overlap. A zero means no demonstrated defect in that scoped category, not universal correctness.

| Category | Observed defects | Assessment |
|---|---|---|
| Methodology usefulness/completeness | 2 / 5 | AIC selection and NNAR tuning cannot currently substantiate the installed choices. |
| Analytical clarity | 1 / 5 | Offline Ljung–Box interpretation overstates evidence of neural learnability. ADF is explicitly descriptive in current weekly documentation. |
| Visual/interaction consistency | N/A | Source-methodology audit, no rendered UI review. |

| Category | Observed defects | Assessment |
|---|---|---|
| Source authority/confidence | 0 / 5 | Genuine statsmodels/sklearn implementations identified; source-data authenticity not audited. |
| Calculation/value accuracy | 2 / 5 | Ljung–Box fitted-model p-values and NNAR tuning scores have demonstrated defects. |
| Within-chart agreement | N/A | No chart review. |
| Complete source details | N/A | No dashboard evidence-surface review. |
| Cross-workflow consistency | 2 / 5 | SARIMA and NNAR settings/preprocessing differ between search and runtime. |
| Data-quality controls | 2 / 5 | Offline SARIMA/NNAR use compressed missing rows and initialization residuals. Runtime protections are stronger. |
| Conclusion support | 2 / 5 | Lowest-AIC selection and tuned-NNAR claims need corrected search evidence. |

## Governing references

- [Statsmodels ADF](https://www.statsmodels.org/stable/generated/statsmodels.tsa.stattools.adfuller.html): unit-root null and ADF regression autolag.
- [Statsmodels Ljung–Box](https://www.statsmodels.org/stable/generated/statsmodels.stats.diagnostic.acorr_ljungbox.html): model degrees of freedom and lag handling.
- [Statsmodels SARIMAX FAQ](https://www.statsmodels.org/stable/examples/notebooks/generated/statespace_sarimax_faq.html): initialization and interpretation of residuals.
- [Scikit-learn MLPRegressor](https://scikit-learn.org/stable/modules/generated/sklearn.neural_network.MLPRegressor.html): optimizer, regularization and network settings.
