> Current consolidated implementation: [Revision 45 report](REVISION45_REPORT.md).

> Current weekly-system handoff: [3 October 2026 reconciliation](RECONCILIATION_HANDOFF_2026-10-03.md). The content below is historical; its runtime status and monthly model scores are not current weekly acceptance evidence.

# Antipolo dashboard: detailed agent handoff

Prepared 2026-09-27, Asia/Manila. Start here before changing this workspace.

## Objective and current status

The user is developing a thesis-related Antipolo disease-surveillance dashboard. They requested a reconciliation covering two distinct baselines, explicit approval of upload-defined disease catalogs, threshold sensitivity without changing policy, investigation of seasonal-naive superiority, and fresh verification. Those implementation and investigation outputs are saved. The latest request is to gather detailed handoff context, run the system, and explain its processes.

The app is now running locally at **http://127.0.0.1:8050** with debug/reloader disabled. On 2026-09-27, HTTP checks passed for `/`, `/healthz`, `/_dash-layout`, and `/_dash-dependencies`. A request to the running server's registered forecast callback generated a 12-month sample Dengue forecast, selecting SARIMA-only, with holdout WAPE 27.018472980905077%, and returned both reference cards. See `evidence/runtime-check-2026-09-27.json`.

Do not equate successful startup or HTTP checks with live-browser visual acceptance. No browser screenshot/layout inspection has been performed. The previous handoff explicitly withheld a blanket thesis-ready declaration.

## Read these sources in order

1. This document: operational context, constraints, architecture, and continuation instructions.
2. [THESIS_READINESS.md](THESIS_READINESS.md): authoritative current thesis reconciliation, exact UI/documentation wording, full evidence tables, actual test output, reference inventory, and **single current ledger of remaining author decisions**. Do not maintain a competing decision ledger here.
3. [README.md](../../README.md): launch, input formats, PDF conversion, model interpretation, and deployment.
4. [ARCHITECTURE.md](../../ARCHITECTURE.md): detailed modules, contracts, model stages, and deployment limitations.
5. [CHANGELOG.md](../../CHANGELOG.md): historical changes. Earlier entries saying the historical reference was removed or seasonal naive was hidden are superseded by the 2026-09-26 entry.
6. Evidence scripts, JSON, and logs below, then the relevant source and tests.

The original detailed request remains at `C:/Users/redlo/.codex/attachments/c256980d-0391-4808-b216-8325ad380309/Pasted text.txt` on this machine. It may not accompany a repository transfer; its binding requirements are summarized below.

## Binding user decisions and scope boundaries

- Show fixed historical MAPE **32.22%** and live seasonal-naive holdout MAPE/WAPE distinctly and neutrally. Do not average, merge, or rank their authority. Historical provenance belongs to the manuscript; it is not an active-dataset calculation.
- Permit arbitrary upload disease labels only after an explicit approval action. Preserve active data while pending or rejected. Reuse Upload summary and show the full disease list, not just a limited row preview.
- Preserve `HYBRID_MIN_WAPE_GAIN_PP = 1.0` and the current selection mechanism. The expert consultation is deferred, **not resolved**. Sensitivity analysis is evidence, not authorization to change policy.
- Investigate seasonal-naive superiority openly. Do not hide the finding or silently change the mock generator or modeling code to improve results.
- Keep real and synthetic evidence separate. Claims must identify their verification method and limitations.
- Do not introduce unrelated changes. Author decisions and thesis wording changes belong in the existing consolidated ledger.
- All five readiness conditions matter: distinct visible references, tested explicit catalog approval, an evidence-based benchmark explanation, fresh passing full tests with actual output, and one current remaining-decision document.

No model/generator changes were made during the 2026-09-26 reconciliation. Changes visible against Git in those files were already present at the start of that task.

## Workspace and version-control warning

- Workspace: `C:/Users/redlo/Downloads/Antipolo-dashboard`.
- Windows PowerShell; current Python is 3.13.3. Project metadata requires Python >=3.12.
- Last inspected commit: `46f186d`, beginning “Major refactoring of the backend codebase to improve maintainability and performance.”
- There are many pre-existing uncommitted edits. **Do not reset, clean, overwrite, or assume the Git diff consists only of the latest agent's work.** No commit or deployment was made by this handoff.
- Already modified before the reconciliation: README, architecture, changelog, callbacks, charts, config, data ingestion/conversion/generator modules, modeling modules, layout, and multiple tests. Original PDF and converted data were already untracked.
- Reconciliation additions: `THESIS_READINESS.md`, `evidence/`, `tests/test_upload_confirmation.py`, plus scoped modifications to baseline/config/UI, upload callbacks, documentation, and tests. Current-session additions: this handoff, runtime evidence, and server log/PID files.
- No `AGENTS.md` was found by the workspace file search. Check applicable instructions again if moving to another checkout.
- Preserve the actual working tree and untracked evidence when transferring. Checking out the last commit alone will not recreate this system.

