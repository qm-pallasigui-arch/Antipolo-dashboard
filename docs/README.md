# Current documentation

- [Setup and behavior](../README.md)
- [Architecture](../ARCHITECTURE.md)
- [Implementation methodology status](../THESIS_READINESS.md)
- [Data dictionary](MONTHLY_DATA_DICTIONARY.md)
- [UI components](MONTHLY_UI_COMPONENTS.md)
- [Supabase migration plan](SUPABASE_MIGRATION.md)
- [Repository hygiene and cleanup](REPOSITORY_HYGIENE.md)
- [Thesis audit, evidence and listing tools](thesis-program-listings/README.md)
- [Historical archive and recovery instructions](../archive/README.md)

These documents cover the current seven-candidate Prophet + XGBoost prototype. Final thesis settings still require methodology approval. Superseded handoffs, old documentation trees and legacy implementations are compressed into one archive rather than mixed with current guidance.

The root `AGENTS.md` and `CLAUDE.md` contain development-assistant instructions. They are not application dependencies, but should remain available to the tools used on this project.

## Broader follow-up sprints

These four roadmap items are separate from the numbered UI layout phases. Layout Phases 4 and 5 were subsequently implemented in this session; see the completion record in the UI document for verification and remaining limitations. See the reconciliation below before treating this table as the complete remaining-work list.

The forecast reliability sprint adds batch locking, persisted progress, interruption recovery, partial-failure feedback, explicit forecast dates and labels for earlier rankings. Model settings and source-data semantics are unchanged. The thesis package remains historical verification evidence; its source hashes and test counts do not certify later code changes.

| Priority | Sprint | Scope and acceptance checks |
|---|---|---|
| 1 | Accessibility and interaction | Implemented targeted focus, progress-announcement stability, control contrast and long-error fixes on November 16; 69 tests and the full browser regression pass. Manual screen-reader acceptance and exhaustive traversal remain open; see the UI sprint record. |
| 2 | Durable forecast execution | Implemented November 16: database queue, separate supervised model process, confirmed cancellation, retained batch history and local/container launch wiring. Local lifecycle and browser verification pass; Linux container and PostgreSQL acceptance carry into Sprint 3. |
| 3 | Performance and deployment | Measure progress-poll load, adapt polling when idle and verify concurrency/recovery against a dedicated PostgreSQL test database. Test the threaded Gunicorn container and backup/restore before deployment. Current local checks do not establish cloud readiness. |
| 4 | Research handoff | Regenerate source listings and verification evidence after implementation stabilizes. Review Chapter 3 choices with the owner before changing model parameters, splits, residual methodology or uncertainty estimates. |

These are proposed follow-up sprints, not authorization to change methodology, add dependencies or deploy.

## Agent handoff reconciliation — 15 November 2026

This summary reconciles the current working tree, the [UI phase record](MONTHLY_UI_COMPONENTS.md), the roadmap above and [methodology readiness](../THESIS_READINESS.md). It supersedes interpreting the four roadmap items as the only remaining phases. The initial handoff changed documentation only. The subsequent owner request authorized finishing the layout phases first; the status rows below reflect that follow-up, while the initial audit evidence remains historical.

### Current project structure and behavior

| Area | Current location and responsibility |
|---|---|
| Startup | `app.py`, `dashboard/app_instance.py`, `dashboard/config.py`, `dashboard/logging_config.py`; Flask/Dash installation and `/healthz`. |
| Interface | `dashboard/monthly/ui.py`, `views.py`, `components.py`, `charts.py`, `navigation.py`; shared styles and behavior in `dashboard/assets/monthly.css` and `monthly-ui.js`. |
| Data and accounts | `domain.py`, `data_quality.py`, `store.py`, `security.py`, `admin.py`; canonical validation, explicit activation, persistence and server-side permissions. Paths in this row are under `dashboard/monthly/`. |
| Forecasting | `dashboard/monthly/forecasting/` contains configuration, adapter, Prophet, residual features/XGBoost, hybrid composition and evaluation. `services/` orchestrates forecasting and rankings; `repositories/` persists results and coordinates batches. |
| Reports | `dashboard/monthly/reports.py`; HTML, JSON and CSV exports are already implemented. |
| Verification | `tests/` contains unit/integration tests and browser/performance scripts; `tools/verify_prototype.py` exercises real models in an isolated database. |
| Documentation and provenance | Current guidance in root Markdown and `docs/`; historical thesis evidence in `docs/thesis-program-listings/`; verified history ZIP and original tuning-script provenance in `archive/`. |
| Local state and generated output | `.monthly/` is active state, not a test fixture. `.artifacts/` holds routine outputs. Root CSV/XLSX sources, historical `evidence/`, `reconciliation/`, `.forecast-jobs/` and `.weekly-models/` are not permission to delete or reactivate legacy code. |

