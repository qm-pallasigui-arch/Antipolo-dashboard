"""Extract exact working-tree excerpts and attach captured verification evidence.

Documentation tooling only; does not edit application code or application state.
Run from the repository root after the commands documented in README.md.
"""
import ast
from collections import Counter
import contextlib
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
HERE = Path(__file__).resolve().parent
EVIDENCE = HERE / 'evidence'


def excerpt(path, symbol, first=None, last=None):
    source = (ROOT / path).read_text(encoding='utf-8')
    nodes = ast.parse(source).body
    node = None
    for part in symbol.split('.'):
        node = next(n for n in nodes if isinstance(n, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)) and n.name == part)
        nodes = node.body
    start = min([node.lineno] + [d.lineno for d in getattr(node, 'decorator_list', [])])
    end = node.end_lineno
    lines = source.splitlines()
    if first:
        start = next(i + 1 for i in range(start - 1, end) if first in lines[i])
    if last:
        end = next(i + 1 for i in range(start - 1, end) if last in lines[i])
    return '\n'.join(lines[start - 1:end]), start, end


def probes():
    from dashboard.monthly.domain import parse_upload
    from dashboard.monthly.forecasting.adapter import modeling_frame, observed_frame
    from dashboard.monthly.forecasting.config import PrototypeModelConfig
    from dashboard.monthly.forecasting.evaluation import metrics
    from dashboard.monthly.forecasting.pipeline import combine_forecast
    import numpy as np
    outputs = {}
    def capture(key, fn):
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            fn()
        outputs[key] = buffer.getvalue().rstrip()
    canonical = ROOT / 'Antipolo_ICD10_Canonical_Monthly_2016_2025.csv'
    dataset = parse_upload(canonical.read_bytes(), canonical.name)
    workbook = ROOT / 'Antipolo_ICD10_Canonical_Monthly_2016_2025.xlsx'
    xlsx = parse_upload(workbook.read_bytes(), workbook.name)
    capture('loading', lambda: print(json.dumps(dict(
        csv_observations=len(dataset['observations']), xlsx_observations=len(xlsx['observations']),
        matching_signature=dataset['dataset_signature'] == xlsx['dataset_signature'],
        dataset_signature=dataset['dataset_signature'],
        candidates=[b['icd10_block'] for b in dataset['blocks']]), indent=2)))
    capture('states', lambda: print(json.dumps(dict(sorted(Counter(r['observation_status'] for r in dataset['observations']).items())), indent=2)))
    frame = modeling_frame([r for r in dataset['observations'] if r['icd10_block'] == 'A00-A09'])
    capture('dates', lambda: print(json.dumps(dict(
        block='A00-A09', first=str(frame.actual_timestamp.min().date()), last=str(frame.actual_timestamp.max().date()),
        canonical_months=len(frame), observed_months=len(observed_frame(frame)),
        unavailable_years_have_only_null_counts=bool(frame.loc[frame.year.isin([2020, 2022]), 'consultation_count'].isna().all())), indent=2)))
    capture('metrics', lambda: print(json.dumps(dict(
        inputs={'actual': [10, 20, 30], 'predicted': [12, 18, 33], 'mase_scale': 2},
        result=metrics([10, 20, 30], [12, 18, 33], mase_scale=2),
        zero_scale_result=metrics([10, 20, 30], [12, 18, 33], mase_scale=0)), indent=2)))
    capture('combine', lambda: print(json.dumps(dict(
        inputs={'base': [-2, 10, 20], 'correction': [-4, 0.5, 7]},
        baseline_hybrid_applied_correction=combine_forecast(np.array([-2., 10., 20.]), np.array([-4., .5, 7.]), PrototypeModelConfig())), indent=2)))
    verified = json.loads((EVIDENCE / 'canonical-verification.json').read_text(encoding='utf-8'))
    capture('real', lambda: print(json.dumps(dict(
        input_file=verified['input_file'], is_prototype=verified['is_prototype'], methodology_status=verified['methodology_status'],
        statuses=verified['statuses'], stored_monthly_values=verified['stored_monthly_values'],
        ranked_blocks=len(verified['ranking']['rankings']), top_five_status=verified['ranking']['top_five_status']), indent=2)))
    capture('ranking', lambda: print(json.dumps({k: verified['ranking'][k] for k in ('forecast_months', 'rankings', 'top_five_status', 'attempted_blocks', 'model_statuses', 'failed_blocks')}, indent=2)))
    capture('evaluation', lambda: print(json.dumps({'A00-A09': verified['evaluations'].get('A00-A09')}, indent=2)))
    capture('data_quality', lambda: print(json.dumps([{k: b[k] for k in ('icd10_block', 'reported_month_count', 'observed_zero_count', 'coverage_summary')} for b in verified['data_quality']], indent=2)))
    (EVIDENCE / 'probe-outputs.json').write_text(json.dumps(outputs, indent=2), encoding='utf-8')
    (EVIDENCE / 'probe-outputs.txt').write_text('\n\n'.join(f'[{k}]\n{v}' for k, v in outputs.items()), encoding='utf-8')
    return outputs


