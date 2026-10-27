# SARIMA + NNAR residual-hybrid search

Dataset-agnostic pipeline. Selection uses training data only; the test set is scored once, after selection is locked.

## Run configuration

- Data: `../tradeoffanalysis/weekly/weekly_measlesrubella_dated.csv` (column `cases`)
- Seasonal period: **52** (by config)
- Gap profile (days): {'7': 529} - positional indexing, seasonality aligned by row not calendar
- Train n=478, test n=52, train mean 5.12, test mean 2.10
- Grid: p[1, 2] d[0, 1] q[0] P[1, 2] D[1] Q[0, 1]
- Residual filter: `non_white` (alpha=0.05)
- Grid tier **fast** - 16 candidates, 4 worker processes

## Stage 1 - SARIMA grid (train only)

- Fitted 16 candidates, 0 rejected
- Survived filter `non_white`: 16
- Shortlisted 4 by AIC

## Stage 2 - NNAR optimisation (train only)

| Order | Seasonal | AIC | Ljung-Box p | white? | NNAR | Val RMSE base | Val RMSE hybrid | NNAR helps? | vs baseline | per-window hybrid RMSE |
|---|---|---:|---|:---:|---|---:|---:|:---:|---:|---|
| (2, 1, 0) | (2, 1, 1, 52) | 2093.37 | 52:7.53e-08, 104:0.00363 | no | lag9 k2 | 22.34 | 22.32 | yes | -0.1% | 2025-02-21: 3.0<br>2024-02-23: 2.8<br>2023-02-24: 61.2 |
| (2, 1, 0) | (2, 1, 0, 52) | 2109.62 | 52:4.5e-09, 104:4.73e-06 | no | lag3 k5 | 36.32 | 35.87 | yes | -1.3% | 2025-02-21: 31.2<br>2024-02-23: 12.0<br>2023-02-24: 64.5 |
| (2, 0, 0) | (2, 1, 1, 52) | 2130.85 | 52:6.32e-23, 104:1.95e-12 | no | lag6 k2 | 11.03 | 10.84 | yes | -1.8% | 2025-02-21: 10.8<br>2024-02-23: 14.7<br>2023-02-24: 7.1 |
| (1, 1, 0) | (2, 1, 1, 52) | 2143.94 | 52:1.48e-08, 104:0.00138 | no | lag3 k5 | 38.54 | 38.21 | yes | -0.8% | 2025-02-21: 13.8<br>2024-02-23: 64.3<br>2023-02-24: 36.6 |

## Selected

**SARIMA(2, 0, 0)(2, 1, 1, 52) + NNAR(lag 6, k 2)**
- lowest hybrid_val_rmse among 4 refined candidates

### Ranking diagnostics

- Chosen by `hybrid_val_rmse`: `SARIMA(2, 0, 0)(2, 1, 1, 52)`
- Would be chosen by AIC: `SARIMA(2, 1, 0)(2, 1, 1, 52)`
- Would be chosen by 'NNAR actually helps': `SARIMA(2, 0, 0)(2, 1, 1, 52)`
- NNAR made validation *worse* for **0 of 4** candidates
- Rank correlation between AIC and hybrid validation RMSE: 0.4 (near zero or negative means AIC does not predict accuracy here)

- SARIMA order (2, 0, 0) seasonal (2, 1, 1, 52)
- NNAR lag 6, k 2

## Residuals of the selected model

- **ljung_box_p**: {'52': 6.32390244358096e-23, '104': 1.9529295456786154e-12}
- **white_noise**: False
- **learnable_by_nnar**: True
- **verdict**: structure remains in the residuals (non-white), as the filter targets; NNAR improved significantly at horizon(s) [26]

## Evaluation by horizon (fixed origin)

| Horizon | n | Metric | SARIMA | +NNAR | Seasonal-naive | Improvement | DM p |
|---:|---:|---|---:|---:|---:|---:|---:|
| 4 | 4 | RMSE | 1.45 | 1.19 | 1.22 | -18.1% | 0.3513 |
| 4 | 4 | MAE | 1.24 | 1.03 | 1.00 | -17.5% | 0.3513 |
| 4 | 4 | MAPE | 77.04 | 57.00 | 55.56 | -26.0% | 0.3513 |
| 13 | 13 | RMSE | 4.56 | 2.23 | 2.24 | -51.1% | 0.181 |
| 13 | 13 | MAE | 3.98 | 1.78 | 1.92 | -55.4% | 0.181 |
| 13 | 13 | MAPE | 186.84 | 87.10 | 77.50 | -53.4% | 0.181 |
| 26 | 26 | RMSE | 4.43 | 2.62 | 2.36 | -41.0% | 0.0032 |
| 26 | 26 | MAE | 3.99 | 2.20 | 2.04 | -44.7% | 0.0032 |
| 26 | 26 | MAPE | 166.42 | 89.22 | 76.06 | -46.4% | 0.0032 |
| 52 | 52 | RMSE | 3.46 | 2.45 | 2.18 | -29.1% | 0.6697 |
| 52 | 52 | MAE | 2.82 | 2.03 | 1.81 | -27.8% | 0.6697 |
| 52 | 52 | MAPE | 123.12 | 86.15 | 72.30 | -30.0% | 0.6697 |

The DM p-value is computed once per horizon on the absolute-error loss differential (hybrid minus SARIMA), not separately per metric - hence the repeated value down each horizon block. Negative mean differential favours the hybrid.

MAPE zero-actual exclusions: h=4: 1, h=13: 3, h=26: 4, h=52: 10

### Stratum split (below / at or above 70 actual)

| Horizon | Stratum | n | Metric | SARIMA | +NNAR |
|---:|---|---:|---|---:|---:|
| 26 | < 70 | 26 | RMSE | 4.43 | 2.62 |
| 26 | < 70 | 26 | MAE | 3.99 | 2.20 |
| 26 | < 70 | 26 | MAPE | 166.42 | 89.22 |
| 52 | < 70 | 52 | RMSE | 3.46 | 2.45 |
| 52 | < 70 | 52 | MAE | 2.82 | 2.03 |
| 52 | < 70 | 52 | MAPE | 123.12 | 86.15 |

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