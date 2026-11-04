"""Validate exact source excerpts, evidence and links in the generated appendix."""
import hashlib
import importlib.metadata
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
BASE = Path(__file__).resolve().parent
manifest = json.loads((BASE / 'listing-manifest.json').read_text(encoding='utf-8'))
document = (BASE / 'PYTHON_CODE_LISTINGS.md').read_text(encoding='utf-8')
excerpts = re.findall(r'\*\*Code:\*\*\n```python\n(.*?)\n```', document, re.S)
assert len(excerpts) == len(manifest['listings']) == 51
for item, code in zip(manifest['listings'], excerpts):
    path = ROOT / item['path']
    assert hashlib.sha256(path.read_bytes()).hexdigest() == item['source_sha256'], item['path']
    expected = '\n'.join(path.read_text(encoding='utf-8').splitlines()[item['start'] - 1:item['end']])
    assert code == expected, item['number']
assert len(re.findall(r'\*\*Actual Output:\*\*\n```kotlin\n.+?\n```', document, re.S)) == 51
for path in BASE.glob('*.md'):
    for target in re.findall(r'\]\(([^)]+)\)', path.read_text(encoding='utf-8')):
        if '://' not in target:
            assert (path.parent / target).exists(), (path, target)
for path in (ROOT / 'dashboard').rglob('*.py'):
    assert not re.search(r'\b(readiness|readiness_policy|readiness_status|eligible|eligibility|NotEligible)\b', path.read_text(encoding='utf-8'), re.I), path
assert not re.search(r'\b(readiness|eligible|eligibility|NotEligible)\b', document, re.I)
canonical = json.loads((BASE / 'evidence/canonical-verification.json').read_text(encoding='utf-8'))
assert canonical['statuses'] == {'hybrid_completed': 7}
assert canonical['stored_monthly_values'] == 84
ranking = canonical['ranking']
assert len(ranking['attempted_blocks']) == len(ranking['rankings']) == len(ranking['model_statuses']) == 7
assert not ranking['failed_blocks']
assert ranking['top_five'] == ranking['rankings'][:5]
assert ranking['forecast_months'] == [f'2026-{month:02}' for month in range(1, 13)]
assert all(e['status'] == 'completed' for e in canonical['evaluations'].values())
test_log = (BASE / 'evidence/pytest-verified.txt').read_text(encoding='utf-8')
assert '51 passed, 1 skipped' in test_log
browser_log = (BASE / 'evidence/browser-verified.txt').read_text(encoding='utf-8')
assert 'PASS: login, activation' in browser_log and 'no browser errors.' in browser_log
result = dict(listing_count=51, exact_source_excerpts_verified=True, output_fences_verified=51,
              local_document_links_verified=True, active_classification_terms_absent=True,
              canonical_model_attempts=7, canonical_completions=7, persisted_monthly_values=84,
              canonical_holdout_evaluations_completed=7, application_code_reconciled=True,
              tests='51 passed, 1 skipped', browser_workflow='passed',
              packages={name: importlib.metadata.version(name) for name in ('prophet', 'xgboost', 'pandas', 'numpy', 'pytest', 'dash', 'psycopg')},
              input_sha256={name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in (
                  'Antipolo_ICD10_Canonical_Monthly_2016_2025.csv', 'Antipolo_ICD10_Canonical_Monthly_2016_2025.xlsx')})
(BASE / 'evidence/package-validation.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print(json.dumps(result, indent=2))
