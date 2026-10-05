# Weekly redesign reconciliation report

Prepared: 2 October 2026, Asia/Manila.

**Historical baseline:** this report describes the initial weekly revision before Revision 39. The guided upload/interface correction and subsequent browser review are documented in [REVISION39_REPORT.md](REVISION39_REPORT.md). Earlier JSON controls, navigation names, and browser-review limitations below are superseded there.

## Assessment

The operational application has been switched from the historical monthly workflow to a separate weekly implementation. The requested data-integrity controls, model infrastructure, five-section interface, exports and prospective-recordkeeping structure are implemented. **This is software implementation progress, not evidence that the weekly statistical protocol or final thesis dataset has been approved.**

The default model configuration remains pending and produces an explicit unavailable status. Generating forecasts requires an explicit configuration. Final research acceptance still requires eligible real surveillance data, documented methodology approval, and evaluation under that protocol. Browser visual acceptance also remains outstanding.

This report reconciles the supplied weekly coding-agent handoff against the current implementation and the recorded verification from 1 October 2026. Tests were not rerun solely to produce this report. It is not a new reconciliation of source case counts or a prospective forecast-versus-observation evaluation.

## Acceptance-criteria reconciliation

“Implemented” describes the software behavior. “Conditional” means the capability exists but depends on supplied source facts or protocol choices. Neither status certifies research validity.

| Handoff criterion | Status | Implementation / qualification |
| --- | --- | --- |
| 1. Weekly core modeling | Implemented | Ordered reporting-year/morbidity-week sequences in `dashboard/weekly/model.py`. |
| 2. Up to 52 weekly forecast points | Conditional | A configured successful run generates a single 52-point path. Pending or failed components remain unavailable. |
| 3. No monthly aggregation dependency | Implemented | Operational weekly fitting does not call the historical monthly pipeline. |
| 4. Monthly/quarterly presentation only | Conditional | Display summaries require source-established `week_start_date`; they do not retrain models. |
| 5. Ages 5–19 versus all-age separation | Implemented | Dataset/output contexts distinguish final thesis from technical/retrospective use. |
| 6. Confirmed-only eligibility | Implemented | Unknown, suspected, probable or conflicting classification does not qualify. |
| 7. CESU/PIDSAR primary source | Implemented | Source/provenance eligibility checks preserve this terminology; FHSIS is not an equivalent eligible source. |
| 8. Distinct Measles categories | Implemented | Source labels remain distinct; case/whitespace inconsistencies are reported. |
| 9. Hybrid primary | Implemented | Hybrid SARIMA–NNAR is the primary forecast presentation. |
| 10. Separate SARIMA-only | Implemented | Comparison values, status, configuration and metrics remain separate. |
| 11. No silent Hybrid fallback | Implemented | Permitted candidate retries can end in explicit Hybrid unavailable; SARIMA is never relabeled. |
| 12. Missing is not zero | Implemented | Source blanks remain null; absent weeks become missing model positions, not fabricated case records. |
| 13. Preserve week 53 | Implemented | Original records are retained; calendar conflicts are reported, never merged or remapped. |
| 14. Exclude incomplete recent weeks | Implemented | Only complete reporting observations enter training; incomplete/unknown values remain visible. |
| 15. Gaps produce warnings | Conditional | State-space handling can continue with gaps. NNAR requires usable lag windows; missing calendar boundaries or insufficient windows can prevent a result. |
| 16. Validate and Confirm & Activate | Implemented | Pending uploads do not replace active data. Editing inputs clears the stale preview. |
| 17. Four mandatory row fields | Implemented | `disease`, `year`, `morbidity_week`, `case_count`; CSV/XLSX supported. |
| 18. Dataset-level eligibility metadata | Implemented | Dataset metadata and consistent row metadata can establish context. Approval assertions are not independently authenticated. |
| 19. Synthetic exclusion | Implemented | Synthetic/demo context cannot qualify as thesis evidence; identified real/synthetic mixtures prevent activation. |
| 20. Provenance and lifecycle | Implemented | Metadata, upload/validation/confirmation/activation/replacement/reset events are exposed; lifecycle state is browser-session scoped. |
| 21. Cache isolation | Implemented | Signature includes dataset contents/metadata, disease, configuration and implementation version. |
| 22. Five-section navigation | Implemented; visual review pending | Overview, Forecast, Historical Trends, Data & Quality, Technical Details. Layout and HTTP behavior tested. |
| 23. Cautious forecast language | Implemented | Interpretation uses projected/model-based language and identifies demo outputs. |
| 24. No epidemic-threshold feature | Implemented exclusion | No operational threshold comparison or outbreak-declaration feature added. |
| 25. Main MAE/WAPE | Implemented | Emphasized in Forecast; unavailable/undefined results are explicit. |
| 26. Four technical metrics | Implemented | MAE, RMSE, MAPE, WAPE; zero handling and denominator coverage documented. |
| 27. Remove fixed 32.22% main-UI reference | Implemented | Historical reference does not appear in the weekly operational UI. |
| 28. Provenance-rich exports | Implemented | CSV and complete evidence JSON preserve weekly context, model status/configuration, warnings and metrics. |
| 29. Retrospective/prospective separation | Structural support implemented | Historical evaluation stays retrospective. Original snapshot values and later reconciliation revisions are recorded separately; prospective validation is not claimed complete. |
| 30. Pending methodology stays configurable | Implemented | No default approved seasonal period, candidate grid, weekly NNAR design or holdout protocol is invented. |
| 31. Integrity tests | Implemented | 58 weekly tests recorded passing; full suite recorded 170 passing. See qualifications below. |
| 32. Documentation synchronization | Implemented | Current README, architecture, evaluation notes, system contract and test report describe weekly behavior. Earlier material is retained as historical evidence. |

