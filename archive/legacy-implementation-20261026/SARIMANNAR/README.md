# Corrected offline SARIMA-NNAR selection

The controlling workflow is documented in [the methodology reconciliation](../docs/FORECAST_METHODOLOGY_2026-10-17.md).

```powershell
python SARIMANNAR/residual_search.py --dataset eligible-dataset.json --output evidence/corrected-selection --install
```

Supply a validated active dataset JSON with source metadata, confirmed cases and ages 5-19. No eligible dataset is currently available. Without it, corrected configurations and final-test results remain pending.

The CLI runs Dengue, Leptospirosis and Measles, or the repeated `--disease` selections. It writes a checkpointed candidate audit, a lock before final testing, final evaluation arrays/metrics, and a disease methodology report. `--install` updates the runtime registry only after every requested disease completes successfully.

All estimators are shared with `dashboard/weekly/estimators.py`. Search is offline only: 144 SARIMA candidates, common-window AIC screening of the top ten successful fits, validation-based SARIMA selection, and 96 NNAR configurations with three fixed seeds scored on hybrid case forecasts. Final-test values never enter selection.

Existing `rs_*`, `rt_*` and `pin_*` files are historical results from the audited workflow. Their old `--config` CLI and rankings are superseded; they are not evidence from the corrected search. The previous source remains available in Git history.
