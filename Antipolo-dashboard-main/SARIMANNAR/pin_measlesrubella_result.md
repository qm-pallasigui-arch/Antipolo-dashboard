# SARIMA + NNAR residual-hybrid search

Dataset-agnostic pipeline. Selection uses training data only; the test set is scored once, after selection is locked.

## Run configuration

- Data: `../tradeoffanalysis/weekly/weekly_measlesrubella_dated.csv` (column `cases`)
- Seasonal period: **52** (by config)
- Gap profile (days): {'7': 529} - positional indexing, seasonality aligned by row not calendar
- Train n=478, test n=52, train mean 5.12, test mean 2.10
- Grid: p[2] d[1] q[0] P[2] D[1] Q[1]
- Residual filter: `non_white` (alpha=0.05)
- Grid tier **pinned-aic** - 1 candidates, 4 worker processes

## Stage 1 - SARIMA grid (train only)

- Fitted 1 candidates, 0 rejected
- Survived filter `non_white`: 1
- Shortlisted 1 by AIC

## Stage 2 - NNAR optimisation (train only)

| Order | Seasonal | AIC | Ljung-Box p | white? | NNAR | Val RMSE base | Val RMSE hybrid | NNAR helps? | vs baseline | per-window hybrid RMSE |
|---|---|---:|---|:---:|---|---:|---:|:---:|---:|---|
| (2, 1, 0) | (2, 1, 1, 52) | 2093.37 | 52:7.53e-08, 104:0.00363 | no | lag3 k5 | 35.25 | 34.91 | yes | -1.0% | 2025-02-21: 60.2<br>2024-02-23: 31.8<br>2023-02-24: 12.8 |

## Selected

**SARIMA(2, 1, 0)(2, 1, 1, 52) + NNAR(lag 3, k 5)**
- lowest hybrid_val_rmse among 1 refined candidates

### Ranking diagnostics

- Chosen by `hybrid_val_rmse`: `SARIMA(2, 1, 0)(2, 1, 1, 52)`
- Would be chosen by AIC: `SARIMA(2, 1, 0)(2, 1, 1, 52)`
- Would be chosen by 'NNAR actually helps': `SARIMA(2, 1, 0)(2, 1, 1, 52)`
- NNAR made validation *worse* for **0 of 1** candidates
- Rank correlation between AIC and hybrid validation RMSE: nan (near zero or negative means AIC does not predict accuracy here)

- SARIMA order (2, 1, 0) seasonal (2, 1, 1, 52)
- NNAR lag 3, k 5

## Residuals of the selected model

- **ljung_box_p**: {'52': 7.530573619048493e-08, '104': 0.0036312806542065155}
- **white_noise**: False
- **learnable_by_nnar**: True
- **verdict**: structure remains in the residuals (non-white), as the filter targets; NNAR improved significantly at horizon(s) [52]

## Evaluation by horizon (fixed origin)

| Horizon | n | Metric | SARIMA | +NNAR | Seasonal-naive | Improvement | DM p |
|---:|---:|---|---:|---:|---:|---:|---:|
| 4 | 4 | RMSE | 2.44 | 1.81 | 1.22 | -25.8% | 0.4115 |
| 4 | 4 | MAE | 2.11 | 1.56 | 1.00 | -26.0% | 0.4115 |
| 4 | 4 | MAPE | 156.15 | 97.92 | 55.56 | -37.3% | 0.4115 |
| 13 | 13 | RMSE | 7.34 | 2.35 | 2.24 | -67.9% | 0.528 |
| 13 | 13 | MAE | 6.51 | 1.94 | 1.92 | -70.2% | 0.528 |
| 13 | 13 | MAPE | 296.72 | 99.38 | 77.50 | -66.5% | 0.528 |
| 26 | 26 | RMSE | 8.92 | 2.79 | 2.36 | -68.7% | 0.1979 |
| 26 | 26 | MAE | 8.34 | 2.39 | 2.04 | -71.3% | 0.1979 |
| 26 | 26 | MAPE | 348.72 | 99.72 | 76.06 | -71.4% | 0.1979 |
| 52 | 52 | RMSE | 8.56 | 2.56 | 2.18 | -70.1% | 0.0028 |
| 52 | 52 | MAE | 8.17 | 2.10 | 1.81 | -74.3% | 0.0028 |
| 52 | 52 | MAPE | 395.67 | 99.85 | 72.30 | -74.8% | 0.0028 |

The DM p-value is computed once per horizon on the absolute-error loss differential (hybrid minus SARIMA), not separately per metric - hence the repeated value down each horizon block. Negative mean differential favours the hybrid.

MAPE zero-actual exclusions: h=4: 1, h=13: 3, h=26: 4, h=52: 10

### Stratum split (below / at or above 70 actual)

| Horizon | Stratum | n | Metric | SARIMA | +NNAR |
|---:|---|---:|---|---:|---:|
| 26 | < 70 | 26 | RMSE | 8.92 | 2.79 |
| 26 | < 70 | 26 | MAE | 8.34 | 2.39 |
| 26 | < 70 | 26 | MAPE | 348.72 | 99.72 |
| 52 | < 70 | 52 | RMSE | 8.56 | 2.56 |
| 52 | < 70 | 52 | MAE | 8.17 | 2.10 |
| 52 | < 70 | 52 | MAPE | 395.67 | 99.85 |

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