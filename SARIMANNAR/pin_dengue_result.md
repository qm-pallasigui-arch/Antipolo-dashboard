# SARIMA + NNAR residual-hybrid search

Dataset-agnostic pipeline. Selection uses training data only; the test set is scored once, after selection is locked.

## Run configuration

- Data: `../tradeoffanalysis/weekly/weekly_dengue_dated.csv` (column `cases`)
- Seasonal period: **52** (by config)
- Gap profile (days): {'7': 529} - positional indexing, seasonality aligned by row not calendar
- Train n=478, test n=43, train mean 43.29, test mean 102.33
- Grid: p[2] d[0] q[0] P[2] D[1] Q[1]
- Residual filter: `non_white` (alpha=0.05)
- Grid tier **pinned-aic** - 1 candidates, 4 worker processes

## Stage 1 - SARIMA grid (train only)

- Fitted 1 candidates, 0 rejected
- Survived filter `non_white`: 1
- Shortlisted 1 by AIC

## Stage 2 - NNAR optimisation (train only)

| Order | Seasonal | AIC | Ljung-Box p | white? | NNAR | Val RMSE base | Val RMSE hybrid | NNAR helps? | vs baseline | per-window hybrid RMSE |
|---|---|---:|---|:---:|---|---:|---:|:---:|---:|---|
| (2, 0, 0) | (2, 1, 1, 52) | 2709.09 | 52:1.1e-05, 104:3.09e-06 | no | lag9 k8 | 49.09 | 48.49 | yes | -1.2% | 2025-04-25: 54.2<br>2024-04-19: 43.5<br>2023-04-14: 47.7 |

## Selected

**SARIMA(2, 0, 0)(2, 1, 1, 52) + NNAR(lag 9, k 8)**
- lowest hybrid_val_rmse among 1 refined candidates

### Ranking diagnostics

- Chosen by `hybrid_val_rmse`: `SARIMA(2, 0, 0)(2, 1, 1, 52)`
- Would be chosen by AIC: `SARIMA(2, 0, 0)(2, 1, 1, 52)`
- Would be chosen by 'NNAR actually helps': `SARIMA(2, 0, 0)(2, 1, 1, 52)`
- NNAR made validation *worse* for **0 of 1** candidates
- Rank correlation between AIC and hybrid validation RMSE: nan (near zero or negative means AIC does not predict accuracy here)

- SARIMA order (2, 0, 0) seasonal (2, 1, 1, 52)
- NNAR lag 9, k 8

## Residuals of the selected model

- **ljung_box_p**: {'52': 1.1011777395624208e-05, '104': 3.0909760408938028e-06}
- **white_noise**: False
- **learnable_by_nnar**: True
- **verdict**: structure remains in the residuals (non-white), as the filter targets; no horizon showed a statistically significant NNAR improvement

## Evaluation by horizon (fixed origin)

| Horizon | n | Metric | SARIMA | +NNAR | Seasonal-naive | Improvement | DM p |
|---:|---:|---|---:|---:|---:|---:|---:|
| 4 | 4 | RMSE | 17.97 | 14.59 | 46.36 | -18.8% | 1.0 |
| 4 | 4 | MAE | 15.83 | 12.66 | 46.00 | -20.0% | 1.0 |
| 4 | 4 | MAPE | 20.61 | 16.10 | 58.58 | -21.9% | 1.0 |
| 13 | 13 | RMSE | 24.15 | 23.35 | 36.78 | -3.3% | 1.0 |
| 13 | 13 | MAE | 22.81 | 21.55 | 34.85 | -5.5% | 1.0 |
| 13 | 13 | MAPE | 35.59 | 33.77 | 50.87 | -5.1% | 1.0 |
| 26 | 26 | RMSE | 31.56 | 31.86 | 34.09 | +0.9% | 0.8919 |
| 26 | 26 | MAE | 27.16 | 26.93 | 31.35 | -0.9% | 0.8919 |
| 26 | 26 | MAPE | 28.40 | 27.69 | 35.77 | -2.5% | 0.8919 |

The DM p-value is computed once per horizon on the absolute-error loss differential (hybrid minus SARIMA), not separately per metric - hence the repeated value down each horizon block. Negative mean differential favours the hybrid.

MAPE zero-actual exclusions: none - all actuals non-zero, so no MAPE exclusions apply

### Stratum split (below / at or above 70 actual)

| Horizon | Stratum | n | Metric | SARIMA | +NNAR |
|---:|---|---:|---|---:|---:|
| 26 | < 70 | 9 | RMSE | 28.09 | 28.19 |
| 26 | < 70 | 9 | MAE | 27.77 | 27.80 |
| 26 | < 70 | 9 | MAPE | 45.22 | 45.22 |
| 26 | >= 70 | 17 | RMSE | 33.26 | 33.63 |
| 26 | >= 70 | 17 | MAE | 26.84 | 26.47 |
| 26 | >= 70 | 17 | MAPE | 19.49 | 18.41 |

## Figures

- `None` - actual vs SARIMA vs hybrid vs seasonal-naive, one panel per horizon
- `None` - error growth as the horizon extends

## Limitations

- **Bounded search.** Grid tier `pinned-aic` searched 1 specifications. No further exclusions recorded. A bounded grid is not an exhaustive one.
- Fixed-origin evaluation: horizon h is scored on the FIRST h test periods only. Short horizons therefore describe a narrow slice of the test year and are not representative; a rolling-origin variant would give many more error pairs.
- Diebold-Mariano p-values are small-sample; with few periods they have low power and should be read as indicative only.
- MAPE is undefined at zero actuals; those periods are excluded and the count is reported with every metric block.
- Positional (not calendar) indexing means seasonality is aligned by row; irregular reporting gaps cause slight drift from the true calendar period (see gap profile above).
- NNAR and MAPE carry small run-to-run variance; single-run results are not averaged.