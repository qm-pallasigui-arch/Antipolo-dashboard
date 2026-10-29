"""Read-only legacy-term inventory; excludes dependencies and binary files."""
import csv
import argparse
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TERMS = re.compile(r'SARIMA|ARIMA|NNAR|TBATS|Holt.Winters|PIDSR|Dengue|Leptospirosis|Measles|weekly|morbidity week|week.?53|52.week|4.week|13.week|26.week|32\.22|Random\s?Forest|LightGBM|SVM|LSTM|icd_forecast|icd_inference|\bcases\b|icd10_code|historical reference MAPE|seasonal naive|confirmed.only|outbreak alert|school.specific', re.I)
SKIP = {'.git', '.venv', '.browser-tools', '__pycache__', '.pytest_cache', 'node_modules'}
TEXT = {'.py', '.md', '.txt', '.json', '.toml', '.yaml', '.yml', '.css', '.js', '.html', '.csv', '.bat', '.ini'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output-name', default='reconciliation-20261029')
    args = parser.parse_args()
    if not re.fullmatch(r'[a-z0-9-]+', args.output_name):
        raise ValueError('Output name must be a simple directory name.')
    output = ROOT / 'docs' / args.output_name
    output.mkdir(parents=True, exist_ok=True)
    errors, findings = [], []
    for base, dirs, names in os.walk(ROOT, onerror=lambda e: errors.append(str(e))):
        dirs[:] = [d for d in dirs if d not in SKIP and not d.endswith('.egg-info')]
        for name in names:
            path = Path(base) / name
            rel = path.relative_to(ROOT).as_posix()
            if path.suffix.lower() not in TEXT or rel.startswith(('docs/reconciliation-20261029/', 'docs/final-handoff-audit/')):
                continue
            try:
                lines = path.read_text(encoding='utf-8-sig').splitlines()
            except (OSError, UnicodeError) as exc:
                errors.append(f'{rel}: {type(exc).__name__}')
                continue
            for number, line in enumerate(lines, 1):
                matches = sorted(set(m.group() for m in TERMS.finditer(line)))
                if not matches:
                    continue
                historical = rel.startswith(('archive/', 'evidence/', 'reconciliation/', 'docs/historical-', 'docs/legacy-')) or rel == 'CHANGELOG.md'
                active = rel.startswith(('dashboard/', 'tests/')) or rel in ('README.md', 'ARCHITECTURE.md', 'THESIS_READINESS.md', 'pyproject.toml', 'requirements.txt')
                action = 'KEEP' if historical else 'REWRITE' if active else 'REVIEW'
                replacement = 'Superseded provenance; excluded from runtime' if historical else 'Monthly seven-block Prophet + XGBoost design; inspect context'
                if 'icd_inference' in rel or rel.endswith('prototype_adapter.py'):
                    action, replacement = 'ARCHIVE', 'Final hybrid service; retain original artifact'
                if active and (rel.startswith('tests/') or 'weekly_seasonality' in line or 'confirmed cases' in line):
                    action, replacement = 'KEEP', 'Negative guard, disabled Prophet seasonality or source-semantics caveat; not an active legacy model'
                if historical:
                    action = 'KEEP'
                findings.append([rel, number, ', '.join(matches), replacement, action, 'Low' if historical else 'Review', line.strip()[:500]])
    with (output / 'static-audit.csv').open('w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['File', 'Line / Symbol', 'Legacy assumption', 'Current-study replacement', 'Action', 'Risk', 'Context'])
        writer.writerows(findings)
    (output / 'scan-limitations.txt').write_text('\n'.join(errors) or 'No read errors.', encoding='utf-8')
    print(f'{len(findings)} matching lines inventoried; {len(errors)} read limitations. No files deleted.')


if __name__ == '__main__':
    main()
