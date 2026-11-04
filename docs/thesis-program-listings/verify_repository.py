"""Reproduce the local test and canonical execution evidence, without active state.

Run from repository root. In restricted Windows environments the process may
need permission to create/read its temporary directories outside the sandbox.
This runner deliberately does not enable the opt-in live Supabase test.
"""
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = Path(__file__).resolve().parent / 'evidence'
OUTPUT.mkdir(parents=True, exist_ok=True)
environment = dict(os.environ, PYTHONIOENCODING='utf-8', PROTOTYPE_MODE='true')
environment.pop('TEST_SUPABASE_DATABASE_URL', None)
environment.pop('PROTOTYPE_CONFIG_PATH', None)
commands = [
    ('pytest-verified.txt', [sys.executable, '-m', 'pytest', '-v', '-ra', '--color=no', '-p', 'no:cacheprovider']),
    ('canonical-verified.txt', [sys.executable, 'tools/verify_prototype.py', '--canonical',
        'Antipolo_ICD10_Canonical_Monthly_2016_2025.csv', '--output', str(OUTPUT / 'canonical-verification.json')]),
    ('synthetic-verified.txt', [sys.executable, 'tools/verify_prototype.py', '--output', str(OUTPUT / 'synthetic-verification.json')]),
    ('browser-verified.txt', [sys.executable, 'tests/browser_monthly.py']),
]
for filename, command in commands:
    result = subprocess.run(command, cwd=ROOT, env=environment, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (OUTPUT / filename).write_bytes(result.stdout)
    print(filename, 'exit_code=', result.returncode)
    if result.returncode:
        raise SystemExit(result.returncode)
subprocess.run([sys.executable, str(Path(__file__).with_name('build_listings.py'))], cwd=ROOT, env=environment, check=True)
subprocess.run([sys.executable, str(Path(__file__).with_name('validate_listings.py'))], cwd=ROOT, env=environment, check=True)
