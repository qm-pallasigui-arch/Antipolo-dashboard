# Weekly system architecture

`app.py` creates the weekly layout and registers only `dashboard.weekly.ui` callbacks against the shared Dash/Flask app. Browser session stores hold active data and the current model result; source preparation and pending review use in-memory stores. Old monthly callback modules remain available for historical tests, but normal startup does not import them.

| Module | Responsibility |
| --- | --- |
| `dashboard/weekly/transform.py` | Source CSV/XLSX inspection, aliases, per-sheet disease hints, week-by-year unpivoting, explicit fallback mappings, original/prepared provenance |
| `dashboard/weekly/data.py` | Internal weekly validation, lossless source observations, quality findings, eligibility, dataset fingerprints and explicit activation |
| `dashboard/weekly/model.py` | Configurable weekly SARIMA candidates, residual NNAR, 52-point path, chronological evaluation, cache identity, failure diagnostics |
| `dashboard/weekly/outputs.py` | Provenance-rich exports, source-date display summaries, exclusive-create forecast snapshots and append-only reconciliations |
| `dashboard/weekly/ui.py` | Five-section interface, pending/active lifecycle, freshness, warnings, forecasts and technical inspection |
| `dashboard/weekly/presentation.py` | Human-readable statuses, source facts, quality summaries and progressive disclosure |
| `dashboard/weekly/charts.py` | Weekly observations, model series and provisional range |
| `dashboard/weekly/settings.py` | Administrator-supplied model and study requirements; no ordinary-user configuration editor |
| `dashboard/assets/revision39.css`, `review.js` | Responsive interface, scrollable review dialog and keyboard focus containment |

Uploading triggers reading, automatic preparation and a before/after review. Unresolved mappings open ordinary dropdowns. Only Confirm & Use Data changes the active store. Cancel discards the pending review, preserving current data. Explicit source facts are applied and revalidated at confirmation. Transformation history stays attached to active data and detailed exports. Activation/reset invalidates model results. A full dataset/configuration/disease signature prevents incompatible cache reuse. Horizon, history range and aggregation controls are not inputs to the training callback.

The weekly model uses ordered reporting-year/morbidity-week positions, retains missing values, and requires source calendar metadata across year boundaries. No monthly aggregate enters fitting. Hybrid candidate retries stay inside the supplied mechanism. SARIMA-only remains separately identified when Hybrid fails. Unapproved settings and source limitations remain visible in outputs.

Prospective snapshots use content-addressed JSON files created exclusively. Reconciliation verifies the original hash and writes a new revision without editing originals. Set `WEEKLY_SNAPSHOT_DIR` to a durable writable location for deployment. Browser session state and local file snapshots are lightweight prototype storage, not an authenticated research repository.

See [WEEKLY_SYSTEM.md](WEEKLY_SYSTEM.md) for the complete implemented contract and unresolved methodology. The previous architecture, preserved including pre-existing workspace edits, is [archived here](docs/historical-pre-weekly/ARCHITECTURE.md).
