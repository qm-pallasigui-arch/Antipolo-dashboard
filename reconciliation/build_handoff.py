"""Build the consolidated handoff from checked local evidence; does not change models."""
from pathlib import Path
import json,hashlib,subprocess,zipfile,difflib
ROOT=Path('.')
def read(p):return Path(p).read_text(encoding='utf-8-sig')
def line(file,needle):return next((n for n,x in enumerate(read(file).splitlines(),1) if needle in x),1)
def ref(file,needle=''):return f'`{file}:{line(file,needle)}`'
def git(*args):return subprocess.check_output(['git',*args],text=True).strip()
base=json.loads(read('reconciliation/baseline-hashes.json'))
old=zipfile.ZipFile('reconciliation/baseline.zip')
current={p.as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in ROOT.rglob('*') if p.is_file() and not any(part in ('.git','__pycache__','.pytest_cache','.browser-tools','.browser-cache') for part in p.parts) and not p.name.endswith('.zip')}
modified=[p for p,h in base.items() if p in current and current[p]!=h]
deleted=[p for p in base if not Path(p).exists()]
assert not deleted,deleted
changes={
'README.md':('Conditional primary and stale interpretation','Current mandatory hybrid/reproduction/limitations','Research reconciliation','Documentation/source trace'),
'ARCHITECTURE.md':('Fixed SARIMA and cross-family fallback','Exact bounded search, residuals, split and provenance contract','Match actual architecture','Source trace and model tests'),
'CHANGELOG.md':('Historical development record','New reconciliation entry; prior entries preserved','Version transparency','Baseline comparison'),
'dashboard/config.py':('Combined source mapped to Measles','Measles-Rubella preserved; historical threshold unused','Preserve source definition','Label tests'),
'dashboard/callbacks/data_callbacks.py':('Upload lacked population/classification/dataset metadata','Metadata defaults/preservation, unverified eligibility notice','Population separation','Upload and provenance tests'),
'dashboard/callbacks/view_callbacks.py':('Selected-model labels, limited metadata','Mandatory primary labels, candidate/benchmark/failure details, source-bearing CSV and new cache schema','Transparent model/provenance','Callback tests; actual three-disease exports and traces'),
'dashboard/charts/figures.py':('Selected candidate/alternative labels','Primary hybrid and benchmark labels','Mandatory architecture','Trace regression tests'),
'dashboard/data/combine.py':('Date preparation without metadata defaults','Separate category guard and metadata retained','Prevent mixed populations','Provenance tests'),
'dashboard/data/date_parser.py':('Invalid values dropped and metadata discarded in aggregation','Reject invalid dates/counts/duplicates/synthetic relabel; preserve metadata','No silent data invention','Date and provenance tests'),
'dashboard/data/validation.py':('Invalid rows dropped, negatives clipped, counts rounded, duplicate first chosen','Reject invalid labels/counts/calendar fields/duplicates','Preserve original observations','Ingestion tests'),
'dashboard/data/xlsx_parser.py':('Blanks silently skipped; partial weeks not identified','Blank/week coverage warnings, incomplete flag, strict numeric validation','Distinguish unknown from zero','Independent1590 cells/360 monthly checks and tests'),
'dashboard/modeling/metrics.py':('Missing neural correction filled with zero','Exact aligned finite component contract','No fabricated neural component','Alignment/finite tests and numerical verification'),
'dashboard/modeling/nnar.py':('Insufficient history returned zero correction','Explicit failure; baseline architecture plus iteration/convergence metadata','Honest component status','NNAR/failure tests'),
'dashboard/modeling/pipeline.py':('WAPE-gated hybrid/base primary','Mandatory hybrid, independent benchmarks, raw components, coverage/provenance validation and preserved failure evidence','Approved hybrid and separation','Model tests;20 numerical records; rolling/error-band checks'),
'dashboard/modeling/sarima.py':('Fixed(1,1,1)(0,1,1) with Holt-Winters/drift fallback','12 bounded candidates, diagnostics, lowest valid AIC, neural retry; typed failures','Disease-specific identification','Actual40 window searches; failure/retry tests'),
'dashboard/modeling/serialization.py':('Baseline arrays/scalars only','Raw components, seasonal-naive, rolling arrays and diagnostics; legacy optional fields','Reviewable provenance','Roundtrip/export tests'),
'dashboard/ui/layout.py':('Conditional model-selection explanatory copy','Mandatory hybrid and provisional scope/calendar limitations','Match approved decisions','Component contracts; browser review pending'),
}
for p in modified:
 if p.startswith('tests/'):
  changes[p]=('Tests of historical behavior','Updated approved contracts and regression cases','Verify revised semantics','112-test suite')
