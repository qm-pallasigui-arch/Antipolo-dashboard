"""
Importing this package registers every @callback against the shared app
(dashboard.app_instance.app) as a side effect of importing the submodules
below. app.py does `from dashboard import callbacks` purely for that
side effect -- nothing in this file needs to be called directly.
"""

from dashboard.callbacks import data_callbacks  # noqa: F401
from dashboard.callbacks import view_callbacks  # noqa: F401