## Run, check, and stop

The server was started hidden with `Start-Process`, using the existing Python executable, the workspace as working directory, and these process environment settings:

```powershell
$env:DASH_DEBUG = 'false'
$env:HOST = '127.0.0.1'
$env:PORT = '8050'
$env:PYTHONUTF8 = '1'
python app.py
```

The command above is the equivalent foreground launch, useful on a new terminal after stopping the current instance. Do not start a duplicate on the occupied port.

Current process ID at launch: **11300**. Also saved in `evidence/dashboard.pid`; a PID is temporary and can be reused after exit. Verify process identity before stopping it:

```powershell
Get-NetTCPConnection -LocalPort 8050 -State Listen
Get-CimInstance Win32_Process -Filter 'ProcessId = 11300' |
    Select-Object ProcessId, ExecutablePath, CommandLine
Invoke-RestMethod http://127.0.0.1:8050/healthz
```

After verifying that PID still belongs to this dashboard, `Stop-Process -Id 11300` stops this instance. A foreground instance can be stopped with Ctrl+C. Logs: `evidence/dashboard-stdout.log` and `evidence/dashboard-stderr.log`. The initial health probe raced startup; subsequent health and application requests succeeded. Local launch is not a production deployment and does not make the app accessible publicly.

### Environment reproducibility

The existing installed environment differs from `requirements.txt` and `pyproject.toml`. Do not silently claim the pinned environment was tested or install over the working environment merely to tidy it.

| Library | Installed and used for evidence | Repository pin |
| --- | --- | --- |
| Dash | 4.2.0 | 4.4.1 |
| Plotly | 5.19.0 | 7.0.0 |
| pandas | 2.3.3 | 3.0.5 |
| NumPy | 2.3.4 | 2.5.2 |
| statsmodels | 0.14.6 | 0.15.0 |
| scikit-learn | 1.4.0 | 1.9.0 |
| openpyxl | 3.1.5 | 3.1.5 |
| SciPy | 1.16.3 | no direct pin |

Numerical optimization, warnings, and fallback behavior may differ in a different environment. If validating the declared pins later, use an isolated environment, verify package availability, and rerun the tests and comparisons before asserting reproducibility. Dependency changes are not part of this handoff.

## User workflow and data state

1. Open the local URL. A fresh browser session begins with seven clearly labeled synthetic sample diseases, 2016–2025. It does not automatically load the local real workbook.
2. **Surveillance overview:** choose disease and reporting-year range to inspect total cases, top disease, yearly bars, disease shares, and a monthly heatmap.
3. **Data & quality:** choose a date convention if needed, upload CSV/XLSX, inspect Upload summary's complete disease table and quality notes, then click **Use these N diseases** to activate the catalog.
4. Before that click, overview, selectors, and forecasts still use the previous session dataset. A parsed upload is only a candidate.
5. **Forecasts:** select a disease to view the selected model, holdout error, both reference cards, and next-12-month outlook. Expand diagnostics and Technical model details for additional evidence. Forecast computation is lazy; it runs when the callback requests a disease, not eagerly for every uploaded disease.
6. Download forecast CSV after a successful forecast, or use the chart camera control for PNG. Downloads preserve relevant provenance and model metadata.
7. Reset restores the built-in sample and clears pending data. Refresh retains confirmed session data but discards an unconfirmed memory-only candidate.

Browser stores:

| Store | Lifetime | Purpose |
| --- | --- | --- |
| `store-data` | Browser session | Active canonical dataframe serialized as pandas split JSON |
| `store-upload-summary` | Browser session | Active dataset metadata |
| `store-pending-upload` | Page memory | Parsed candidate, its complete catalog, preview, and notes; not active |
| `store-hybrid` | Browser session | Per-disease serialized results and dataset signature |

There is no central database of user uploads. Tests and the separate live HTTP smoke check do not populate the user's browser session. A session-confirmation workflow is not a security boundary against a browser owner modifying client-side storage.

## Source data and ingestion process