changes['dashboard/data/provenance.py']=('Absent','Shared source/population/classification boundary check','Dataset separation','Provenance tests')
changes['tests/test_provenance.py']=('Absent','Source-label, population, metadata/export and invalid-input tests','Regression coverage','Full test suite')
inventory=[]
for file in modified+['dashboard/data/provenance.py','tests/test_provenance.py']:
 before,after,reason,verification=changes.get(file,('Initial snapshot','See assignment diff','Research correction','Recorded tests/source trace'))
 if file in base:
  a=old.read(file).decode('utf-8-sig').splitlines();b=read(file).splitlines()
  first=next((j1+1 for tag,i1,i2,j1,j2 in difflib.SequenceMatcher(a=a,b=b).get_opcodes() if tag!='equal'),1)
 else:first=1
 inventory.append(f'| `{file}:{first}` | {before} | {after} | {reason} | {verification} |')
source=json.loads(read('reconciliation/source-reconciliation.json'))
original=json.loads(read('reconciliation/original-evaluation.json'))
revised=json.loads(read('reconciliation/revised-evaluation.json'))
assert len(revised['results'])==10
h=['# Antipolo thesis and dashboard: coding-agent return handoff','',
'Completed technical reconciliation on27 September2026. Assessment: **Needs revision for research claims; implemented technical corrections verified within the stated software scope.** Research/data acceptance remains partial. The original manuscript and surveillance files are unchanged.','',
'## 20.1 Executive summary','',
'Inspected the current uncommitted repository, all application/model/data/callback modules and tests, deployment/dependency manifests, historical evidence, original workbook, all three original disease PDFs, and the manuscript including tables and eight diagrams. Baseline recovery and hashes preceded edits. The current source was checked directly rather than accepting previous handoff assertions.',
'',
'Implemented mandatory SARIMA+NNAR primary forecasting, bounded disease/window-specific SARIMA identification, typed component failures/retries, preserved independent benchmarks, corrected provisional Measles-Rubella labels, source/population/classification metadata, rejection of invalid/mixed/incomplete inputs, updated tests and documentation. General disease-label uploads and explicit catalog confirmation remain. No disease-scope expansion, age estimation, source-value correction, original-manuscript edit, dependency installation, commit, deployment or external message was made.',
'',
'Verified112 tests, independent source arithmetic and20 before/after series evaluations. The revised all-age hybrid WAPE is34.86% Dengue,58.63% Leptospirosis,576.65% Measles-Rubella. Adverse results remain visible. Source transcription agrees, but eligibility/completeness/confirmed-only claims are unsupported. Browser visual rendering and clean pinned/container deployment remain unverified. No eligible ages5-19 extract, CHO interview/acceptance or expert usability results were supplied.',
'',
'Entry-point companions: docs/archive/AUDIT_MATRIX.md, docs/archive/DATA_RECONCILIATION.md, docs/archive/MODEL_EVALUATION.md, TEST_RESULTS.md, docs/archive/MANUSCRIPT_REVISION_PROPOSALS.md and the single docs/archive/DECISION_LEDGER.md. Historical docs/archive/THESIS_READINESS.md, docs/archive/AGENT_HANDOFF.md and evidence/ were preserved unchanged.','',
'## 20.2 Preserved author decisions','',
'1. **Population:** individuals aged5-19, city-wide Antipolo surveillance intended to inform public-school preparedness. Cases are not assumed contracted at school or enrolled in public schools. The age range was not changed.',
'2. **Separation:** retain all-age evaluation separately; evaluate eligible5-19 records independently when supplied. All-age results do not establish target-population performance. No populations or synthetic/real results were pooled.',
'3. **Case classification:** final analytical dataset must be confirmed-only. Existing report totals remain unverified for classification; no confirmed-only label was inferred.',
'4. **Disease coverage:** initial Dengue, Leptospirosis and provisionally combined Measles-Rubella. Final scope/classification awaits researcher/adviser/epidemiologist/CHO. No Top5 pivot; generalized upload capability is separate from thesis scope.',
'5. **Architecture:** primary prediction is SARIMA forecast plus NNAR residual forecast. SARIMA-only and seasonal naive are benchmarks, never performance-based replacements. Alternative valid SARIMA configurations are tried after neural failure; no Holt-Winters/drift/base-only or fabricated zero correction is called hybrid. Failure remains explicit.',
'6. **Identification:** disease-specific ADF assessment, ACF/PACF evidence, candidate SARIMA fitting, AIC and residual diagnostics. Search occurs inside each training window; final holdout values do not select parameters.',
'7. **Horizon:**12-month capability retained provisionally pending1/3/12-month operational interview. Thesis objective was not changed.',
'8. **Transparency:** disclose all benchmark comparisons, including worse hybrid results; retain final holdout outside search and do not claim general superiority. Prior human exposure to2025 is explicitly disclosed.',
'9. **Week conversion:** retain existing ISO-Thursday/non-ISO-week53-December conversion provisionally; obtain official CHO calendar confirmation.',
'10. **Source discrepancy:** preserve Dengue2024 printed4516 and weekly/workbook4588, difference72. No choice of corrected value was fabricated.',
'',
'**Agent implementation choices, not separately approved research protocol:**12-candidate bounds; ADF p=.05; D0/1 comparison; trend=c; common burn13; root tolerance1.000001; maxiter300; lag12 Ljung-Box warning; strict invalid-row rejection; preserving finite NNAR forecasts with convergence warnings. The neural architecture itself is unchanged. Adviser acceptance of these exact technical choices remains D17.','',
'## 20.3 Repository state','',
f'- Branch: `{git("branch","--show-current")}`; relevant HEAD: `{git("rev-parse","HEAD")}`. No new commit.',
'- Initial Git status is below; these modifications and untracked files predated this assignment. The baseline is the working tree, not HEAD.',
'```text',read('reconciliation/initial-git-status.txt').strip(),'```','',
'- Recovery: reconciliation/baseline.zip contains67 initial files, including all historical untracked evidence; baseline-hashes.json records SHA256. initial-working-tree.patch preserves the initial tracked diff. repository-history.bundle preserves local branch/tag/HEAD history; final working-tree files are in the updated ZIP.',
'- Deleted initial files: none. Authoritative original manuscript/workbook/PDFs are also bundled byte-for-byte in reconciliation/sources/. Their hashes were compared with external originals.',
'- Final Git status: see reconciliation/final-git-status.txt and the final-state inventory below. Existing uncommitted changes were not reset, cleaned, committed, or discarded.',
'',
'## 20.4 Complete change inventory','',
'This table compares assignment changes with the preserved initial working tree, not with the last commit. Line numbers identify the first changed/current line; detailed function references are in docs/archive/AUDIT_MATRIX.md current feature coverage. All previously modified files not listed here retain their initial assignment bytes.','',
'| File | Previous behavior | New behavior | Reason | Verification |','|---|---|---|---|---|',*inventory,'',
'New evidence/documentation files are inventoried at the end of this section. No source data or manuscript content was changed.','',
'## 20.5 Modeling implementation','',
f'Source: {ref("dashboard/modeling/sarima.py","def run_arima")}, {ref("dashboard/modeling/nnar.py","def run_nnar")}, {ref("dashboard/modeling/pipeline.py","def run_hybrid_pipeline")}, {ref("dashboard/modeling/metrics.py","def compute_metrics")}.',
'',
read('ARCHITECTURE.md').split('## 5. Modeling architecture\n',1)[1].split('## 6. UI',1)[0].strip(),
'',
'Extra transparency: successful fits are not proof of epidemiological fitness. ACF/PACF are retained for review and do not algorithmically expand the fixed candidate bounds. AIC comparison includes D0/1 branches on a common scored span; its adequacy and exact differencing policy deserve independent statistical scrutiny. Full candidate rejection reasons remain in JSON/UI. Failure objects preserve any completed rolling/holdout metrics and available standalone benchmarks rather than inventing a production forecast.',
'',
'## 20.6 Data verification','',
'Original source copies and SHA256:','',
'| Source | SHA256 |','|---|---|']
for key,v in source['sources'].items():h.append(f"| {Path(v['path']).name} | `{v['sha256']}` |")
mp=Path('reconciliation/sources/BRPM_Documentation (2).docx');h.append(f'| {mp.name} | `{hashlib.sha256(mp.read_bytes()).hexdigest()}` |')
h+=['',
'All1590 weekly PDF/workbook cells match, including9 source dashes retained as blanks;1581 numeric cells include636 explicit zeros. All30 annual workbook sums match weekly PDF sums. Nineteen of20 printed PDF totals match; Leptospirosis has no printed annual total. Dengue2024 remains4516 printed versus4588 weekly/workbook. Weekly rows1-53 are present;9 Dengue week53 cells2016-2024 remain unknown. Measles-Rubella week53 has2 cases2023 and5 cases2025; Dengue2025 week53 has56.',
'',
'Independent calendar aggregation yields360 monthly values/120 per disease and agrees with the revised parser. ISO Thursday assigns weeks to months; non-ISO week53 goes to December. Only2020 is an ISO53-week year within the historical period. This agreement does not authenticate the calendar or reporting completeness. Known missing/blank weeks1-52 block modeling; ambiguous week53 remains provisionally labeled. Workbook Notes incorrectly claims Dengue printed totals all match; original wording was preserved.',
'',
'None of the three source tables supplies age, enrollment or case-classification fields. All-age status follows the established author description; confirmed-only eligibility cannot be verified. Generic uploads default to unknown metadata, even if structurally similar. Evaluator labels the reviewed original dataset all-age with its workbook hash. Existing browser sessions whose old parser lost Measles-Rubella terminology must re-upload the original; genuine arbitrary Measles labels are not forcibly reinterpreted.',
'',
read('docs/archive/DATA_RECONCILIATION.md').split('## Annual totals\n',1)[1].split('## Blanks',1)[0].strip(),
'',
'## 20.7 Numerical evaluation','',
'Fresh original and revised runs each cover3 real all-age and7 synthetic series separately. Eligible age-specific results: unavailable. Complete unrounded arrays, raw components, monthly actuals, rolling folds, all selected configurations and diagnostics are in the JSON artifacts. docs/archive/MODEL_EVALUATION.md reports all four metrics for all methods; its tables are reproduced below for independent review.',
'',
read('docs/archive/MODEL_EVALUATION.md').split('## Preserved historical reported values',1)[1].split('## Interpretation and formulas',1)[0].strip(),
'',
'No hyperparameters were subsequently tuned to reduce the disclosed2025 errors. Poor Measles-Rubella performance is evidence against a broad superiority claim, not a reason to suppress the hybrid or invent a favorable dataset. The historical holdout is computationally excluded from search, but was previously examined by developers; prospective confirmation remains unresolved.',
'',
'## 20.8 Testing','',read('TEST_RESULTS.md').split('\n',1)[1].strip(),
'',
'## 20.9 Manuscript reconciliation','',
'The authoritative DOCX was not edited. docs/archive/MANUSCRIPT_REVISION_PROPOSALS.md provides44 traceable proposals: original paragraphs or diagram labels, exact replacement wording, reason, source evidence and acceptance status. The manuscript extraction includes292 XML paragraphs, three tables and eight figures. It contains introduction and Chapter2; no completed results chapter was present. Text/diagram review is not a full Word pagination/formatting proofread.',
'',
'Chapters/sections needing changes: both title dates; background/causal and superiority statements; objectives (five models vs initial three categories); significance and resource-allocation claims; population and public-school delimitation; confirmed-only eligibility vs suspected cases; historical period2016-2025 vs2016-2026/2015-2025; disease terminology; literature comparison/ref duplicates; research design; data preprocessing and COVID-imputation claims; decomposition vs model residuals; SARIMA identification; NNAR settings; metric definitions/denominators; rolling/holdout split; uncertainty; session stores vs databases/model persistence; software/dependency versions; all conflicting Figures1-8; glossary; source completeness; bibliographic validation; future-dated cover; evaluation-standard/security-scope discrepancies.',
'',
'Exact core insertion: "The primary forecast is the nonnegative sum of the SARIMA point prediction and the NNAR residual prediction. SARIMA-only and seasonal naive are reported as benchmarks on the same held-out dates; their lower errors do not replace the primary hybrid. Each SARIMA identification procedure uses only its own training window. A failed component makes the hybrid unavailable rather than triggering a different model family."',
'',
'Exact population insertion: "The approved population is individuals aged5-19 in city-wide Antipolo surveillance, with findings intended to inform public-school preparedness. Existing all-age totals are evaluated separately and do not establish performance for that population or confirmed-only cases. Enrollment or transmission within public schools is not inferred."',
'',
'Exact uncertainty insertion: "The displayed band uses the maximum historical absolute hybrid error from earlier evaluation folds and the final holdout, with a nonnegative lower bound. It is descriptive; no validated95% future prediction coverage is claimed."',
'',
'External32.22 provenance is now verified against [Olana et al.(2025), publisher Table1](https://doi.org/10.1155/tbed/7480710): national dengue SARIMA testing MAPE, train2017-2023/test2024. Its use as a local acceptance standard is unsupported. Other bibliography claims were not exhaustively authenticated.',
'',
'## 20.10 Remaining decisions','',read('docs/archive/DECISION_LEDGER.md').split('\n',1)[1].strip(),
'',
'## 20.11 Independent review requests','',
'- Check the actual search/training boundaries and whether prior2025 exposure undermines confirmatory claims despite algorithmic exclusion.',
'- Scrutinize the12-candidate bounds, D0/1 treatment, ADF policy, common AIC burn, constant trend, stability tolerance and residual whiteness warning policy; these are implementation choices, not a demonstrated optimal search.',
'- Inspect residual initialization/alignment, training-only feature scaling, recursion and finite NNAR convergence-warning policy; confirm raw addition before nonnegative clipping.',
'- Verify independent SARIMA/seasonal-naive benchmark fairness, all unfavorable arrays, MAPE/WAPE zero handling and the lack of any superiority guarantee.',
'- Cross-check1590 original weekly cells,9 unknown blanks, week53 assignment, missing age/classification and Dengue2024 totals; arithmetic agreement is not source-office approval.',
'- Review all44 manuscript proposals and conflicting figures against the original DOCX; no proposed wording is automatically accepted.',
'- Inspect UI metadata and exports; perform missing desktop/mobile browser and clean pinned/container checks. Check whether additional eligibility controls are needed when actual verified records arrive.',
'- Challenge every resolved claim using its test/source artifact; passing112 tests does not certify methodology, clinical utility or thesis readiness.',
'',
'## 20.12 Final limitations','',
'This work establishes a recoverable, tested implementation of the authorized technical corrections and auditable retrospective calculations. It does not establish target-population performance, confirmed-case eligibility, complete surveillance, official calendar correctness, corrected Dengue counts, final disease/horizon approval, validated probabilistic coverage, causal mechanisms, clinical safety, prevention, optimized medical allocation, field benefit, formal CHO acceptance, expert usability, publication readiness or a previously unseen confirmatory validation set.',
'',
'General PDF extraction remains partial for the complex original layouts; source-specific audit extraction and the workbook are verified. Source copies are bundled for researcher review, not independently authorized public redistribution. No upload label or file hash authenticates the issuing office. Exact dependency pins and browser rendering remain unverified. The current deliverable is ready for independent technical/research review, not a claim of final thesis acceptance.',
'',
'### Return files and recovery','',
'Return docs/archive/CHATGPT_RETURN_HANDOFF.md, Antipolo-dashboard-reconciled-2026-09-27.zip, TEST_RESULTS.md, docs/archive/MODEL_EVALUATION.md and docs/archive/MANUSCRIPT_REVISION_PROPOSALS.md. The ZIP includes these reports, docs/archive/AUDIT_MATRIX.md, docs/archive/DATA_RECONCILIATION.md, docs/archive/DECISION_LEDGER.md, original source copies, current code/tests, baseline.zip and repository-history.bundle. Restore the baseline ZIP into a new directory to inspect initial uncommitted files; do not overwrite the active workspace. Git history can be recovered from the verified bundle in a separate directory, then overlaid with the delivered working-tree files. No original branch was modified by a commit.',
'',
'Copyable return message:',
'',
'"Continue my Antipolo thesis audit using the attached coding-agent handoff and updated repository. Independently review the implementation, reconcile it against my original manuscript and established research decisions, challenge unsupported claims, identify remaining inconsistencies, and ask me only the next material clarification questions. Do not assume the coding agent\'s conclusions are correct simply because tests passed."',
]
# Add every new artifact path to section20.4. Generated delivery ZIP/manifests self-reference is intentionally excluded.
artifact=[]
for p in sorted(ROOT.rglob('*')):
 file=p.as_posix()
 if not p.is_file() or file in base or file.startswith('.git/') or '__pycache__' in p.parts or '.pytest_cache' in p.parts or file.endswith('.zip') or file in ('dashboard/data/provenance.py','tests/test_provenance.py'):continue
 if file=='docs/archive/CHATGPT_RETURN_HANDOFF.md':continue
 purpose='Review artifact / retained evidence; see corresponding report'
 if file.startswith('reconciliation/sources/'):purpose='Byte-identical authoritative original copy; SHA256 verified'
 elif file.endswith('.py'):purpose='Reproducible audit/evaluation/report script'
 elif file.endswith('.json'):purpose='Machine-readable calculations, metadata, arrays or verification results'
 elif file.endswith('.csv'):purpose='Inspectable source reconciliation or actual forecast export'
 elif file.endswith('.bundle'):purpose='Recoverable local Git history; git bundle verify passed'
 elif file.endswith('.png'):purpose='Original manuscript diagram or source-report rendering'
 elif file.endswith('.md'):purpose='Requested consolidated report, proposals, matrices or current ledger'
 artifact.append(f'| `{file}:1` | Absent at assignment start | {purpose} | Independent review/recovery | Source hashes, recorded execution or document inspection |')
artifact+=['| `reconciliation/baseline.zip` | Absent |67-file initial working-tree snapshot | Recovery | baseline-hashes.json |','| `docs/archive/CHATGPT_RETURN_HANDOFF.md:1` | Absent | Consolidated20.1-20.12 handoff | Required return protocol | Final artifact checks |','| `Antipolo-dashboard-reconciled-2026-09-27.zip` | Absent | Current working-tree/source/evidence package | Return/recovery | ZIP CRC and manifest verification |']
pos=h.index('## 20.5 Modeling implementation')
h[pos:pos]=['### Added artifacts','', '| File | Previous behavior | New behavior | Reason | Verification |','|---|---|---|---|---|',*artifact,'']
Path('docs/archive/CHATGPT_RETURN_HANDOFF.md').write_text('\n'.join(h)+'\n',encoding='utf-8')
Path('reconciliation/assignment-change-inventory.json').write_text(json.dumps({'modified_from_initial':modified,'deleted_from_initial':deleted,'added':sorted(set(current)-set(base))},indent=2),encoding='utf-8')
print('Handoff written:',len(h),'lines; modified initial files:',len(modified))
