"""Verify deployment still starts after retiring the disease-specific application."""
import os
from pathlib import Path
import subprocess
import sys


def test_entrypoint_is_monthly_only(tmp_path):
    environment = {**os.environ, 'MONTHLY_DB': str(tmp_path / 'startup.sqlite3')}
    result = subprocess.run([sys.executable, '-c', '''
import sys
import app
assert app.app is app.server and callable(app.app)
client = app.server.test_client()
assert client.get('/healthz').get_json() == {'status': 'ok'}
assert client.get('/').status_code == 302
assert client.get('/login').status_code == 200
assert client.get('/monthly-theme.css').status_code == 200
assert app.dash_app.callback_map
assert not any(name.startswith(('dashboard.weekly', 'dashboard.modeling',
    'dashboard.callbacks', 'dashboard.data', 'dashboard.ui', 'dashboard.charts')) for name in sys.modules)
print('Monthly entrypoint and health check passed')
'''], env=environment, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr


def test_only_monthly_browser_assets_are_shipped():
    assets = Path('dashboard/assets')
    assert {p.name for p in assets.iterdir() if p.is_file()} == {'monthly.css'}
