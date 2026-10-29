"""Reversible, workspace-contained archival after the static audit."""
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'archive' / 'forecasting'
HEADER = '# LEGACY RESEARCH CODE\n# Not part of the finalized Prophet-XGBoost thesis implementation.\n# Retained only for historical/reproducibility purposes.\n'
MOVES = {
    'icd_inference.py': 'icd_inference_legacy.py',
    'dashboard/monthly/forecasting/icd_inference.py': 'packaged_icd_inference_legacy.py',
    'dashboard/monthly/forecasting/prototype_adapter.py': 'prototype_adapter_legacy.py',
    'tests/test_prototype_forecast.py': 'tests/test_prototype_forecast.py',
    'icd_inference_a00.json': 'sample_outputs/icd_inference_a00.json',
    'icd_inference_b25.json': 'sample_outputs/icd_inference_b25.json',
    'tests/fixtures/prototype/icd_inference_a00.json': 'sample_outputs/fixture_a00.json',
    'tests/fixtures/prototype/icd_inference_b25.json': 'sample_outputs/fixture_b25.json',
}

for source, target in MOVES.items():
    src, dst = (ROOT / source).resolve(), (DEST / target).resolve()
    if not src.is_relative_to(ROOT) or not dst.is_relative_to(ROOT):
        raise RuntimeError('Archive path escaped workspace')
    if not src.exists():
        continue
    if dst.exists():
        raise RuntimeError(f'Archive collision: {dst}')
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dst))
    if dst.suffix == '.py':
        dst.write_text(HEADER + dst.read_text(encoding='utf-8'), encoding='utf-8')
    print(f'{source} -> {dst.relative_to(ROOT)}')
