import pytest


@pytest.fixture(autouse=True)
def isolated_weekly_registry(tmp_path, monkeypatch):
    """Tests must never read or replace an operator's selected configurations."""
    monkeypatch.setenv('WEEKLY_MODEL_STORE', str(tmp_path / 'models.sqlite3'))