Real analysis source: `C:/Users/redlo/Downloads/Antipolo_Disease_Surveillance_2016-2025.xlsx` (outside the repository). Sheets: Dengue, Measles-Rubella, Leptospirosis, Notes. The Notes sheet identifies RESU/DOH-CALABARZON, PIDSR, Antipolo City, 2016–2025, and describes transcription from source tables/PDFs.

SHA-256: `c8e90c7e040e0c5e5b4676bbe6e26485e6921054d89f684f4f3768ae43cb73ff`.

This source is needed for `python -m evidence.investigate` and `python -m evidence.source_checks`; their path is currently machine-specific. Transfer it separately or intentionally update the evidence script path for a new machine. `evidence/real-monthly.csv` preserves the 360 parsed monthly rows but does not replace authentication of the original workbook.

Do not substitute `Diseases Data (for NBL).xlsx` or the project's top-five-disease PDF for this workbook. They are different sources. The top-five PDF and `sample-pdf-converted.csv` plus its report are relevant converter fixtures, not the three-disease workbook used for the real benchmark.

Pipeline:

1. Decode base64; apply upload/resource limits and supported extensions.
2. CSV/flat XLSX: normalize disease/cases and supported date or year/month or year/week columns. Specialized workbook: detect morbidity-week tables, map known sheet aliases, aggregate weekly values to months.
3. Validate labels/counts, normalize case-only disease duplicates to the first spelling, aggregate as implemented, and retain visible parse/rejection/gap notes. Read the validators for exact row-level policy before altering it.
4. Preserve explicit zeros; missing observations are not automatically evidence of zero cases. Forecasting separately blocks internally missing months.
5. Prepare canonical columns (`year`, `month`, `disease`, `cases`, `source`, `date`), then stage the upload. No synthetic diseases are backfilled into a confirmed real catalog.
6. Render all validated labels in Upload summary. The first-ten-row data preview is separate from the full disease table.
7. Activate the exact staged candidate only on a confirmation-button event. Prior positive click counts do not approve a later upload. Invalid replacement uploads prevent confirmation of an older candidate.

Weekly conversion uses the ISO week's Thursday; non-ISO week 53 is assigned to December of the reporting year. `Measles-Rubella` maps to `Measles`. All 30 source disease/year sums reconciled with parsed monthly totals, but underlying transcription authenticity and epidemiological calendar conventions were not independently established. Blank weekly cells are skipped; 120 monthly rows do not prove complete weekly reporting.

PDF conversion runs offline:

```powershell
python -m dashboard.data.pdf_converter source.pdf converted.csv --date-convention day-first
```

Read the generated `.report.json` and source PDF before uploading the converted CSV/XLSX. Resolve `dashboard_ready: false` blockers first. The converter supports text-based tables, not scanned-PDF OCR. Arbitrary labels and ICD-10 categories are compatible with the explicit catalog approval policy.

## Forecasting process and interpretation

The pipeline requires at least **72 consecutive explicitly observed months** at default settings: 36 initial training months, two 12-month selection folds, and one final 12-month holdout. Sparse uploads can be valid for surveillance summaries yet ineligible for forecasting.

For a complete 2016–2025 dataset:

| Stage | Training | Evaluation or forecast |
| --- | --- | --- |
| Selection fold 1 | 2016–2022, 84 months | 2023 |
| Selection fold 2 | 2016–2023, 96 months | 2024 |
| Untouched evaluation | 2016–2024, 108 months | 2025 |
| Production refit | 2016–2025, 120 months | 2026 |

Each leg fits the base series model, then a neural residual correction. The base attempts SARIMA(1,1,1)(0,1,1)[12] with a constant. Failure falls back to additive Holt-Winters, then nonnegative naive drift. Actual model tiers and warnings remain visible; base-only may therefore mean a fallback rather than SARIMA. Selection, holdout, and production can use different tiers.

NNAR is a small residual MLP: 3 lag inputs, one hidden layer of 4 units, L2 alpha=10, fixed random state, and recursive residual forecasts. Hybrid equals base forecast plus NNAR residual correction, clipped at zero.

Selection aggregates full-precision WAPE over the two earlier folds. Hybrid wins only if its gain is at least `HYBRID_MIN_WAPE_GAIN_PP` (1.0 point) **and** its score is strictly lower. Otherwise base-only wins. All-zero selection actuals make WAPE undefined; the existing mechanism then uses strict lower MAE. The final holdout is scored after selection and cannot be used to choose a retrospective winner.

Metrics:

- WAPE: `100 * sum(abs(actual - prediction)) / sum(abs(actual))`; undefined for an all-zero actual window.
- MAPE: average absolute percentage error over nonzero-actual months only; coverage is retained.
- MAE: average absolute error in cases/month.
- RMSE: square root of mean squared error in cases/month.

The selected production path is refit on all observed months. Its shaded band uses historical maximum absolute error across selected-path rolling/holdout errors, clipped at zero below. It is not validated as 95% future coverage.

The historical reference is a fixed external figure, **not** computed by this pipeline. Seasonal naive copies the final training year's monthly observations into the holdout, and is scored on the same actuals as the candidates. It remains a diagnostic benchmark, not a third selection candidate. Both references are shown neutrally, with no claim that their provenance or metric populations are interchangeable.

## Verified findings to preserve

From the unchanged default pipeline and the real workbook, January–December 2025:

| Disease | Selected model | Selected WAPE | Seasonal-naive WAPE |
| --- | --- | --- | --- |
| Dengue | Hybrid | 25.17% | 34.90% |
| Leptospirosis | SARIMA-only | 67.08% | 55.86% |
| Measles | SARIMA-only | 162.58% | 50.00% |

All three holdout base fits used SARIMA. Real Dengue's base-only WAPE was 27.36%, so Hybrid improved it in this one window. Seasonal naive beats the selected model on **two of three real diseases** and **six of seven synthetic diseases**. Do not average these findings together or describe the problem as exclusively synthetic.

All seven sample diseases select base-only at the default threshold. Lower thresholds would change some selections; the exact table and rolling gains are in THESIS_READINESS.md. No policy change was made.

The generator uses fixed annual seasonal weights, fresh random noise, and a deterministic 0.32 reduction in 2020–2022, with seed 2025. Stable 2024–2025 seasonal structure favors a previous-year template. Copying last year is not trivially optimal: a diagnostic seasonal average beats it on six of seven sample diseases.

NNAR improves training fit on all seven sample diseases but worsens holdout WAPE on four. This suggests generalization limitations without proving overfitting as the sole cause. It cannot explain all default selected-model failures because all selected sample paths are base-only. Training-window checks also change fit/fallback behavior; 60-month checks all fell back to Holt-Winters, so their results do not isolate history length alone.

Supported claim: this evaluated implementation shows a hybrid benefit for real Dengue in this particular holdout, and exposes failures elsewhere. Unsupported claims: general superiority, never worse than SARIMA, or established conditions guaranteeing hybrid success. Remaining expert/manuscript decisions are consolidated only in THESIS_READINESS.md.

## Code navigation

| Path | Main responsibility |
| --- | --- |
| `app.py` | Assemble layout/callbacks; expose Flask WSGI app and `/healthz`; launch locally |
| `dashboard/app_instance.py` | Shared Dash instance and request-size limit |
| `dashboard/config.py` | Sample disease definitions, static historical figure, model constants, resource limits |
| `dashboard/ui/layout.py` | Overview, Forecasts, Data & quality tabs; stores and controls |
| `dashboard/ui/components.py` | Reusable metric cards, neutral/good/bad styling |
| `dashboard/callbacks/data_callbacks.py` | Parse/stage (`load_data`), explicit activation (`confirm_pending_upload`), dispatch (`transition_data_session`), single registered writer (`handle_data_session`) |
| `dashboard/callbacks/view_callbacks.py` | Active catalog controls, source labels, full Upload summary, shared reference cards, lazy forecast/cache, exports and aggregate views |
| `dashboard/data/date_parser.py` | Supported date/date-convention normalization |
| `dashboard/data/xlsx_parser.py` | Morbidity-week workbook import and sheet aliases |
| `dashboard/data/validation.py` | Canonical row validation, normalization, and gap notes |
| `dashboard/data/combine.py` | Prepare authoritative uploaded frame without sample backfill |
| `dashboard/data/mock_data.py` | Deterministic synthetic sample only |
| `dashboard/data/pdf_converter.py` | Offline table extraction and conversion review report |
| `dashboard/modeling/pipeline.py` | Coverage gate, rolling selection, untouched evaluation, refit, error band |
| `dashboard/modeling/sarima.py` | Base-model fit/fallback and decomposition |
| `dashboard/modeling/nnar.py` | Neural residual correction |
| `dashboard/modeling/metrics.py` | Hybrid combination and full-precision metrics |
| `dashboard/modeling/serialization.py` | JSON round-trip of series and model metadata |
| `dashboard/charts/figures.py` | Plotly figures and aggregate metric cards |

