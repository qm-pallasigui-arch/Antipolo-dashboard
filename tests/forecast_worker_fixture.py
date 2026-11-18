"""Browser-only gate around the real workflow in a separate model process."""
from pathlib import Path
import sys
import time

from dashboard.monthly.forecasting.pipeline import PrototypeWorkflow
from dashboard.monthly.worker import execute

original = PrototypeWorkflow.__call__


def controlled(self, rows, dates):
    deadline = time.monotonic() + 120
    while not Path(sys.argv[1]).exists():
        if time.monotonic() > deadline:
            raise TimeoutError('Browser did not release the model gate.')
        time.sleep(0.1)
    return original(self, rows, dates)


if __name__ == '__main__':
    PrototypeWorkflow.__call__ = controlled
    execute()
