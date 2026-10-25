# Dengue provisional assessment — Not Thesis-Validated

Source: repository Antipolo_Disease_Surveillance_2016-2025.xlsx, unchanged as requested.

The full parameter search completed, but the strict Hybrid Final Test could not start because its NNAR lag window includes a missing residual at [[2024, 53]].

Dataset fingerprint: `01b6f52cc4ccf6059702bfa4fcd9470d9e36e5bb7235f78fd253f12d3c01ab9c`

Search: 144 SARIMA candidates and 96 NNAR configurations, with three seeds each. NNAR configurations successful for all seeds: 16.

Selected SARIMA: [0, 1, 1] [1, 0, 0, 52].
Selected NNAR: lag 2, hidden nodes 8, alpha 0.1, production seed 42.

- training: [2016, 1] through [2024, 2]
- validation: [2024, 3] through [2025, 1]
- final_test: [2025, 2] through [2025, 53]

| Period / model | RMSE | MAE | MAPE (%) |
|---|---:|---:|---:|
| Validation SARIMA | 43.129127 | 38.200915 | 77.183064 |
| Validation Hybrid (seed median) | 43.148213 | 38.255854 | 77.255319 |
| Final Test SARIMA (supplemental) | 46.756811 | 36.280323 | 30.830243 |
| Final Test Hybrid | Unavailable | Unavailable | Unavailable |

Final Test SARIMA coverage: 52 scored observations, 0 missing exclusions, 0 zero exclusions from MAPE, 52 MAPE-valid observations.

## Answers about shape and future forecasts

- Hybrid versus SARIMA on Final Test: cannot be determined because Hybrid initialization was blocked.
- Actual test peak: [2025, 32], 193 cases.
- SARIMA test peak: [2025, 33], 91.456371 cases; timing error +1 chronological weeks; magnitude error -101.543629 cases.
- SARIMA direction agreement: 50.98% on 51 adjacent observed pairs. This is supplementary, not proof of seasonal accuracy.
- Hybrid reproduction of major rises/falls and peak timing: unavailable.
- Component causing a future decline: unavailable; no provisional future path was generated after the blocked Hybrid test.
- Support for a smooth future Hybrid decline: not established by this run. Earlier fixed-preset sample forecasts are not evidence for the selected provisional configuration.
- Resulting provisional 52-week Hybrid path: intentionally not generated. Final Test must complete first.

## Source assumptions

- Provisional assumption: 1590 rows with unverified reporting status are included as supplied; historical completeness is not established.
- Provisional calendar assumption for 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025: retain supplied Week 53; otherwise use 52 positions. This is not source calendar verification.

## Next step

Establish from the data provider whether the blank Week 53 is a missing report or a nonexistent source-calendar week. Do not replace it with zero without evidence. Recursive residual warm-up would extend the method and requires an explicit decision; it was not enabled.

The signed provisional lock remains separate from the research registry. No parameter was retuned using these test outcomes. Full precision and baseline diagnostic arrays are in sarima-only-holdout.json; candidate failures are in search.json.