Forecast cache uses a dataset hash plus `CACHE_SCHEMA_VERSION = "model-audit-v5"`. New active data invalidates stale results; switching diseases reuses valid per-disease entries. Year-range controls filter displayed data without retraining a model on a truncated range. Error results are cached and displayed safely as well.

## Verification and evidence inventory

Latest full test run: **2026-09-26**, `python -X utf8 -m pytest -v --tb=short`: **85 passed, 11 warnings, 19.83 seconds**. No new full-suite run is claimed for 2026-09-27; today's changes are documentation/runtime artifacts and startup/live callback checks.

| Test file | Passed |
| --- | --- |
| `test_app_contracts.py` | 10 |
| `test_callbacks.py` | 18 |
| `test_data_ingestion.py` | 20 |
| `test_date_preprocessing.py` | 9 |
| `test_modeling.py` | 15 |
| `test_production_safety.py` | 4 |
| `test_upload_confirmation.py` | 9 |

Warnings: ten Dash DataTable deprecation notices and one pytest cache-directory permission warning. The latter did not prevent test execution. Targeted pyflakes checks of changed modules/evidence scripts passed. Old ingestion contracts use `tests.load_confirmed_data` to explicitly approve their uploads; the new gate tests call the unconfirmed path independently.

| Evidence | Contents / how to reproduce |
| --- | --- |
| `evidence/pytest-full.txt` | Actual verbose suite output, also embedded in THESIS_READINESS.md |
| `evidence/investigate.py` | `python -m evidence.investigate`; all 10 disease pipelines, independent WAPE assertions, threshold sensitivity, sample training/window diagnostics |
| `evidence/investigation.json` | Full-precision scores, predictions, tiers, warnings, source hash, environment |
| `evidence/investigation-run.txt` | Actual investigation console output |
| `evidence/real-monthly.csv` | Canonical parsed real dataset |
| `evidence/source_checks.py` | `python -m evidence.source_checks`; independent workbook totals and diagnostic seasonal average |
| `evidence/source-checks.json` | 30 matched totals, blank-week counts, seasonal-average results |
| `evidence/reproduce_upload.py` | `python -X utf8 -m evidence.reproduce_upload`; registered Dash HTTP callback flow using Flask test client |
| `evidence/malaria-reproduction.txt` | Actual Dengue=10/Malaria=500 flow: full labels before approval, unchanged active data, Malaria Top disease only after explicit approval |
| `evidence/reference-inventory.txt` | Final code/docs/test search for historical number and removed guarantee language |
| `evidence/runtime-check-2026-09-27.json` | Today's actual listening-server health and sample forecast check, installed versions |
| `evidence/dashboard*.log`, `evidence/dashboard.pid` | Current local server lifecycle artifacts; not permanent scientific evidence |

PowerShell-captured earlier text logs may be UTF-16. JSON, Python, and Markdown evidence are UTF-8. Detect a BOM when parsing logs rather than assuming one encoding.

## Recommended continuation

First read the consolidated decision ledger and preserve all current work. For technical acceptance, the unperformed step is a live-browser visual review: inspect both reference cards and Technical model details; upload the two-row Malaria fixture; confirm the full list is readable before approval and overview remains unchanged; approve and verify the new catalog/Top disease; check reset and refresh; inspect narrow-screen wrapping. HTTP assertions are already present but do not establish absence of visual clipping.

Do not start by changing model settings, generator logic, or the selection threshold. Obtain the author's actual consultation/manuscript decisions before those changes. If changing any behavior later, run the relevant tests and a fresh full suite, update evidence and the existing ledger, and explicitly separate new findings from the saved 2026-09-26 results.

### Copyable prompt for the receiving agent

> Work in C:/Users/redlo/Downloads/Antipolo-dashboard. Read AGENT_HANDOFF.md, then THESIS_READINESS.md before editing. Preserve the dirty working tree and untracked evidence. The baseline display and explicit upload-catalog confirmation are implemented; the last full suite was 85 passed. The app was launched at http://127.0.0.1:8050 on 2026-09-27; verify the current process rather than assuming it is still running. Do not change the 1.00-point threshold, mock generator, or modeling code without new authorization. Seasonal naive beats selected forecasts on two of three real diseases and six of seven sample diseases; preserve that finding. Live-browser visual verification remains unperformed. Keep all author decisions in the existing THESIS_READINESS.md ledger. Continue with the user's next specific instruction and report what was actually checked.
