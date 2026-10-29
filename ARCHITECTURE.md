# Current prototype architecture

The final handoff authorizes provisional execution of the fixed Prophet + XGBoost family. Standalone Prophet is only the baseline comparator. No competing model-family registry exists.

| Layer | Modules | Responsibility |
|---|---|---|
| UI | ui, views, components, charts | Nine modules including Security; provisional labels, charts, rankings, comparison |
| Source domain | domain | Canonical CSV/XLSX validation and immutable source states |
| Configuration/readiness | forecasting/config, readiness | One provisional settings object; seven candidates; explicit readiness states |
| Model adapter | forecasting/adapter | Canonical fields and actual timestamps; no hidden source file |
| Base model | forecasting/prophet_model | Prophet fitting and fitted/future values |
| Residual features | forecasting/features | Replaceable residual construction; calendar lags with missing values |
| Correction | forecasting/xgboost_residual | XGBoost fitting and recursive residual prediction; explicit failures |
| Hybrid workflow | forecasting/pipeline, hybrid | Provisional composition and fixed architecture contract |
| Evaluation | forecasting/evaluation | Generic chronological split; training-only scale; baseline/hybrid comparison |
| Application services | services/forecast_service, ranking_service | RBAC, batch groups, twelve-month output, projected totals and rankings |
| Analytical persistence | repositories/forecast_repository, ranking_repository | Mode/configuration/version isolation, atomic run and monthly-value writes |
| Database boundary | repositories/database | Server-side Supabase/PostgreSQL connection, private schema, transaction and SQL compatibility layer |
| Application store | store | Users, datasets, source bytes, quality/readiness payloads, notifications, audit, annotations, reports |

The canonical dataset is never overwritten by model processing. Actual calendar gaps remain null and carry their source states. The prototype fits on observed timestamps; unknown lag values remain NaN for XGBoost. Recursive predictions bridge trailing gaps without creating observed values. Twelve future forecast months start after the common canonical endpoint, not after a compressed sequence or a block-specific shortened calendar.

All generated results are provisional. A generic last-reported-year evaluation refits both components on earlier data; residuals within that training subset remain in-sample. This limitation is disclosed. Chapter 3 can replace residual construction, features and evaluation via the module boundaries. The current implementation does not approve a final methodology through a Boolean flag.

Successful runs store status hybrid_completed, is_prototype=true, methodology_status=provisional, configuration/hash, model version, dataset/version, run/group ID, observed cutoff and calendar origin. Twelve monthly values and baseline values are persisted transactionally in forecast_values. Errors preserve prior valid results but never create substitute hybrid outputs. Ranking reads require a coherent group, mode, configuration and calendar; fewer than five valid blocks yields an unavailable Top Five while retaining full ranks.

Store operations use SQLite locally or Supabase PostgreSQL when configured. The shared database boundary handles parameter binding, identity IDs, conflict handling and transaction locking. Password hashes, revocable sessions and server-side role checks remain application-managed in either backend. PostgreSQL uses a private schema and SSL; cloud operation requires an explicit signing secret. Existing SQLite data require a deliberate migration, not an automatic destructive conversion.

Archives and the supplied original script are never imported. The default runtime has exactly one hybrid pipeline. Future final results must have a separately approved configuration/workflow and remain segregated from prototype artifacts.
