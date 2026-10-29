# Supabase PostgreSQL migration plan

Status: planned, not executed. Local SQLite remains authoritative. No production credentials or target Supabase project were supplied for this change.

1. Back up the existing SQLite database and signing key. Inventory table schemas, counts, dataset signatures, forecast model metadata, reports and account identifiers without exposing password hashes or session tokens.
2. Create a private PostgreSQL application schema through an explicit migration. Separate repositories for datasets, users, notifications, forecasts, rankings and reports must replace remaining local SQL usage. Preserve transactional activation, unique usernames, one active dataset and per-user notification read state.
3. Add forecast-run and forecast-value tables with dataset ID/signature, run/group ID, block, month, value, model name/version, status, generated timestamp and warnings. Add ranking-run and ranking-item tables with run/group ID, signature, horizon, rank, block, total and source forecast run ID. Use foreign keys and uniqueness constraints for run/month and ranking/block.
4. Keep old forecasts in a legacy namespace or explicitly labeled historical table. Never relabel prototype predictions as final hybrid output. Refresh derived readiness under the new approved policy without changing source hashes or values.
5. Import into staging first. Verify row counts, source hashes, null/zero preservation, all seven candidate summaries, roles, notification visibility and current-model filtering. Check rollback on failed activation and failed forecast persistence.
6. Test authenticated server-side PostgreSQL access with SSL. Credentials belong in deployment secrets, never browser code. Define access controls before exposing any API. Revoke old sessions or migrate them through an explicit security decision.
7. Run integration tests against an isolated Supabase project for restart persistence, duplicate writes, concurrent activation, forecast/ranking transactions, cross-dataset isolation and RBAC. Mock tests are insufficient to claim live persistence.
8. Cut over only after staging verification; preserve a rollback copy. Remove obsolete columns only in a separate reviewed migration after inspecting retained data.

This cleanup adds a local rankings table non-destructively and stores final-model metadata in separate new forecast payloads. No existing tables or columns are dropped. The current application does not yet connect to Supabase; the migration remains an explicit acceptance gap.
