# SARIMA + NNAR residual-hybrid search

Dataset-agnostic pipeline. Selection uses training data only; the test set is scored once, after selection is locked.

## Run configuration

- Data: `../tradeoffanalysis/weekly/weekly_leptospirosis_dated.csv` (column `cases`)
- Seasonal period: **52** (by config)
- Gap profile (days): {'7': 529} - positional indexing, seasonality aligned by row not calendar
- Train n=478, test n=52, train mean 0.55, test mean 2.13
- Grid: p[1, 2] d[0, 1] q[0] P[1, 2] D[1] Q[0, 1]
- Residual filter: `non_white` (alpha=0.05)
- Grid tier **fast** - 16 candidates, 8 worker processes

## Stage 1 - SARIMA grid (train only)

- Fitted 16 candidates, 0 rejected
- Survived filter `non_white`: 16
- Shortlisted 4 by AIC

## Stage 2 - NNAR optimisation (train only)

| Order | Seasonal | AIC | Ljung-Box p | white? | NNAR | Val RMSE base | Val RMSE hybrid | NNAR helps? | vs baseline | per-window hybrid RMSE |
|---|---|---:|---|:---:|---|---:|---:|:---:|---:|---|
| (2, 0, 0) | (2, 1, 0, 52) | 1080.05 | 52:1.93e-07, 104:1.81e-06 | no | lag12 k2 | 1.46 | 1.46 | NO | +0.1% | 2025-02-21: 2.1<br>2024-02-23: 1.7<br>2023-02-24: 0.6 |
| (2, 0, 0) | (2, 1, 1, 52) | 1081.73 | 52:2.1e-07, 104:2.09e-06 | no | lag6 k5 | 1.85 | 1.86 | yes | +0.3% | 2025-02-21: 2.7<br>2024-02-23: 2.1<br>2023-02-24: 0.7 |
| (2, 1, 0) | (2, 1, 0, 52) | 1094.21 | 52:8.68e-09, 104:4.55e-08 | no | lag12 k2 | 1.72 | 1.72 | yes | +0.0% | 2025-02-21: 2.2<br>2024-02-23: 2.3<br>2023-02-24: 0.7 |
| (2, 1, 0) | (2, 1, 1, 52) | 1095.80 | 52:9.76e-09, 104:5.9e-08 | no | lag12 k2 | 2.05 | 2.05 | yes | +0.1% | 2025-02-21: 3.0<br>2024-02-23: 2.2<br>2023-02-24: 1.0 |

## Selected

**SARIMA(2, 0, 0)(2, 1, 0, 52) + NNAR(lag 12, k 2)**
- lowest hybrid_val_rmse among 4 refined candidates

### Ranking diagnostics

- Chosen by `hybrid_val_rmse`: `SARIMA(2, 0, 0)(2, 1, 0, 52)`
- Would be chosen by AIC: `SARIMA(2, 0, 0)(2, 1, 0, 52)`
- Would be chosen by 'NNAR actually helps': `SARIMA(2, 1, 0)(2, 1, 0, 52)`
- NNAR made validation *worse* for **1 of 4** candidates
- Rank correlation between AIC and hybrid validation RMSE: 0.8 (near zero or negative means AIC does not predict accuracy here)

- SARIMA order (2, 0, 0) seasonal (2, 1, 0, 52)
- NNAR lag 12, k 2

## Residuals of the selected model

- **ljung_box_p**: {'52': 1.930690997417901e-07, '104': 1.8128193075009256e-06}
- **white_noise**: False
- **learnable_by_nnar**: True
- **verdict**: structure remains in the residuals (non-white), as the filter targets; no horizon showed a statistically significant NNAR improvement

## Evaluation by horizon (fixed origin)

| Horizon | n | Metric | SARIMA | +NNAR | Seasonal-naive | Improvement | DM p |
|---:|---:|---|---:|---:|---:|---:|---:|
| 4 | 4 | RMSE | 1.02 | 0.78 | 0.87 | -23.5% | 0.2604 |
| 4 | 4 | MAE | 0.95 | 0.75 | 0.75 | -21.3% | 0.2604 |
| 4 | 4 | MAPE | 116.21 | 86.67 | 66.67 | -25.4% | 0.2604 |
| 13 | 13 | RMSE | 0.65 | 0.53 | 0.68 | -18.4% | 0.5499 |
| 13 | 13 | MAE | 0.45 | 0.38 | 0.46 | -14.2% | 0.5499 |
| 13 | 13 | MAPE | 114.73 | 90.00 | 75.00 | -21.6% | 0.5499 |
| 26 | 26 | RMSE | 0.94 | 0.88 | 1.06 | -7.2% | 1.0 |
| 26 | 26 | MAE | 0.71 | 0.65 | 0.73 | -7.6% | 1.0 |
| 26 | 26 | MAPE | 81.11 | 72.31 | 73.44 | -10.8% | 1.0 |
| 52 | 52 | RMSE | 3.59 | 3.56 | 3.73 | -0.7% | 0.7045 |
| 52 | 52 | MAE | 1.57 | 1.55 | 1.87 | -1.3% | 0.7045 |
| 52 | 52 | MAPE | 77.80 | 74.07 | 112.17 | -4.8% | 0.7045 |

The DM p-value is computed once per horizon on the absolute-error loss differential (hybrid minus SARIMA), not separately per metric - hence the repeated value down each horizon block. Negative mean differential favours the hybrid.

MAPE zero-actual exclusions: h=4: 1, h=13: 9, h=26: 10, h=52: 18

### Stratum split (below / at or above 70 actual)

| Horizon | Stratum | n | Metric | SARIMA | +NNAR |
|---:|---|---:|---|---:|---:|
| 26 | < 70 | 26 | RMSE | 0.94 | 0.88 |
| 26 | < 70 | 26 | MAE | 0.71 | 0.65 |
| 26 | < 70 | 26 | MAPE | 81.11 | 72.31 |
| 52 | < 70 | 52 | RMSE | 3.59 | 3.56 |
| 52 | < 70 | 52 | MAE | 1.57 | 1.55 |
| 52 | < 70 | 52 | MAPE | 77.80 | 74.07 |

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