The operational pipeline remains the provisional monthly Prophet + XGBoost workflow for all seven ICD-10 blocks. Explicit zeros, unknown values and actual reporting dates must remain intact. Historical Top Five and projected rankings are separate. Final methodology is not implemented merely by setting prototype mode to false.

### Reconciled phase status

The UI document contains an earlier November 8 review sequence and a later **Layout overhaul** sequence; their repeated phase numbers are not interchangeable.

| Workstream | Established status | Next work / boundary |
|---|---|---|
| Layout Phase 1 | Implemented in the recorded November 9 work: shared shell/navigation and Dashboard layout. | Manual accessibility checks remain; this is not a claim of full accessibility conformance. |
| Layout Phase 2 | Implemented in the recorded November 14 work: Disease Trends and Forecasting layouts. | Preserve real progress, table alternatives and responsive chart behavior. |
| Layout Phase 3 | Implemented in the recorded November 14 work: Model Performance and Data & Quality layouts. | Preserve persistent upload controls, viewer coverage and shared chart configuration. |
| Layout Phase 4 | Implemented November 15 after this initial handoff. | Reports retain three responsive export cards; Notifications use persistent 3/9 filters/activity with fit-aware sticky behavior; Help uses 8/4 content/glossary. See the UI completion record. |
| Layout Phase 5 | Implemented November 15 after owner clarification. | Responsive account creation/management panels, associated password-reset disclosures, visible feedback and server-enforced self-demotion/self-disable protection. Forced-first-login password changes remain outside scope. |
| Forecast reliability / durable execution | Batch locking, persisted progress, heartbeats, interruption recovery and late-write protection now support the dedicated worker. The web callback queues through `service.submit`. | Local tests cover stopping process trees, cancellation, refresh, history and real models; PostgreSQL/container operational checks remain Sprint 3. |
| Four broader roadmap sprints | Still documented follow-up work, with some foundations already implemented. | Accessibility completion; durable execution; performance/deployment; research handoff. They are not numbered layout Phases 4–7 or four wholly untouched features. |

Phase 4 acceptance is already recorded in the UI document: before/after captures at 1920, 1440, 1024, 768 and 375px; no page overflow or obstructive sticky controls; keyboard/filter/disclosure checks; notification empty/unread states and mark-read confirmation/cancel; all three exports for both roles; Help links/glossary; relevant pytest and full browser regression. Reuse the established requirements unless scope changes.

### Remaining implementation and decision gaps

- **Durable jobs:** implemented by the November 16 continuation below. The supervisor stops model descendants, and new batch history is retained separately from the current slot. Previously overwritten legacy batch records cannot be reconstructed. Interrupted work requires an explicit rerun; no partial batch is silently resumed.
- **Polling and cloud:** `ui.py` mounts a fixed two-second batch interval and a separate thirty-second state interval. Idle polling adaptation and poll-load measurement remain roadmap work. PostgreSQL concurrency/recovery, container execution, backup/restore, migration and AWS deployment remain unverified by the latest local audit. The opt-in Supabase persistence test does not by itself cover all concurrency/recovery acceptance criteria.
- **Accessibility:** November 16 checks add navigation-heading focus, stable progress notices across timer updates, nine chart/control/notice contrast measurements and long mobile error wrapping. Manual screen-reader behavior, exhaustive keyboard traversal and physical-device/cross-browser checks remain open. This is not full accessibility certification.
- **Security reconciliation:** the owner explicitly authorized fixing self-demotion/self-disable with Phase 5. The server now rejects these self-account changes even with another administrator; other administrators retain existing account-management permissions. Forced-first-login password change remains unsupported and outside this scope.
- **Earlier partial UI items:** original screenshot/run identification (F1), comprehensive advanced-diagnostic wording review (X2), and historical notifications without run references (N1) remain documented limitations. Do not invent a source run or backfill guessed group membership.
- **Research:** Chapter 3 approval is still required for gap treatment, residual methodology, features/lags, tuning, clipping/shrinkage, evaluation design, metrics/scaling and uncertainty. Do not change these while cleaning up code or layouts.
- **Unused-code candidates:** alternate `fit_predict` functions in both model modules and `ForecastService.generate_forecast` have no repository callers found in the preceding audit. `validate_error_rows` is test-only, not an active training safeguard. `Store.latest_forecast` retains an explicit archive-access test contract. Review compatibility before removal; decorated routes/callbacks are not dead code.

### Evidence reconciliation and immediate checks

