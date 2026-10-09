# SARIMA + NNAR residual-hybrid search

Dataset-agnostic pipeline. Selection uses training data only; the test set is scored once, after selection is locked.

## Run configuration

- Data: `../tradeoffanalysis/weekly/weekly_dengue_dated.csv` (column `cases`)
- Seasonal period: **52** (by config)
- Gap profile (days): {'7': 529} - positional indexing, seasonality aligned by row not calendar
- Train n=478, test n=43, train mean 43.29, test mean 102.33
- Grid: p[1, 2] d[0, 1] q[0] P[1, 2] D[1] Q[0, 1]
- Residual filter: `non_white` (alpha=0.05)
- Grid tier **fast** - 16 candidates, 4 worker processes

## Stage 1 - SARIMA grid (train only)

- Fitted 16 candidates, 0 rejected
- Survived filter `non_white`: 9
- Shortlisted 4 by AIC

## Stage 2 - NNAR optimisation (train only)

| Order | Seasonal | AIC | Ljung-Box p | white? | NNAR | Val RMSE base | Val RMSE hybrid | NNAR helps? | vs baseline | per-window hybrid RMSE |
|---|---|---:|---|:---:|---|---:|---:|:---:|---:|---|
| (2, 0, 0) | (2, 1, 1, 52) | 2709.09 | 52:1.1e-05, 104:3.09e-06 | no | lag9 k8 | 51.91 | 51.28 | yes | -1.2% | 2025-04-25: 54.7<br>2024-04-19: 58.2<br>2023-04-14: 41.0 |
| (2, 0, 0) | (2, 1, 0, 52) | 2723.85 | 52:1.04e-08, 104:9.81e-11 | no | lag9 k2 | 43.47 | 43.60 | yes | +0.3% | 2025-04-25: 41.7<br>2024-04-19: 48.3<br>2023-04-14: 40.8 |
| (1, 0, 0) | (2, 1, 1, 52) | 2745.78 | 52:5.26e-07, 104:1.24e-05 | no | lag3 k2 | 46.48 | 46.08 | yes | -0.9% | 2025-04-25: 55.4<br>2024-04-19: 45.7<br>2023-04-14: 37.1 |
| (1, 0, 0) | (2, 1, 0, 52) | 2766.20 | 52:4.34e-12, 104:1.47e-11 | no | lag3 k2 | 44.81 | 44.45 | yes | -0.8% | 2025-04-25: 55.7<br>2024-04-19: 40.7<br>2023-04-14: 37.0 |

## Selected

**SARIMA(2, 0, 0)(2, 1, 0, 52) + NNAR(lag 9, k 2)**
- lowest hybrid_val_rmse among 4 refined candidates

### Ranking diagnostics

- Chosen by `hybrid_val_rmse`: `SARIMA(2, 0, 0)(2, 1, 0, 52)`
- Would be chosen by AIC: `SARIMA(2, 0, 0)(2, 1, 1, 52)`
- Would be chosen by 'NNAR actually helps': `SARIMA(2, 0, 0)(2, 1, 0, 52)`
- NNAR made validation *worse* for **0 of 4** candidates
- Rank correlation between AIC and hybrid validation RMSE: -0.4 (near zero or negative means AIC does not predict accuracy here)

- SARIMA order (2, 0, 0) seasonal (2, 1, 0, 52)
- NNAR lag 9, k 2

## Residuals of the selected model

- **ljung_box_p**: {'52': 1.0357071129341565e-08, '104': 9.810683022267764e-11}
- **white_noise**: False
- **learnable_by_nnar**: True
- **verdict**: structure remains in the residuals (non-white), as the filter targets; no horizon showed a statistically significant NNAR improvement

## Evaluation by horizon (fixed origin)

| Horizon | n | Metric | SARIMA | +NNAR | Seasonal-naive | Improvement | DM p |
|---:|---:|---|---:|---:|---:|---:|---:|
| 4 | 4 | RMSE | 18.21 | 19.68 | 46.36 | +8.1% | 0.5525 |
| 4 | 4 | MAE | 16.49 | 18.18 | 46.00 | +10.2% | 0.5525 |
| 4 | 4 | MAPE | 21.40 | 23.60 | 58.58 | +10.2% | 0.5525 |
| 13 | 13 | RMSE | 29.83 | 30.72 | 36.78 | +3.0% | 1.0 |
| 13 | 13 | MAE | 28.06 | 29.04 | 34.85 | +3.5% | 1.0 |
| 13 | 13 | MAPE | 44.00 | 45.46 | 50.87 | +3.3% | 1.0 |
| 26 | 26 | RMSE | 29.28 | 29.75 | 34.09 | +1.6% | 1.0 |
| 26 | 26 | MAE | 26.60 | 27.10 | 31.35 | +1.9% | 1.0 |
| 26 | 26 | MAPE | 32.15 | 32.86 | 35.77 | +2.2% | 1.0 |

The DM p-value is computed once per horizon on the absolute-error loss differential (hybrid minus SARIMA), not separately per metric - hence the repeated value down each horizon block. Negative mean differential favours the hybrid.

MAPE zero-actual exclusions: none - all actuals non-zero, so no MAPE exclusions apply

### Stratum split (below / at or above 70 actual)

| Horizon | Stratum | n | Metric | SARIMA | +NNAR |
|---:|---|---:|---|---:|---:|
| 26 | < 70 | 9 | RMSE | 36.71 | 37.38 |
| 26 | < 70 | 9 | MAE | 35.94 | 36.55 |
| 26 | < 70 | 9 | MAPE | 58.46 | 59.50 |
| 26 | >= 70 | 17 | RMSE | 24.44 | 24.78 |
| 26 | >= 70 | 17 | MAE | 21.66 | 22.10 |
| 26 | >= 70 | 17 | MAPE | 18.22 | 18.76 |

## Figures

- `None` - actual vs SARIMA vs hybrid vs seasonal-naive, one panel per horizon
- `None` - error growth as the horizon extends

## Limitations

- **Bounded search.** Grid tier `fast` searched 16 specifications. Excludes q>0, p=0, p=3. On dengue this forgoes the q sweep, where MAPE improved monotonically with q (23.11 at q=0 to 21.98 at q=3). A bounded grid is not an exhaustive one.
- Fixed-origin evaluation: horizon h is scored on the FIRST h test periods only. Short horizons therefore describe a narrow slice of the test year and are not representative; a rolling-origin variant would give many more error pairs.
- Diebold-Mariano p-values are small-sample; with few periods they have low power and should be read as indicative only.
- MAPE is undefined at zero actuals; those periods are excluded and the count is reported with every metric block.
- Positional (not calendar) indexing means seasonality is aligned by row; irregular reporting gaps cause slight drift from the true calendar period (see gap profile above).
- NNAR and MAPE carry small run-to-run variance; single-run results are not averaged.