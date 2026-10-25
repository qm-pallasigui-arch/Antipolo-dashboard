# Provisional Model Validation — Not Thesis-Validated

Disease: Measles. Source: source.csv.

Dataset fingerprint: `1213272e96c5c69f69f899fc73b8aa9f1023e910f3997a34c5b37add3afea94e`

Lock: `9357182d219fcb0478a5dc2d98b7e62c01a7c090da9879e90a5ce73f663e9e4e`

- training: [2016, 1] through [2021, 36]
- validation: [2021, 37] through [2022, 36]
- final_test: [2022, 37] through [2023, 36]

Selected SARIMA: [0, 0, 0] [0, 0, 0, 52], no exogenous inputs.
Selected NNAR: lag 4, hidden nodes 4, alpha 0.1; ReLU/L-BFGS; seeds 42/137/2026; production seed 42.

| Period / model | RMSE | MAE | MAPE (%) |
|---|---:|---:|---:|
| Validation / sarima | 11.171736 | 11.000000 | 84.253807 |
| Validation / hybrid_seed_median | 11.171736 | 11.000000 | 84.253807 |
| Final Test / hybrid | 10.245074 | 10.038462 | 76.395239 |
| Final Test / sarima | 11.226685 | 11.038462 | 84.263493 |

Validation Hybrid errors are seed medians; Final Test uses seed 42. Full-precision errors, seed coverage, ADF and Ljung–Box diagnostics are in report.json.

Hybrid performed better on RMSE and MAE in the Final Test. MAPE is supporting evidence, with zero-actual exclusions reported.
The Hybrid forecast was substantially smoother than observed week-to-week Final Test changes.
Hybrid peak timing error: -1 chronological weeks; peak magnitude error: -13.000 cases.
Direction agreement: 0.0% across 51 consecutive observed pairs; supplementary only.
Future first-to-last changes: raw SARIMA +0.000, NNAR correction +0.000, clipped Hybrid +0.000 cases. Inspect component paths for intervening rises and falls.
A held-out test is historical evidence; it cannot establish that a future smooth decline will occur. No variability was added to the predictions.

## Peak evidence

Actual peak: {'week': [2022, 38], 'position': 2, 'count': 16.0}

| Model | Peak week | Peak count | Timing error (positions) | Magnitude error (cases) | Direction agreement |
|---|---|---:|---:|---:|---:|
| hybrid | [2022, 37] | 3.000000 | -1 | -13.000000 | 0.00% |
| sarima | [2022, 37] | 2.000000 | -1 | -14.000000 | 0.00% |

Descriptive heuristics, not proof of accuracy or statistical seasonality. Earliest tied peak; observed positions only; directions exclude pairs crossing missing observations.

## Warnings and assumptions

- Not Thesis-Validated
- Population, case classification and provenance retain their supplied verification status; this run does not establish research eligibility.

## Provisional future 52-week path

Horizon positions are relative to the last supplied usable week. Calendar labels are omitted where the future source calendar is unverified. Values below are rounded for reading only; JSON retains full precision.

| Horizon week | Raw SARIMA | NNAR correction | Final Hybrid |
|---:|---:|---:|---:|
| 1 | 2.000000 | 1.000000 | 3.000000 |
| 2 | 2.000000 | 1.000000 | 3.000000 |
| 3 | 2.000000 | 1.000000 | 3.000000 |
| 4 | 2.000000 | 1.000000 | 3.000000 |
| 5 | 2.000000 | 1.000000 | 3.000000 |
| 6 | 2.000000 | 1.000000 | 3.000000 |
| 7 | 2.000000 | 1.000000 | 3.000000 |
| 8 | 2.000000 | 1.000000 | 3.000000 |
| 9 | 2.000000 | 1.000000 | 3.000000 |
| 10 | 2.000000 | 1.000000 | 3.000000 |
| 11 | 2.000000 | 1.000000 | 3.000000 |
| 12 | 2.000000 | 1.000000 | 3.000000 |
| 13 | 2.000000 | 1.000000 | 3.000000 |
| 14 | 2.000000 | 1.000000 | 3.000000 |
| 15 | 2.000000 | 1.000000 | 3.000000 |
| 16 | 2.000000 | 1.000000 | 3.000000 |
| 17 | 2.000000 | 1.000000 | 3.000000 |
| 18 | 2.000000 | 1.000000 | 3.000000 |
| 19 | 2.000000 | 1.000000 | 3.000000 |
| 20 | 2.000000 | 1.000000 | 3.000000 |
| 21 | 2.000000 | 1.000000 | 3.000000 |
| 22 | 2.000000 | 1.000000 | 3.000000 |
| 23 | 2.000000 | 1.000000 | 3.000000 |
| 24 | 2.000000 | 1.000000 | 3.000000 |
| 25 | 2.000000 | 1.000000 | 3.000000 |
| 26 | 2.000000 | 1.000000 | 3.000000 |
| 27 | 2.000000 | 1.000000 | 3.000000 |
| 28 | 2.000000 | 1.000000 | 3.000000 |
| 29 | 2.000000 | 1.000000 | 3.000000 |
| 30 | 2.000000 | 1.000000 | 3.000000 |
| 31 | 2.000000 | 1.000000 | 3.000000 |
| 32 | 2.000000 | 1.000000 | 3.000000 |
| 33 | 2.000000 | 1.000000 | 3.000000 |
| 34 | 2.000000 | 1.000000 | 3.000000 |
| 35 | 2.000000 | 1.000000 | 3.000000 |
| 36 | 2.000000 | 1.000000 | 3.000000 |
| 37 | 2.000000 | 1.000000 | 3.000000 |
| 38 | 2.000000 | 1.000000 | 3.000000 |
| 39 | 2.000000 | 1.000000 | 3.000000 |
| 40 | 2.000000 | 1.000000 | 3.000000 |
| 41 | 2.000000 | 1.000000 | 3.000000 |
| 42 | 2.000000 | 1.000000 | 3.000000 |
| 43 | 2.000000 | 1.000000 | 3.000000 |
| 44 | 2.000000 | 1.000000 | 3.000000 |
| 45 | 2.000000 | 1.000000 | 3.000000 |
| 46 | 2.000000 | 1.000000 | 3.000000 |
| 47 | 2.000000 | 1.000000 | 3.000000 |
| 48 | 2.000000 | 1.000000 | 3.000000 |
| 49 | 2.000000 | 1.000000 | 3.000000 |
| 50 | 2.000000 | 1.000000 | 3.000000 |
| 51 | 2.000000 | 1.000000 | 3.000000 |
| 52 | 2.000000 | 1.000000 | 3.000000 |
