"""Operator-maintained model protocol; normal users never edit configuration."""
import json
import os
from pathlib import Path

from dashboard.weekly.protocol import exploratory_configuration


# The pinned per-disease protocol ships with the application. It is used whether
# or not WEEKLY_MODEL_CONFIG is set, because the fallback below resolves sixteen
# candidates per disease against this file's one. Two launch paths producing
# different models is a defect, not a configuration choice.
BUNDLED_PROTOCOL = Path(__file__).resolve().parents[2] / 'config' / 'weekly_model_per_disease.json'


def protocol_source():
    """Path of the model protocol in use, and whether it was named explicitly.

    An explicitly named protocol that does not exist is an error the operator
    should see. An absent bundled default is not, so that a partial checkout
    degrades to the built-in exploratory protocol rather than refusing to start.
    """
    explicit = os.environ.get('WEEKLY_MODEL_CONFIG')
    path = Path(explicit) if explicit else BUNDLED_PROTOCOL
    return path, bool(explicit), path.is_file()


def model_configuration():
    path, explicit, found = protocol_source()
    if not found:
        if explicit:
            raise ValueError('The installed model protocol could not be loaded. Please contact the study administrator.')
        return exploratory_configuration()
    config = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(config, dict):
        raise ValueError('The installed model protocol could not be loaded. Please contact the study administrator.')
    return config


def protocol_summary():
    """One line describing the protocol actually in use, for the startup log.

    A forecast takes minutes and a wrong protocol multiplies that, so which
    protocol is active should be visible before a long run rather than inferred
    afterwards.
    """
    path, explicit, found = protocol_source()
    if not found:
        # Must not raise: this runs at startup and the operator needs the server
        # up to read the message. model_configuration still refuses to guess.
        return (f'NAMED PROTOCOL NOT FOUND: {path}' if explicit
                else f'built-in exploratory protocol (no file at {path})')
    config = model_configuration()
    candidates = config.get('candidates')
    if isinstance(candidates, dict):
        named = {len(v) for key, v in candidates.items() if key != 'default'}
        counts = sorted(named) or [0]
        scope = (f'{counts[0]} candidate per disease' if len(counts) == 1
                 else f'{counts[0]}-{counts[-1]} candidates per disease')
        fallback = candidates.get('default')
        if fallback and len(fallback) not in counts:
            scope += f' ({len(fallback)} for any disease not listed)'
    else:
        scope = 'candidates unknown'
    return f"{path}{'' if explicit else ' (default)'} - {scope}"


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
