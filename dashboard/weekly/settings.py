"""Operator-maintained model protocol; normal users never edit configuration."""
import json
import os
from pathlib import Path

from dashboard.weekly.protocol import exploratory_configuration


def model_configuration():
    path = os.environ.get('WEEKLY_MODEL_CONFIG')
    if not path:
        return exploratory_configuration()
    config = json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(config, dict):
        raise ValueError('The installed model protocol could not be loaded. Please contact the study administrator.')
    return config


def research_requirements():
    """Documented study decisions only; never supply unknown source facts."""
    path = os.environ.get('WEEKLY_RESEARCH_CONFIG')
    if not path:
        return {}
    config = json.loads(Path(path).read_text(encoding='utf-8'))
    allowed = {'approved_diseases', 'weekly_protocol'}
    if not isinstance(config, dict) or set(config) - allowed:
        raise ValueError('The installed study requirements need administrator review.')
    return config
