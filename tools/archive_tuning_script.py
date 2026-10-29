"""Preserve the supplied development script after real-service verification."""
import hashlib
import json
from pathlib import Path
import shutil

root = Path(__file__).resolve().parents[1]
source = (root / 'icd10_prophet_xgboost_tuning.py').resolve()
target = (root / 'archive/model_development/icd10_prophet_xgboost_tuning.py').resolve()
if not source.is_relative_to(root) or not target.is_relative_to(root):
    raise RuntimeError('Archive paths must remain inside the workspace.')
if target.exists():
    raise RuntimeError('Archive destination already exists; no overwrite allowed.')
digest = hashlib.sha256(source.read_bytes()).hexdigest()
target.parent.mkdir(parents=True, exist_ok=True)
shutil.move(str(source), str(target))
assert hashlib.sha256(target.read_bytes()).hexdigest() == digest
(target.parent / 'provenance.json').write_text(json.dumps({
    'original_name': source.name, 'sha256': digest,
    'classification': 'ARCHIVED MODEL DEVELOPMENT',
    'reason': 'Replaced by the modular real-date prototype; never imported by the application.'}, indent=2), encoding='utf-8')
print('Development script archived with unchanged content and a recorded SHA-256.')
