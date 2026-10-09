# Background forecast jobs

Generate Forecast submits a durable job and returns immediately after preflight
validation. The UI polls every two seconds, shows the stage, candidate/window,
NNAR initialization and elapsed time, and offers Cancel Forecast. Navigation
and horizon changes do not restart fitting.

The first complete Decision 90 search is still expensive. The grids, three
validation windows, five NNAR initializations, lock, holdout and future-refit
rules have not been reduced. Numerical work runs in a separate process, with
one job active at a time and one BLAS thread by default to keep the UI responsive.

## Local use

Restart an older running app process, then run `python app.py` as usual. No new
packages or separate worker command are needed. The application starts a hidden
worker supervisor automatically on the first job. It exits after five idle
minutes and starts again when needed.

The default database is `.forecast-jobs/jobs.sqlite3` in the repository. Set
`WEEKLY_JOB_DIR` to a durable writable directory to choose another location.
The directory stores validated input, complete results and a worker log, and
is excluded from Git and Docker builds. Keep it private alongside source data.

Closing a tab does not stop a job. A page refresh retains its job handle in
browser session storage. After switching disease or losing browser state, click
Generate Forecast with the same active data and settings to reconnect to a job
or load its completed result. Exact signatures include dataset identity, all
records and metadata, disease, model version and configuration. A re-upload with
different metadata is intentionally a different signature.

Duplicate requests share a job. Cancellation terminates its fitting subprocess,
including during a long numerical fit. Cancelled/failed attempts never become
successful cached results. Retrying rotates the job ID, so an old cancel or
poll cannot affect a new attempt. If a supervisor dies, the next supervisor
marks abandoned running jobs failed; it does not silently use partial output.

For a manually managed worker, set `WEEKLY_JOB_AUTOSTART=0` in the web process
and run this on the same host with the same `WEEKLY_JOB_DIR`:

```text
python -m dashboard.weekly.jobs worker --idle-seconds 0
```

Use one persistent host/volume for this SQLite queue. It is not a distributed
multi-host queue. `WEEKLY_WORKER_THREADS` controls numerical-library threads;
the default is 1. Increasing it may reduce UI responsiveness on a small host.

## Vercel dashboard with a persistent worker

Vercel cannot host this long-lived local supervisor. When `VERCEL` is set, the
application requires a remote worker instead of launching a subprocess or
writing a supposedly durable cache to ephemeral serverless storage.

1. Deploy `Dockerfile.worker` on an always-running Python/container host. Mount
   a durable volume at `/data`. Keep one service instance using that volume.
   The API entrypoint is `dashboard.weekly.job_service:app`; `/healthz` is its
   health check. This service must remain alive while a job is running.
2. Set a strong shared secret as `WEEKLY_JOB_SERVICE_TOKEN` on the worker host.
   Do not commit the value. The worker rejects missing or invalid bearer tokens.
3. On the Vercel dashboard project, set `WEEKLY_JOB_SERVICE_URL` to the worker's
   HTTPS base URL and `WEEKLY_JOB_SERVICE_TOKEN` to the same secret, then redeploy.
   Tokens stay on the servers, not in browser stores or JavaScript.

The dashboard sends short submit/status/cancel requests to the worker. It sends
the validated Active Dataset and the fixed model protocol, not raw files. The
worker service owns the persistent queue and cache. HTTPS is required except
for localhost development. No paid service or remote deployment was created by
this change; a host URL and shared token must be configured before Vercel can
use it.

## Verification and limits

Automated tests cover atomic duplicate submission, persistent cache reuse,
signature isolation, progress, cancellation of a real subprocess, a real worker
CLI failure path, worker-lease recovery, stale attempts, remote authentication,
short API calls, UI polling and transient network errors.

Verification on 10 October 2026: the full suite passed 277 tests; after the final
cached-result and cancellation-message changes, 115 targeted tests passed.
Pyflakes and whitespace checks passed. A real worker subprocess failure path
and cancellation of a real subprocess are included in the automated checks.

The initial browser run verified progress, navigation and cancellation, but its
synthetic completed-result fixture lacked context and produced a rendering
error. The fixture and HTTP-error assertions were corrected. Automatic approval
review then hit its usage limit, so the corrected browser run was not executed.
Completed-result rendering is covered by an automated UI test; final browser
rendering remains unverified.

`python tests/browser_forecast_jobs.py` exercises progress, navigation,
cancellation, completion and disk-cache reuse using synthetic worker responses.
It requires the existing local Playwright installation and Microsoft Edge and
stores timestamped evidence under `evidence/forecast-jobs/`. It does not fit a
research dataset or establish full-grid speed.

The full real-workbook search has not been benchmarked. Background execution
removes the long web request; persistent cache avoids rerunning identical
completed jobs. It does not make a new complete statistical search instantaneous.
