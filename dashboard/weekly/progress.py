"""Optional worker progress hook; direct offline model calls remain unchanged."""
from contextlib import contextmanager
from contextvars import ContextVar

_reporter = ContextVar('weekly_progress', default=None)


def report(stage, completed=0, total=None, detail=''):
    callback = _reporter.get()
    if callback:
        callback({'stage': stage, 'completed': completed, 'total': total, 'detail': detail})


@contextmanager
def reporting(callback):
    token = _reporter.set(callback)
    try:
        yield
    finally:
        _reporter.reset(token)
