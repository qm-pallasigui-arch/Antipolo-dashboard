# Final model reconciliation — 29 October 2026

The user finalized Prophet + XGBoost. This supersedes model-family selection and the former prototype. The pre-change inventory is [static-audit.csv](static-audit.csv); it records each matching line and context. [scan-limitations.txt](scan-limitations.txt) records inaccessible paths and undecodable files. Dependencies, Git internals, bytecode, browser tooling and binary files are excluded. This is a static source audit, not a claim that every binary artifact was inspected.

No destructive deletion is planned. Original DOH sources and canonical CSV/XLSX are KEEP. Existing database records are retained without relabeling old predictions as final-model results.

| File | Line / Symbol | Legacy assumption | Current-study replacement | Action | Risk |
|---|---|---|---|---|---|
| dashboard/monthly/forecasting/prototype_adapter.py | PrototypeForecastAdapter | Learner selection, compressed calendar gaps, base-only fallback | Single hybrid contract, explicit failure | ARCHIVE | High: forecast contract changes |
| dashboard/monthly/forecasting/icd_inference.py; icd_inference.py | module | Imports old engine | No production imports | ARCHIVE | Low: preserved verbatim with provenance header |
| icd_inference_a00.json; icd_inference_b25.json; tests/fixtures/prototype | entire artifacts | Old sample outputs | Archive only, never seeded into storage | ARCHIVE | Low |
| icd10_forecast_clean.py; icd_forecast.py | not found in source inventory | Requested starting script / old engine | Record absence; do not invent supplied code | REVIEW | Refactor cannot reuse an absent file |
| dashboard/monthly/domain.py | evaluate_forecast_eligibility | 8/8 and 96 as a hard gate | All seven candidates; readiness pending approved policy | REWRITE | High: do not invent replacement thresholds |
| dashboard/monthly/forecast.py | ForecastService | Registry of interchangeable engines, prototype status | Fixed Prophet + XGBoost service | REWRITE | High |
| dashboard/monthly/views.py; ui.py; reports.py | forecast labels and explanations | Prototype/model choice remains open | Model fixed; methodology configuration explicitly pending | REWRITE | Medium |
| dashboard/monthly/store.py | persisted payload reads | Old eligibility and prototype results reusable | Refresh derived readiness; filter legacy results | REWRITE | High: preserve source signatures and history |
| tests/test_prototype_forecast.py | entire test module | Old learner and fallback acceptance | Hybrid failure, chronology, ranking, readiness tests | ARCHIVE | Medium |
| tests/test_monthly_system.py | eligibility and engine tests | Fixed coverage gate | Retain validation/RBAC tests; replace model contracts | REWRITE | Medium |
| README.md; ARCHITECTURE.md; THESIS_READINESS.md; docs/README.md | current guidance | Prototype integration/final family undecided | Current architecture and honest remaining decisions | REWRITE | Medium |
| docs/PROTOTYPE_FORECASTING.md; other superseded developer documents | entire documents | Earlier study implementation | Explicitly historical archive | ARCHIVE | Low |
| CHANGELOG.md; archive; reconciliation; evidence | historical matches | Prior study history | Mark superseded; preserve provenance | KEEP | Low |
| .weekly-models; .forecast-jobs; local caches | historical runtime artifacts | Old experimental outputs | Exclude deployment; retain locally | KEEP | Low |
| pyproject.toml; requirements.txt | dependencies | Final engine dependencies absent | Optional final-model dependency group | REWRITE | Medium: do not change installed environment |
| .dockerignore | deployment exclusions | Root research scripts could ship | Exclude archive, tools, local research inputs | REWRITE | Low |

Remaining methodology decisions: usable observations, gap rules, chronological train/evaluation splits, residual feature design, error-generation strategy, metrics/scaling, tuning, uncertainty. Model-family approval alone does not approve these settings. Default execution must remain blocked until an approved methodology is supplied.

SQLite is the existing local persistence implementation. Supabase migration requires an explicit schema/data migration and deployment connection. No live database conversion, column drop or production-data rewrite is authorized implicitly by a naming cleanup. See the migration plan for additive schema and verification requirements.

## Execution results

The wrappers, adapter, old prototype tests, sample JSON outputs and superseded developer documents were moved to `archive/forecasting/`. Original source inputs were retained. The current package has no imports of the archived engines. Current documentation and UI identify Prophet + XGBoost as the fixed architecture. Readiness summaries cover all seven candidates and no longer use the former coverage threshold as an automatic gate.

The implementation includes component wrappers, a fixed hybrid composition contract, versioned twelve-month forecast records, grouped ranking service, local ranking persistence, UI/report integration and rejection of legacy results. Both model components must succeed. Rankings require one dataset, one run group and identical twelve-month calendars. Missing candidates and failed runs are disclosed; no five-block result is fabricated.

Read-only [database inventory](database-inventory.json) found four existing failed forecast records and no completed forecast records in the inspected local database. No source, account, forecast or report records were rewritten. A rankings table is created additively when the revised Store starts; its persistence was tested against isolated databases.

Validation: **31 tests passed**, five existing Dash DataTable deprecation warnings. Pyflakes passed for current monthly code and tests; `git diff --check` passed. The headless browser acceptance test passed desktop/mobile layout, upload/activation, navigation, HTML export, disabled methodology-pending forecasting, logout and viewer permissions with no browser errors. Screenshots are under `evidence/reconciliation-20261029/` and use synthetic data. Test execution required sandbox escalation because pytest temporary directory permissions failed inside the restricted Windows environment.

The initial static audit inventories **20,277 matching lines**, with **91 read/decoding limitations** recorded separately. Each line retains file, line number, matched terms, disposition and context. REVIEW entries remain review candidates; historical KEEP entries do not become active dependencies. Negative import guards, schema-rejection tests, consultation-versus-case caveats and legacy-record exclusion checks legitimately retain historical terms.

## Acceptance gaps

The full final acceptance condition is **not yet met**. Live model orchestration, approved chronological training/features/readiness/evaluation/uncertainty settings, real-model validation and Supabase persistence are outstanding. Model wrappers and synthetic tests do not substitute for those deliverables. The default runtime deliberately reports methodology_pending and disables fitting instead of inventing research settings. The supplied request names two research scripts that were absent from the scanned source; their refactor cannot be verified without those files.
