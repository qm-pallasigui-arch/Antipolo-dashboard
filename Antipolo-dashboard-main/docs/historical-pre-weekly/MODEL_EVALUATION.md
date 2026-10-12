# Model evaluation - 27 September 2026

Freshly executed original-working-tree and revised-model runs are separate below. All-age records are not ages 5-19 confirmed-case evidence. No eligible age-specific extract was supplied. Synthetic results are separate demonstrations, never pooled with real observations.

The revised hybrid is mandatory even where it loses. The revised hybrid is worse than its SARIMA-only benchmark for Leptospirosis and Measles-Rubella; it also loses to seasonal naive for those two categories. Dengue only narrowly beats seasonal naive. No general superiority is established.

## Artifacts and reproduction

- `reconciliation/original-evaluation.json`: fresh baseline arrays/metrics from initial uncommitted working tree, prior to edits.
- `reconciliation/revised-evaluation.json`: current arrays, every SARIMA candidate, ADF/ACF/PACF, neural settings, warnings, rolling folds, holdout and production.
- `reconciliation/revised-evaluation-initial.json`: intermediate revised run retained; not the final result.
- `reconciliation/evaluate.py`: current evaluator; `python -m reconciliation.evaluate reconciliation/revised-evaluation.json`.
- `reconciliation/verify_evaluation.py`: independent array arithmetic, alignment, component sum, split boundaries, and error-band verification.
- `reconciliation/numerical-verification.json`: actual verification outcomes.
- Initial code/data are recoverable in baseline ZIP. `reconciliation/reproduce_baseline.py` reconstructs the original evaluation against an extracted snapshot; that added wrapper was not separately rerun. Do not run historical evidence scripts against revised imports and overwrite old outputs.

All ten series have 120 months, January 2016-December 2025. Earlier diagnostic evaluations are2023 and 2024; final holdout2025; production2026. Search runs within each training window. Prior human exposure to 2025 means algorithmic exclusion does not establish a pristine confirmatory holdout. A future prospective validation should be considered by the adviser.

## Preserved historical reported values

These are prior handoff findings, not revised output: Dengue 25.17%, Leptospirosis67.08%, category then called Measles162.58% selected-model WAPE; naive34.90%, 55.86%, 50.00%. Fresh baseline results below independently reproduce their rounded values.

## Original implementation: all_age

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

## Original implementation: synthetic

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

## Revised mandatory hybrid: all_age

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

## Revised mandatory hybrid: synthetic

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

## Selected revised configurations

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

## Interpretation and formulas

MAE is mean absolute error; RMSE is square root of mean squared error; MAPE averages absolute relative error only for nonzero actuals; WAPE divides total absolute error by total absolute actuals. Percentage metrics multiply by100. Undefined denominator returns null, never a perfect score. All methods use identical holdout dates.

The hybrid adds the untruncated SARIMA mean and neural residual prediction before clipping to zero. SARIMA-only is separately clipped. Its independent benchmark uses the best valid AIC candidate, even if another candidate is needed for a feasible neural component. No neural rejection occurred in these 40 evaluated/production windows, so the benchmark and hybrid base orders coincide.

Revised runs include hybrid_success and hybrid_with_warnings; inspect warnings and per-candidate rejections rather than interpreting success as adequate model fit. Finite NNAR results with a convergence warning remain explicitly warned results, not evidence of convergence. The residual autocorrelation warnings and particularly large Measles-Rubella error require critical review, not post-hoc tuning on 2025.

The shaded range uses the largest of 36 prior absolute hybrid errors. It is descriptive, uses holdout errors after scoring, and is not a calibrated95% prediction interval.

Original and revised code use different SARIMA identification and residual initialization policies. The before/after comparison evaluates the full authorized change; it does not isolate a causal benefit of mandatory architecture. Original fitted environments are recorded in both JSONs and environment-freeze.txt. Repository pins were not reinstalled or validated.