## Material changes and evidence locations

| Area | Current evidence |
| --- | --- |
| Operational entrypoint | [app.py](app.py) imports the weekly layout/callbacks. |
| Data foundation and eligibility | [dashboard/weekly/data.py](dashboard/weekly/data.py) |
| Weekly fitting, evaluation and cache signature | [dashboard/weekly/model.py](dashboard/weekly/model.py) |
| Exports, display aggregation and prospective records | [dashboard/weekly/outputs.py](dashboard/weekly/outputs.py) |
| Interface and state transitions | [dashboard/weekly/ui.py](dashboard/weekly/ui.py), [weekly.css](dashboard/assets/weekly.css) |
| Automated acceptance coverage | [tests/test_weekly.py](tests/test_weekly.py) |
| Detailed behavior and configuration contract | [WEEKLY_SYSTEM.md](WEEKLY_SYSTEM.md) |
| Verification record | [TEST_RESULTS.md](TEST_RESULTS.md) |
| Preserved pre-weekly documentation | [docs/historical-pre-weekly](docs/historical-pre-weekly) |

Earlier monthly modules remain in the repository for historical evidence and regression tests. Their presence is not evidence that they run in the operational weekly application. A fresh-process test checks that normal startup registers only the seven weekly callbacks. Pre-existing uncommitted workspace changes were preserved; the entire Git diff should not be attributed to the weekly revision alone.

## Verification reconciliation

| Recorded check | Result | Scope |
| --- | --- | --- |
| Full regression suite | 170 passed; 14 deprecation warnings; 58.24 seconds | Existing historical regressions plus weekly tests. |
| Final weekly recheck | 58 passed; 4 deprecation warnings; 7.22 seconds | Rechecked after the final row-context reconciliation guard and metadata-default refinement. |
| Static analysis | Clean | `python -m pyflakes dashboard/weekly tests/test_weekly.py`. |
| Application smoke checks | HTTP 200; seven weekly callbacks | Health, layout and weekly CSS routes; fresh-process callback isolation. |
| Whitespace check | No errors | Git emitted LF/CRLF normalization notices. |
| Browser visual review | Not performed | No screenshot, responsive-browser or interactive usability acceptance is claimed. |

The full-suite run preceded the last small refinements; the final weekly recheck covered the affected implementation afterward. These counts are overlapping checks, not 228 distinct tests. Warnings concern Dash DataTable deprecation, not failed assertions. Initial sandbox runs encountered temporary-directory permission errors; reruns with the required filesystem access passed.

Tests include real SARIMA/NNAR execution using synthetic inputs, plus controlled failure-path tests. They do not establish measured forecasting performance on eligible Antipolo ages 5–19 confirmed-case surveillance.

## Decisions and work still pending

| Item | Needed before final acceptance |
| --- | --- |
| Research data | Establish eligible real weekly ages 5–19, confirmed-only Antipolo CESU/PIDSAR records and their provenance. No new real-data validation result was produced by this revision. |
| Disease scope | Document the approved disease list; software support for a label is not research approval. |
| Reporting calendar | Establish source year lengths, week 53 handling, and any dates used for monthly/quarterly display summaries. Unknown future calendar labels remain null rather than invented. |
| Weekly SARIMA protocol | Approve candidate orders, seasonal assumptions, initialization handling and residual criteria. ADF/ACF/PACF are available diagnostics, not a finalized automatic selection protocol. |
| Weekly NNAR protocol | Approve lag offsets, network size, residual windows and history requirements. |
| Evaluation protocol | Approve holdout/folds/origins and horizon-specific design. Current infrastructure implements a configurable chronological holdout, not a complete approved rolling evaluation study. |
| Missingness and completeness | Confirm reporting-status declarations and formal evaluation treatment of gaps; no automatic imputation is implemented. |
| Uncertainty | Validate or replace the provisional Hybrid ± training SARIMA residual RMSE range. It is not a calibrated 95% interval. |
| User interface | Complete browser visual, responsive and interaction review. Metadata/protocol editing currently uses JSON text areas. |
| Prospective study | Issue genuine forecasts before outcomes, accumulate later observations and revisions, and evaluate under the approved protocol. Structural support alone does not complete the study. |
| Deployment recordkeeping | Provide durable writable snapshot storage and suitable access controls. Local content-addressed files detect original snapshot tampering but are not an externally managed immutable archive. |

## Research-integrity boundaries

No operational seasonal-naive benchmark, epidemic-threshold comparison, direct PDF-to-model ingestion, automatic missing-week imputation, silent zero filling, or SARIMA-as-Hybrid substitution was added. Historical benchmark files were preserved rather than deleted.

Eligibility relies on supplied metadata and references. The application detects specified conflicts but cannot independently prove the truth of operator declarations. Dataset eligibility and model-protocol eligibility are separate. No historical monthly/all-age metric or synthetic result should be cited as validation of the revised weekly school-aged research objective.

The reconciled status is therefore **weekly software workflow implemented and regression-tested; research-method approval, eligible-real-data evaluation, prospective validation, and browser visual acceptance remain outstanding**.