The preceding audit in this conversation, dated November 15, ran **62 passing tests, 2 failing tests and 1 skipped Supabase test**. Those were the initial audit results. The subsequent Phase 4?5 implementation reran the full suite: 68 passed, 1 skipped; see the UI completion record. The failures are `test_failed_latest_attempt_is_visible_in_pages_and_reports` (expects a raw status code now translated for display) and `test_counts_are_readable_without_rounding_small_errors_to_zero` (expects `663.0`, while documented whole-count display returns `663`). Reconcile assertions with the documented presentation contract without weakening latest-failure visibility or small-error precision checks.

That audit also recorded clean Pyflakes/dependency checks, browser acceptance PASS, and real synthetic model evidence: seven candidates attempted, two completed, five expected empty-history failures, 24 stored values and an unavailable Top Five. Browser/model PowerShell redirection returned exit 1 despite success output; the browser PASS message and independently checked saved model JSON were the evidence, not a claimed clean shell exit. Initial sandbox attempts had temporary-folder permission failures. See the local [audit summary](../.artifacts/codebase-audit/summary.md), [browser log](../.artifacts/codebase-audit/browser-verified.log) and [model evidence](../.artifacts/codebase-audit/prototype.json); ignored artifacts may not accompany a clone.

Fresh checks for this handoff compared the thesis manifest with current source: **10 of 21 distinct listed source files have different SHA-256 hashes**. The manifest records October 30 and HEAD `ef1431c8`; this checkout is at `545bdbe` with uncommitted work. The generated thesis listing document is absent as documented. The old 51-pass result and canonical seven-success/84-value run are historical evidence, not verification of today's source. Regenerate listings together with fresh verification after implementation stabilizes.

At inspection, Git showed 27 modified tracked files, 189 deleted tracked paths, no staged changes, and untracked instructions, the history ZIP, `batch_repository.py` and `test_forecast_batches.py`. Preserve this working tree. A checkout of HEAD alone will not reproduce it. The preceding audit verified all 288 history-ZIP manifest hashes; do not restore archived code into runtime or treat the loose-file deletions as authorization for further cleanup.

Continuation update: the two presentation assertions were reconciled with documented behavior, and layout Phases 4?5 were implemented after owner clarification. Read the UI completion record for the final verification results. Broader roadmap work and methodology approvals remain separate and were not started. This order is a handoff recommendation, not a newly approved schedule. Before changes, read root `AGENTS.md`, `README.md`, this index and the relevant UI/architecture guidance. Use the existing environment and isolated databases, preserve source data and local state, and do not stage, commit, push or deploy without instruction.

### Current continuation / next-agent handoff - 16 November 2026

The preceding continuation paragraph records the layout-phase stopping point. The owner subsequently requested the accessibility sprint, then "finish next sprint, prepare next." Sprint 1's automated fixes are implemented, with manual screen-reader acceptance still open. Sprint 2's durable execution is implemented and locally verified. No methodology changes or dependencies were added.

Current execution: `ForecastService.submit` persists a queued request and returns; `dashboard.monthly.worker` supervises a separate model process. `process_tree.py` contains descendants, and `runtime.py` wires local/container lifecycle. The current batch slot still coordinates ownership; `forecast_batch_history` retains every new attempt. Cancellation is administrator-only and tied to the batch shown when the confirmation opens. Completed forecasts are retained, remaining writes are fenced, and ranking publication/terminal status are atomic. `run_all` remains synchronous only for worker/tool use. Plain Gunicorn needs its separate worker; `app.py`/`run.bat` and the Docker runtime launch it automatically.

Fresh evidence is in `.artifacts/durable-sprint/`: the full suite passed **81 tests, 1 skipped** (`pytest-acceptance.log`), then the final lifecycle suite passed **20 tests** (`lifecycle-final.log`), including the additional abrupt-supervisor-loss test and final worker query change. The browser regression covers real model execution, cancellation dismissal/acceptance, rerun, refresh/second-tab progress, completed output, roles and five-width layouts. Local startup checked `/healthz` on port 8050 with an isolated database and verified automatic worker exit after the web launcher stopped. See the UI record for final browser evidence and limitations. These are fresh results, not the historical thesis evidence.

**Next: Sprint 3, Performance and deployment.** Follow the ordered acceptance checklist in [Supabase/AWS guidance](SUPABASE_MIGRATION.md): measure browser/worker polling, adapt idle polling, test PostgreSQL concurrency/recovery, verify Linux container signals/process cleanup, then stage a backup/restore drill. Docker is not available in the current shell and no dedicated PostgreSQL test URL was used. Prepare or request those environments when needed; do not treat local SQLite tests as cloud acceptance. No deployment, production migration, commit or push was performed.

Carry forward the manual screen-reader check, research-methodology approvals and existing provenance limitations. Keep explanations concise unless the owner asks for detail.