def main():
    outputs = probes()
    tests = (EVIDENCE / 'pytest-verified.txt').read_text(encoding='utf-8').splitlines()
    listings = []
    def add(title, path, symbol, description, evidence, *, first=None, last=None, probe=None, scope='Active implementation; verified by the named existing test(s).'):
        code, start, end = excerpt(path, symbol, first, last)
        test_lines = [line for line in tests if any(name in line for name in evidence) and ('PASSED' in line or 'SKIPPED' in line)]
        if evidence and not test_lines:
            raise ValueError(f'No captured test evidence for {title}')
        actual = '\n'.join(test_lines)
        if probe:
            actual = outputs[probe] + ('\n\n' + actual if actual else '')
        if not actual:
            raise ValueError(f'No actual output for {title}')
        listings.append(dict(number=len(listings)+1, title=title, path=path, symbol=symbol,
            description=description, code=code, start=start, end=end, actual=actual, scope=scope,
            evidence=evidence, probe=probe, source_sha256=hashlib.sha256((ROOT/path).read_bytes()).hexdigest()))

    domain = 'dashboard/monthly/domain.py'
    store = 'dashboard/monthly/store.py'
    model = 'dashboard/monthly/forecasting/'
    service = 'dashboard/monthly/services/forecast_service.py'
    ranking = 'dashboard/monthly/services/ranking_service.py'
    repo = 'dashboard/monthly/repositories/'
    sys_test = 'tests/test_monthly_system.py::'
    proto_test = 'tests/test_prototype_pipeline.py::'
    hybrid_test = 'tests/test_hybrid_forecast.py::'
    real_scope = 'ACTIVE provisional model path. Output is the real-library canonical integration run (seven candidates assessed), not final thesis validation or a direct print statement in this function.'

    add('Dataset loading from CSV and XLSX', domain, 'parse_upload',
        'Reads CSV bytes or selects and combines monthly worksheets from XLSX. Supporting worksheets are excluded; normalized data retain a raw-file SHA-256. This is the active loader; the bundled canonical file is not automatically activated.',
        [sys_test+'test_upload_normalization_and_roundtrip', sys_test+'test_workbook_supporting_sheets_do_not_become_observations'], probe='loading',
        scope='Direct invocation on both repository canonical files, followed by existing synthetic upload tests. No application dataset is activated by this probe.')
    add('CSV/XLSX schema and record validation', domain, 'normalize',
        'Checks required fields, approved years, block identifiers, descriptions and duplicate block/month keys before interpreting observation status. parse_upload above also enforces the 10 MB limit and supported formats.',
        [sys_test+'test_invalid_data', sys_test+'test_workbook_combines_monthly_sheets_and_rejects_bad_data'],
        last="raise DataError(f'Duplicate block/year/month: {key}')")
    add('Observed-zero and unavailable-period handling', domain, 'normalize',
        'Retains an explicit zero as observed_zero, requires a valid status for null counts, rejects unavailable-year observations, and constructs the actual 2016–2025 monthly grid without imputing unknown values. Annual entries must contain all twelve observed months.',
        [sys_test+'test_semantics_and_data_quality'], first="        status = row.get('observation_status')", last='source_year_available=y in AVAILABLE_YEARS))', probe='states',
        scope='Canonical status counts from the direct loading probe; the synthetic semantics test additionally exercises explicit observed zeros.')
    add('Actual monthly timestamp construction', model+'adapter.py', 'modeling_frame',
        'Creates first-of-month timestamps from each row’s real year and month_number; rejects duplicate dates and mixed-block model inputs. No synthetic year-2000 timeline is constructed.',
        [proto_test+'test_actual_dates_and_calendar_lags_preserve_unknowns'], probe='dates')
    add('Observed training-row selection', model+'adapter.py', 'observed_frame',
        'Includes observed and observed_zero rows with non-null counts for fitting, while leaving unavailable periods in the canonical frame.',
        [proto_test+'test_actual_dates_and_calendar_lags_preserve_unknowns'])
    add('Prophet base model and baseline comparator', model+'prophet_model.py', 'generate_prophet_base',
        'Fits Prophet on observed actual dates, then returns fitted values and forecasts at the requested real months. Fitting failures carry the explicit prophet_failed status. Settings come from the provisional configuration.',
        [], probe='real', scope=real_scope)
    add('Prophet residual targets and training features', model+'features.py', 'generate_residual_training_data',
        'Computes observed count minus fitted Prophet value and creates usable lagged residual rows. These are IN-SAMPLE residuals in the active prototype, not rolling-origin forecast errors; insufficient residual history raises an explicit status.',
        [proto_test+'test_residual_history_status'], probe='real', scope=real_scope)
    add('Calendar-month residual lags', model+'features.py', 'lag_features',
        'Looks back by actual calendar months. Missing months become NaN features for native XGBoost missing-value handling; source observations are not compressed, interpolated or zero-filled.',
        [proto_test+'test_actual_dates_and_calendar_lags_preserve_unknowns'])
    add('XGBoost residual-model fitting', model+'xgboost_residual.py', 'fit_xgboost_residual_model',
        'Fits the only operational residual learner, XGBRegressor, with configured seed, parameters and CPU limits. Failure does not substitute another algorithm.',
        [], probe='real', scope=real_scope)
    add('Recursive residual forecast and trailing-gap bridge', model+'xgboost_residual.py', 'predict_residuals',
        'Predicts residuals one actual calendar month at a time, including any trailing gap before the requested forecast origin. Predicted residuals enter recursive model history only, not canonical observations.',
        [], probe='real', scope=real_scope)
    add('Clipped and weighted Prophet + XGBoost combination', model+'pipeline.py', 'combine_forecast',
        'Clips residual corrections to the configured range, applies the correction weight and floors forecasts at zero. Defaults are clip ±1 and weight 0.1, so the applied adjustment is at most ±0.1 consultations per month.',
        [], probe='combine', scope='Direct execution on explicitly synthetic numerical inputs using the current default configuration; no epidemiological interpretation is claimed.')
    add('Operational hybrid architecture enforcement', model+'hybrid.py', 'HybridModel.generate',
        'Requires both Prophet and completed XGBoost correction, validates finite values for every requested month, and returns the nonnegative hybrid plus the separate baseline. It does not select a different model when the corrector fails.',
        [hybrid_test+'test_hybrid_chronology_persistence_failure_and_activation'], scope='Existing synthetic workflow test; verifies combination, validation and persistence contracts, not statistical model accuracy.')
    add('Chronological train/test split', model+'evaluation.py', 'build_chronological_split',
        'Uses the last observed reporting year as the test set and earlier calendar years as training. The latest reported year is selected per block and need not be 2025 for every block.',
        [proto_test+'test_split_is_generic_and_scale_uses_only_training'])
    add('Baseline and hybrid chronological evaluation', model+'evaluation.py', 'evaluate_prototype',
        'Refits both components using only pre-test data, computes Prophet and hybrid errors on the held-out reported months, and records training cutoff, predictions and scale. Component failures make evaluation unavailable; this is a provisional single holdout, not approved final validation.',
        [proto_test+'test_workflow_invokes_both_models_and_evaluation'], probe='evaluation',
        scope='A00-A09 evaluation printed from the newly executed canonical verification artifact. The accompanying workflow test stubs the component fitter and verifies orchestration only.')
    add('Mean Absolute Error (MAE)', model+'evaluation.py', 'metrics',
        'Calculates mean absolute prediction error after checking paired nonempty inputs and finite errors. MAE, RMSE and MASE share this one function; it is reproduced intact in listings 15–17 to avoid inventing separate implementations.',
        [], probe='metrics', scope='Direct execution of metrics on the synthetic inputs printed below.')
    add('Root Mean Squared Error (RMSE)', model+'evaluation.py', 'metrics',
        'Calculates the square root of mean squared error in the same active metrics function. Input and output below are a numerical verification example, not model performance on official observations.',
        [], probe='metrics', scope='Same direct numerical probe as listing 15; this is not a separate RMSE function.')
    add('Mean Absolute Scaled Error (MASE)', model+'evaluation.py', 'metrics',
        'Divides MAE by a positive finite supplied scale. Missing, zero or invalid scales return None (JSON null); unavailable MASE is not reported as zero.',
        [], probe='metrics', scope='Same direct numerical probe as listing 15, including undefined MASE for zero scale.')
    add('Training-only calendar-season MASE scale', model+'evaluation.py', 'training_mase_scale',
        'Computes mean absolute differences only for observed training values with an observed partner the configured number of calendar months earlier (default twelve). It excludes held-out values and does not compress gaps.',
        [proto_test+'test_split_is_generic_and_scale_uses_only_training'])
    add('Twelve-month forecast calendar and run metadata', service, 'ForecastService.run',
        'Restricts execution to admins and exactly twelve months, checks the dataset and records descriptive data quality without a coverage gate, and builds the next twelve first-of-month dates from the canonical dataset endpoint. With the enforced 2016–2025 grid, the forecast origin is December 2025 and future months are January–December 2026, even when a block’s last observation is earlier.',
        [hybrid_test+'test_hybrid_chronology_persistence_failure_and_activation'],
        last="self.store.audit(user['id'], 'forecast_execution', result['forecast_run_id'])")
    add('Monthly forecast values and projected twelve-month total', service, 'ForecastService.run',
        'Stores twelve monthly hybrid predictions and calculates projected_total by summing those exact values. This total, not historical annual Top-Five membership, drives projected ranking.',
        [proto_test+'test_prototype_persistence_and_final_isolation'],
        first='        try:', last='            self.repository.save(result)')
    add('Full ICD-10 ranking and comparability checks', ranking, 'rank_forecasts',
        'Accepts only current completed hybrid results with the same dataset, run group, mode, configuration and twelve consecutive months. Recomputes totals from monthly values, ranks all successful blocks descending, and breaks equal totals by block code for display.',
        [hybrid_test+'test_rank_all_seven_and_reject_incomparable_results'],
        last='ranked = [dict(rank=n, **row) for n, row in enumerate(totals, 1)]', probe='ranking',
        scope='Ranking printed from the real canonical run; the synthetic seven-result test additionally proves all-seven ranking and comparability rejection. All seven candidates are attempted; technical model failures can yield fewer than seven completed forecasts.')
    add('Projected Top Five selection and unavailability', ranking, 'rank_forecasts',
        'Returns the first five already-ranked totals only when at least five forecasts succeeded. With fewer successes it returns an empty Top Five and retains the complete available ranking. The scope is restricted to represented forecastable blocks.',
        [hybrid_test+'test_batch_ranking_and_report', hybrid_test+'test_rank_all_seven_and_reject_incomparable_results'],
        first='    return dict(ranking_run_id=')
    add('Forecast failure status and notification handling', service, 'ForecastService.run',
        'Persists component-specific or generic failure status, removes incomplete forecast output, emits an admin notification and raises ModelFailure. Successful completion sends a separate notification. No Prophet-only fallback is executed.',
        [proto_test+'test_failures_are_persisted_without_substitution'], first='        except Exception as exc:')
    add('Forecast and monthly-value persistence', repo+'forecast_repository.py', 'ForecastRepository.save',
        'Transactionally upserts run metadata and, for current completed hybrids, stores individual forecast-month values with Prophet baselines. Store.connect routes these statements to SQLite locally or PostgreSQL when configured.',
        [proto_test+'test_prototype_persistence_and_final_isolation'], probe='real',
        scope='Verified on isolated local SQLite databases, including real model results. This does not establish successful Supabase persistence.')
    add('Supabase PostgreSQL connection boundary', repo+'database.py', 'postgres_connection',
        'Connects through psycopg with SSL required and a server-side private schema. Configured PostgreSQL failures propagate instead of silently falling back to SQLite.',
        ['tests/test_supabase_persistence.py::test_supabase_restart_persistence_and_rbac'],
        scope='ACTIVE conditional cloud implementation, UNVERIFIED against live Supabase in this audit. The dedicated-cloud test was deliberately left disabled for this local audit; SKIPPED is not a pass or a cloud connection result.')
    add('PostgreSQL SQL and transaction adaptation', repo+'database.py', 'postgres_sql',
        'Adapts placeholders, identity columns, binary/floating types and ignore-on-conflict SQL. Dataset/account serialization uses a PostgreSQL advisory transaction lock.',
        [proto_test+'test_postgres_adapter_transactions_and_types'], scope='Local unit test of SQL conversion and row access, not execution on a PostgreSQL server.')
    add('Dataset staging and source-version persistence', store, 'Store.stage',
        'Validates an admin upload, assigns a candidate identifier, and persists normalized content, source signature, raw bytes and uploader as pending. Invalid uploads trigger audit and data-quality notifications.',
        [sys_test+'test_activation_is_explicit_atomic_and_persistent'])
    add('Explicit atomic dataset activation', store, 'Store.activate',
        'Activates only an existing pending candidate within a transaction, retires the previous active version without deleting it, and records audit and neutral coverage/data-quality notifications.',
        [sys_test+'test_activation_is_explicit_atomic_and_persistent'])
    add('Password hashing and authorized account creation', 'dashboard/monthly/security.py', 'create_user',
        'Validates username/password/role, hashes passwords, allows bootstrap only before the first account, and otherwise requires an administrator. User creation is audited.',
        [sys_test+'test_authentication_and_user_management'])
    add('Login authentication and revocable sessions', 'dashboard/monthly/security.py', 'install_security.login',
        'Checks password hashes and active status, limits repeated failures per username, rotates session tokens on successful login, and records eight-hour server-side sessions. The excerpt stops before login-page HTML rendering.',
        [sys_test+'test_authentication_and_user_management', sys_test+'test_expired_login_form_recovers_without_authenticating'],
        last="error = 'Login failed. Check credentials and account status; after repeated failures wait 15 minutes.'")
    add('Authenticated request and CSRF protection', 'dashboard/monthly/security.py', 'install_security.protect',
        'Resolves active users from unexpired persisted sessions; validates form CSRF or Dash same-origin request properties; rejects unauthenticated private requests.',
        [sys_test+'test_authentication_and_user_management', sys_test+'test_login_recovery_does_not_allow_cross_origin_posts'])
    add('Administrator role-based authorization', store, 'require_admin',
        'Provides the server-side active-admin gate used by upload, activation, forecast and account operations. Viewers cannot bypass it by forging Dash callback requests.',
        [sys_test+'test_forged_viewer_callbacks_and_admin_workflow'])
    add('Active dataset retrieval and data-quality refresh', store, 'Store.active',
        'Retrieves only the active dataset payload and recomputes descriptive coverage for all seven candidates before serving dashboard data.',
        [sys_test+'test_activation_is_explicit_atomic_and_persistent'])
    add('Latest model-attempt retrieval and configuration isolation', repo+'forecast_repository.py', 'ForecastRepository.latest_attempt',
        'Selects the latest compatible attempt, including running and failed runs. Dashboard and reports show this actual status; an older successful forecast cannot mask a failed latest attempt.',
        ['tests/test_data_quality_modeling.py::test_failed_latest_attempt_is_visible_in_pages_and_reports', proto_test+'test_prototype_persistence_and_final_isolation'])
    add('Dashboard data preparation', 'dashboard/monthly/views.py', 'page_content',
        'Resolves the selected block, retrieves a relevant current forecast, finds the latest non-null observation, and composes projected rankings, coverage cards, trends and status for the Dashboard.',
        [sys_test+'test_reports_and_notification_visibility', 'tests/test_monthly_performance.py::test_non_forecast_pages_do_not_read_forecast_history'],
        first='    if not dataset:', last='html.P(coverage_text(block), className=')
    add('Report construction and persistence', 'dashboard/monthly/reports.py', 'build_report',
        'Allows authenticated active users to generate reports containing source provenance, historical statuses, available forecasts/evaluation, annotations and projected ranking. It persists the report, audit event and recipient-specific notification.',
        [sys_test+'test_reports_and_notification_visibility', hybrid_test+'test_batch_ranking_and_report'])
    add('CSV export preserving missing and zero values', 'dashboard/monthly/reports.py', 'export_csv',
        'Exports dated historical values with observation statuses, then any forecast values with model and provisional-status labels. Null counts remain blank; observed zeros remain zero.',
        [sys_test+'test_reports_and_notification_visibility', hybrid_test+'test_hybrid_chronology_persistence_failure_and_activation'])
    add('HTML and JSON report download routing', 'dashboard/monthly/ui.py', 'install.action',
        'Builds a report and selects HTML, CSV or JSON serialization for the Dash download response. HTML uses export_html; JSON uses the persisted report structure. The following notification branch marks only filtered visible items as read.',
        [sys_test+'test_forged_viewer_callbacks_and_admin_workflow', hybrid_test+'test_batch_ranking_and_report'],
        first="            elif trigger in ('m-report-html',", last="                text = 'Report generated and recorded.'",
        scope='Existing tests verify callback report generation and HTML export content. They do not constitute a browser download test for every file format. The canonical verifier also generated evidence/canonical-verification.html.')
    add('Notification creation and audience-aware retrieval', store, 'Store.notify',
        'Persists notifications with optional role/user targets, severity and related-record context. Retrieval and read marking are listed separately below.',
        [sys_test+'test_reports_and_notification_visibility'])
    add('Notification visibility and per-user read state', store, 'Store.notifications',
        'Joins recipient-specific read records and limits results to the current user’s role and optional direct user target.',
        [sys_test+'test_reports_and_notification_visibility'])
    add('Marking only visible notifications read', store, 'Store.mark_read',
        'Intersects requested identifiers with notifications visible to the current user before inserting per-user read markers.',
        ['tests/test_monthly_presentation.py::test_read_selection_cannot_mark_hidden_notifications'])
    add('All-seven-candidate data-quality refresh', 'dashboard/monthly/data_quality.py', 'refresh_dataset',
        'Rebuilds descriptive coverage entries for every configured ICD-10 candidate, including blocks absent from an upload, and removes obsolete derived classifications from older payloads. Source observations and signatures are preserved; no block is excluded from modeling.',
        [sys_test+'test_semantics_and_data_quality', 'tests/test_data_quality_modeling.py::test_old_derived_classifications_are_rebuilt_without_changing_source'], probe='data_quality')
    add('Batch forecasting and ranking orchestration', service, 'ForecastService.run_all',
        'Passes all seven candidates to the model workflow under one group, records each model outcome and genuine failures, persists the aggregate ranking and emits completion notifications. No coverage-based continue or pre-model classification remains.',
        [hybrid_test+'test_batch_ranking_and_report', 'tests/test_data_quality_modeling.py::test_all_seven_attempted_even_with_twelve_or_no_observations'], probe='real', scope=real_scope)
    add('Fixed component workflow and evaluation orchestration', model+'pipeline.py', 'forecast_components',
        'Executes Prophet fitting, residual construction, XGBoost fitting, recursive prediction and clipped/weighted combination in order. PrototypeWorkflow invokes this function for full-history forecasting and again through evaluate_prototype for the holdout.',
        [], probe='real', scope=real_scope)
    add('Provisional configuration and methodology guard', model+'config.py', 'PrototypeModelConfig',
        'Centralizes the actual active defaults and validates supported residual, gap and evaluation methods. In-sample residual training and last-reported-year evaluation are the only currently accepted methods; these settings must not be described as approved Chapter 3 parameters.',
        [sys_test+'test_final_forecast_requires_approved_methodology', proto_test+'test_prototype_persistence_and_final_isolation'])
    add('Availability-aware historical and forecast chart', 'dashboard/monthly/charts.py', 'trend_figure',
        'Plots actual monthly dates with connectgaps=False, distinct observed-zero markers and unavailable-year shading. Shows separate Prophet and hybrid series, and draws intervals only when real bounds exist.',
        [sys_test+'test_semantics_and_data_quality', 'tests/test_monthly_presentation.py::test_intervals_are_never_invented'])
    add('Local or PostgreSQL transactional store routing', store, 'Store.connect',
        'Uses the configured PostgreSQL boundary for cloud persistence, otherwise opens local SQLite with foreign keys and transactional commit/rollback. It closes SQLite connections explicitly and never catches a cloud failure to substitute local storage.',
        [sys_test+'test_activation_is_explicit_atomic_and_persistent', 'tests/test_supabase_persistence.py::test_supabase_restart_persistence_and_rbac'],
        scope='SQLite routing and persistence verified locally; live PostgreSQL branch remains unverified (integration test skipped).')
    add('Ranking snapshot persistence', repo+'ranking_repository.py', 'RankingRepository.save',
        'Persists the full ranking and Top Five snapshot, dataset signature, group metadata and generation time as a single JSON payload through the shared transactional store.',
        [hybrid_test+'test_batch_ranking_and_report'])
    add('Prototype full-history forecast and holdout evaluation', model+'pipeline.py', 'PrototypeWorkflow.__call__',
        'Builds the real-date frame, evaluates the chronological holdout, then invokes the fixed components for future dates, and returns baseline plus the already weighted correction to HybridModel. It records in-sample residual provenance and trailing-gap/short-history warnings.',
        [proto_test+'test_workflow_invokes_both_models_and_evaluation'], probe='real', scope=real_scope)
    add('Printable HTML report export', 'dashboard/monthly/reports.py', 'export_html',
        'Creates a standalone HTML report with escaped table content, embedded Plotly history/forecast chart, provenance, evaluation, complete ranking and Top Five availability. No uncertainty interval is fabricated.',
        [sys_test+'test_reports_and_notification_visibility', hybrid_test+'test_batch_ranking_and_report'],
        scope='Existing synthetic report assertions plus the generated canonical-verification.html from the real canonical run. See browser-verified.txt for the separate browser workflow result.')
    add('Descriptive data-quality and coverage statistics', 'dashboard/monthly/data_quality.py', 'coverage_summary',
        'Counts distinct reported months, observed zeros and available reporting years, and lists unknown periods. These are descriptive statistics, not pre-model inclusion criteria. All seven candidates enter the model workflow irrespective of these counts.',
        ['tests/test_data_quality_modeling.py::test_all_seven_attempted_even_with_twelve_or_no_observations', sys_test+'test_semantics_and_data_quality'], probe='data_quality')

    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    header = f'''# Python Codes / Program Listings

Audit date: 30 October 2026 (Asia/Manila). Working-tree basis: Git HEAD `{head}`, plus the current files on disk. This is not a claim that the working tree was clean. File hashes and exact line ranges are in [listing-manifest.json](listing-manifest.json).

**The finalized model family is Prophet + XGBoost, but the repository currently executes a provisional prototype.** These listings document active implementation, not approved final thesis analytical results. Final-mode generation is blocked; methodology approval remains outstanding. See [AUDIT.md](AUDIT.md) before describing the system as finalized in the thesis.

Only operational monthly-path code is excerpted. Standalone Prophet is the baseline comparator. Archived or unused alternatives are excluded. Excerpts are copied exactly, including original indentation, comments and decorators; partial blocks are explicitly identified by line range and are not standalone scripts. Imports and enclosing context remain in the source file. Coverage is descriptive: all seven candidates enter modeling, and technical failures are recorded as outcomes. Execution remains provisional pending Chapter 3 approval.

**Output provenance:** `kotlin` fences below are the requested display format; the content is Python/pytest output, not Kotlin code. PASSED lines are verbatim selected lines from [pytest-verified.txt](evidence/pytest-verified.txt). Direct probes and displayed selections from the fresh real-model artifact are captured in [probe-outputs.txt](evidence/probe-outputs.txt), generated by [build_listings.py](build_listings.py). Canonical-run evidence is [canonical-verification.json](evidence/canonical-verification.json), [execution log](evidence/canonical-verified.txt), and [HTML report](evidence/canonical-verification.html). Synthetic unit tests prove software behavior, not model accuracy. A SKIPPED cloud test proves no cloud persistence.

'''
    sections = [header]
    for item in listings:
        i = item['number']
        link = '../../' + item['path']
        sections.append(f'''**Python Code {i}: {item['title']}**

**Source File:**\\
`{item['path']}`

**Function/Class:**\\
`{item['symbol']}`

**Description:**\\
{item['description']}

Source span: lines {item['start']}–{item['end']} of [{Path(item['path']).name}]({link}). Verification scope: {item['scope']}

**Code:**
```python
{item['code']}
```

**Actual Output:**
```kotlin
{item['actual']}
```

''')
    sections.append('## Final inventory\n\n“Yes” means inclusion as implementation documentation with the qualifications above, not approval of provisional model results.\n\n| Code No. | Title | Source File | Function/Class | Active/Legacy | Included in Thesis? |\n| -------- | ----- | ----------- | -------------- | ------------- | ------------------- |\n')
    for item in listings:
        qualification = 'Yes — cloud path unverified' if item['number'] == 25 else 'Yes — document current implementation'
        sections.append(f"| {item['number']} | {item['title']} | `{item['path']}` | `{item['symbol']}` | ACTIVE | {qualification} |\n")
    sections.append('| — | Superseded weekly/PIDSR and older model implementations | `archive/legacy-implementation-20261026/` | Multiple | LEGACY / ARCHIVED | No |\n| — | Retired inference adapters and prototype engine | `archive/forecasting/` | Multiple | LEGACY / ARCHIVED | No |\n| — | Historical tuning and pre-final handoff | `archive/model_development/` | Multiple | ARCHIVED DEVELOPMENT | No |\n| — | Unwired alternate fitting helpers | `dashboard/monthly/forecasting/prophet_model.py`; `xgboost_residual.py` | `fit_predict` | NON-OPERATIONAL HELPERS | No |\n| — | Unwired chronological-error validator | `dashboard/monthly/forecasting/features.py` | `validate_error_rows` | TESTED HELPER; NOT ACTIVE TRAINING | No |\n')
    (HERE / 'PYTHON_CODE_LISTINGS.md').write_text(''.join(sections), encoding='utf-8')
    manifest = {'git_head': head, 'audit_date': '2026-10-30', 'timezone': 'Asia/Manila',
        'listings': [{k: v for k, v in item.items() if k not in ('code', 'actual')} for item in listings]}
    (HERE / 'listing-manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f'Wrote {len(listings)} exact-source listings and inventory.')


if __name__ == '__main__':
    main()
