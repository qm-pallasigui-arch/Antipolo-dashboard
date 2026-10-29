# Thesis implementation readiness

Model-family decision: **Prophet + XGBoost, finalized October 29, 2026**.

Implemented: manual-source CSV/XLSX workflow; monthly canonical states; seven-candidate readiness inventory; archive isolation; fixed hybrid contract; separate model component wrappers; explicit component failure; twelve-calendar-month forecast service; comparable projected-total ranking; fewer-than-five handling; current-model result filtering; local persistence; RBAC; current UI/report terminology.

Not yet thesis-ready:

- Approved readiness thresholds and rules for internal/trailing gaps.
- Approved chronological residual-error generation and feature construction; full training orchestration.
- Train/evaluation split, tuning protocol, metrics/scaling and uncertainty method.
- Real Prophet/XGBoost fitting and accuracy validation with the approved methodology.
- Full Supabase repository migration and live persistence verification.
- AWS deployment and operational verification.

The application explicitly blocks live forecast execution while methodology configuration is missing. Synthetic contract tests verify software behavior only. They cannot establish forecast accuracy, a successful Supabase deployment or approved research methodology.

No official data are fabricated or automatically activated. Historical source Top Five is not a forecast. Projected rankings compare only valid represented blocks over a common twelve-month period. Schools are intended beneficiaries; the source has no school identifiers and does not support school-level forecasts.
