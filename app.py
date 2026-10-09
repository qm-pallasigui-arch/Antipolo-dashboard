"""
Entrypoint.

Local development:
    python app.py

Production (e.g. gunicorn), skips app.run()'s dev server entirely:
    gunicorn "app:server" --bind 0.0.0.0:$PORT

dashboard.weekly.ui registers the operational weekly callbacks against the
shared app; its layout is then assigned below. Historical monthly modules are
preserved for audit/regression use and are not imported by this entrypoint.
"""

import os

from dashboard.app_instance import app as dash_app, server
from dashboard.weekly.ui import build_layout
from dashboard.logging_config import configure_logging, get_logger
from dashboard.config import DEFAULT_HOST, DEFAULT_PORT

# Attach stdout logging before any module logs, so operator-side events
# (forecast fits, candidate diagnostics, upload rejections) reach the
# platform log stream. Set LOG_LEVEL=DEBUG for per-candidate detail.
configure_logging()

dash_app.layout = build_layout()

# Weekly callbacks are registered by dashboard.weekly.ui. Legacy monthly callbacks
# remain available for historical regression tests, but are not operational routes.

logger = get_logger(__name__)

# Vercel's Python runtime auto-discovers ``app:app`` and expects that object
# to be a WSGI or ASGI callable.  A Dash instance is the application wrapper;
# its underlying Flask server is the actual WSGI application.
app = server


@server.get("/healthz")
def healthz():
    return {"status": "ok"}, 200


if __name__ == "__main__":
    host = os.environ.get("HOST", DEFAULT_HOST)
    port = int(os.environ.get("PORT", DEFAULT_PORT))
    debug = os.environ.get("DASH_DEBUG", "true").lower() in ("1", "true", "yes")

    logger.info("starting dashboard on http://%s:%s (debug=%s)", host, port, debug)
    dash_app.run(host=host, port=port, debug=debug)
