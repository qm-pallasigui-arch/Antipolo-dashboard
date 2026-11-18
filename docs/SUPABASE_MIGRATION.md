# Supabase PostgreSQL and AWS deployment

The PostgreSQL persistence boundary is implemented; no target cloud connection or deployment was configured during this handoff.

## Configure a new cloud environment

Use the Supabase direct connection or session pooler from the project's Connect panel. Set these server-side deployment secrets/settings:

```text
MONTHLY_DATABASE_URL=<PostgreSQL connection string>
MONTHLY_DATABASE_SCHEMA=antipolo_app
MONTHLY_SECRET_KEY=<strong persistent signing secret>
MONTHLY_COOKIE_SECURE=1
PROTOTYPE_MODE=true
```

The app uses psycopg with SSL required and a private schema. The database role must be able to create/use that schema and its tables. Do not expose this schema through a public client API. Users/roles, sessions, dataset source bytes/metadata/data-quality, runs, individual forecast values, rankings, notifications, reports and audit records all use this connection. This retains the application's existing password/session implementation; it is not an implicit migration to Supabase Auth.

Connection failures do not silently fall back to local SQLite. Tables are created additively; no existing columns/tables are dropped. PostgreSQL advisory transaction locks serialize activation and account safety checks across workers. Forecast run completion and its monthly values are committed together.

## Verify in staging

Set `TEST_SUPABASE_DATABASE_URL` to a dedicated test connection and run `pytest tests/test_supabase_persistence.py`. The test creates a random private test schema and removes only that schema. It verifies restart persistence for datasets, roles, forecasts, values, rankings, reports and notifications; role rejection and new-dataset result isolation are also checked. Without the test URL it is explicitly skipped.

## Existing local data

Do not switch an existing installation assuming its SQLite data will automatically appear in PostgreSQL. First back up the local database and signing key, inventory rows/source signatures, then migrate to staging through an explicit export/import procedure. Preserve account IDs, dataset provenance, null/zero distinctions and legacy result classifications. Never relabel old predictions as the new hybrid. Reconcile identity sequences after importing IDs. Validate row counts, hashes, activation atomicity and result isolation before cutover. Retain the original SQLite backup for rollback. No automatic migration was executed in this task.

## AWS container

The Dockerfile installs the application, pinned model libraries, PostgreSQL driver and CPU runtime library. Its `dashboard.monthly.runtime` launcher starts Gunicorn and the dedicated forecast queue worker, listens on PORT (default 8050) and exposes `/healthz`. The launcher stops both services if either exits and handles shutdown signals. Forecast computation runs in a supervised child process, outside HTTP requests. Deploy behind HTTPS with the settings above supplied through the AWS environment/secrets mechanism. Keep one forecast supervisor initially; database claims serialize model batches. Direct Gunicorn/Procfile hosting must also run `python -m dashboard.monthly.worker` against the same database and configuration. Monitor queue delay, failures and memory before changing concurrency. The service does not create synthetic source data on startup.

The container was prepared but not built/deployed in an AWS account during this handoff. Live connection, migration and deployment are distinct operational verification steps.

### Next sprint acceptance: performance and deployment

1. Measure idle/active browser polling and queue-supervisor query load; adapt idle polling while preserving prompt cross-tab completion and cancellation feedback.
2. Against a dedicated PostgreSQL test database, verify competing queue claims, cancellation versus ranking publication, stale-lease recovery and retained history across web/worker restarts. The existing optional persistence test alone does not establish this.
3. Build and run the Linux container; verify `/healthz`, queued startup, real model completion, SIGTERM cleanup and abrupt supervisor loss without orphaned model/CmdStan processes. Verify both services use identical configuration and schema.
4. Perform a staging backup/restore drill covering source bytes, users, forecast values, queue/history and schema identity sequences. Compare counts and source signatures before considering cutover.

Required inputs: a dedicated test PostgreSQL URL and a container runtime. No production migration, credential changes or deployment is authorized by this checklist. Manual screen-reader acceptance from the accessibility sprint remains separate.
