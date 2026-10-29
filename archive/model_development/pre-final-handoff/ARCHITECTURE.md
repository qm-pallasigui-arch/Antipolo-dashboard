# Current architecture

The October 29, 2026 decision fixes the forecasting family as Prophet + XGBoost. Earlier study/model directions are superseded.

| Layer | Location | Responsibility |
|---|---|---|
| Presentation | dashboard/monthly/ui.py, views.py, components.py, charts.py | Authenticated monthly views, candidate review, grouped forecast controls, rankings |
| Security | security.py, admin.py | Password hashes, revocable sessions, CSRF/origin validation, roles |
| Canonical data | domain.py | Upload validation, reporting states, source provenance, preserved calendar |
| Readiness | forecasting/readiness.py | All seven candidates; explicit pending state until approved policy exists |
| Base model | forecasting/prophet_model.py | Prophet fitting on actual observed dates |
| Residual model | forecasting/xgboost_residual.py | XGBoost correction with explicit seed and thread count |
| Hybrid contract | forecasting/hybrid.py | Both components required; nonnegative base-plus-correction output |
| Evaluation support | forecasting/features.py, evaluation.py | Chronological-error provenance checks and metric utilities; final workflow pending |
| Forecast service | services/forecast_service.py | RBAC, readiness, twelve months, versioned runs, explicit failures, batch grouping |
| Ranking service | services/ranking_service.py | Comparable forecast totals, descending ranks, up to five results |
| Analytical repositories | repositories/forecast_repository.py, ranking_repository.py | Result persistence and current-model filtering |
| Existing local store | store.py | SQLite users, datasets, notifications, reports, audit and annotations |
| Reports | reports.py | Historical data, forecast and ranking snapshots, HTML/JSON/CSV |

The UI never constructs model objects from the Prophet or XGBoost libraries. The default hybrid has no approved training workflow and therefore cannot fit live models. A future approved workflow must orchestrate chronological base forecasts, residual training/features and independent evaluation using the component modules. Passing a callable in tests is dependency injection, not model-family selection or production methodology approval.

Available source years remain distinct from missing 2020/2022. Nulls are never interpreted as zero. Dates are never synthesized into an uninterrupted observed sequence. All candidates share the forecast origin at the canonical dataset calendar endpoint; an earlier last observation is recorded separately as training_cutoff.

Historical forecast payloads are preserved. Only completed records with current model name/version and a successful XGBoost correction are exposed. Dataset signatures isolate results. Ranking records contain group ID, signature, months, per-block source run IDs, totals, ranks and warnings. Activation does not delete old results.

Storage extraction is incremental: forecast/ranking repositories exist, while account/dataset/notification operations remain in the existing local Store. Full Supabase migration is pending; see [migration plan](docs/SUPABASE_MIGRATION.md). No claim of live PostgreSQL persistence is made.
