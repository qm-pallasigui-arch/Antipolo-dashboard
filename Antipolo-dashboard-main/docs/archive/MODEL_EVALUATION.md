# Weekly model evaluation status

Weekly statistical methodology remains pending adviser approval. The application supplies configurable SARIMA candidate orders/seasonality, residual NNAR lags/network settings, training/history requirements, a chronological holdout, explicit week 53 and missing-value policies, and provisional uncertainty. It does not establish final weekly search bounds, rolling folds, forecast origins, seasonal period 52, or a 52-week holdout.

Hybrid SARIMA–NNAR is primary. SARIMA-only is separately fit/reported. Hybrid failure is explicit and never replaced by SARIMA-only. A single 52-point forecast is sliced for display. The retrospective holdout fits all components on pre-holdout observations; both models share the same finite-actual evaluation positions. Missing actuals are documented and excluded from scoring. MAE/RMSE retain zeros, MAPE uses nonzero actuals with denominator coverage, and WAPE is undefined when total actuals are zero.

All-age technical evaluation, ages 5–19 confirmed-only thesis evaluation, and synthetic demonstrations stay separate. Dataset and protocol eligibility are independently checked. Existing 2025 testing is **retrospective**, not prospective. No previously reported performance number constitutes a weekly or school-aged validation result.

The current shaded range is Hybrid ± training SARIMA residual RMSE, clipped at zero. It is provisional and uncalibrated, without a formal coverage claim. Its exact method is included in technical details and exports.

Future prospective support records issue timestamps, original forecast snapshots, model/context metadata, eventual observations, per-horizon/model errors, and reporting-delay revisions. Reconciliation appends evidence and does not overwrite original predictions. This structural support does not claim completed prospective validation.

See [WEEKLY_SYSTEM.md](../../WEEKLY_SYSTEM.md) for detailed protocol configuration and limitations. Historical model evaluation, including earlier monthly benchmarks, is preserved in [docs/historical-pre-weekly/MODEL_EVALUATION.md](../historical-pre-weekly/MODEL_EVALUATION.md).
