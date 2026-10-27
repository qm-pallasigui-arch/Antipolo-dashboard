# Monthly ICD-10 architecture

The October 24, 2026 handoff supersedes the weekly design. app.py reuses the shared Dash/Flask application, asset stack, logging and deployment, but installs only dashboard.monthly.ui. Retired weekly and disease-specific source is isolated in archive/legacy-implementation-20261026 and excluded from deployment. Old local caches are never loaded.

| Layer | Files in dashboard/monthly | Responsibility |
| --- | --- | --- |
| Presentation | ui.py, views.py, components.py, charts.py | Shared shell/components, eight authenticated views, monthly charts, preview, downloads |
| Security | security.py, admin.py | Password hashes, revocable sessions, CSRF/origin checks, roles, bootstrap and accounts |
| Domain | domain.py | Four states, normalization, annual history, provenance and standalone eligibility |
| Persistence | store.py | SQLite staging, activation, source bytes, audit, notifications, annotations |
| Forecasting | forecast.py | Eligibility-gated service and replaceable adapter contract |
| Reporting | reports.py | Persistent HTML/JSON/CSV report snapshots for every block |

## Dataset lifecycle

CSV/XLSX input validates canonical columns, years, months, descriptions, nonnegative integers, duplicates and annual coverage. A present annual entry with missing months is rejected because the approved four-state vocabulary does not contain an arbitrary missing-month category. Only city-unavailable and absent-Top-5 periods generate null calendar rows. Explicit zeros remain unchanged; three consecutive zeros trigger warnings.

Pending candidates are independent from active data. Explicit activation uses BEGIN IMMEDIATE and a unique active-state index: retirement, activation, audit and notifications commit together. Source bytes and SHA-256 remain with normalized payloads. Content signatures hash observations and study provenance; identical content keeps its signature. Candidate IDs identify uploads separately.

Current forecasts are selected by signature and block. Old forecasts remain historical but cannot appear under a changed signature. Reports preserve source and forecast snapshots. Browser stores contain selection IDs and revision counters, never authoritative datasets or permissions.

## Security boundary

Every protected request verifies the opaque session token against SQLite and retrieves the current active user's role. This includes Dash layout, dependency and callback endpoints. Session cookies are signed, HttpOnly and SameSite=Strict; sessions expire in eight hours and are revoked on logout/account changes.

Mutating callbacks check administrator permission. Viewers may generate reports and update only their own notification read state. Pending datasets and validation-error notifications are admin-only. Forms use CSRF tokens; JSON callbacks reject cross-origin and non-JSON POSTs. No permissive CORS is configured. Login throttling applies after ten failures within fifteen minutes. Audits cover login/failure/logout, users, uploads, activation, annotations, forecast execution and report generation.

## Forecast abstraction

The service validates authorization → horizon → active dataset → eligibility → registered engine. Engines receive all 120 classified calendar months, including 24 null months for eligible blocks. No deletion, zero filling or interpolation precedes the engine.

The model-independent adapter protocol is `generate(observations, horizon)`. The default prototype adapter translates the current wrapper into selected_output, model_metadata, evaluation and warnings. The service validates finite nonnegative consultation counts and horizon, adds calendar dates and trusted run provenance, and stores completion/failure notifications. The obsolete multi-stage engine compatibility bridge has been removed; all adapters use this single contract.

PrototypeForecastAdapter alone converts the 120 calendar rows to 96 observed consultation counts in chronological order. Unavailable 2020/2022 months are omitted without zero filling or interpolation. This compresses calendar gaps and is explicitly disclosed in every run: it is experimental infrastructure, not an approved treatment of missing years. Charts and reports preserve the original calendar and nulls. Forecast dates begin after the last observed calendar month.

TODO THESIS-METHOD: Final forecasting algorithm and candidate model set are not yet approved. No final adapter is implemented. Prototype CV MAE does not establish a final metric set or horizon-specific evaluation. The supplied icd_forecast dependency is still required for actual inference; imports are lazy so data and reporting remain usable without it.

## Retained infrastructure

The [shared monthly component library](docs/MONTHLY_UI_COMPONENTS.md) defines typography, panels, forms, statuses, tables and chart themes. Login/account pages use the same stylesheet as Dash; exported report charts use the same figure builder.

The shared Dash instance, assets, logging and WSGI deployment remain. New SQLite tables are isolated from the old source/model semantics. Existing source files and local edits are preserved. Legacy tests are archived with their implementation; the active suite covers the monthly system only.

The current forecast contract is synchronous. Prototype inference may be expensive and is synchronous. For longer-running use, the retained job infrastructure can be adapted with authorization and signature binding without changing the other modules.
