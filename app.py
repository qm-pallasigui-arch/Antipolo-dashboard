"""
Entrypoint.

Local development:
    python app.py

Production (e.g. gunicorn), skips app.run()'s dev server entirely:
    gunicorn "app:server" --bind 0.0.0.0:$PORT

Either way, importing this module in the right order is what actually wires
the app together:
  1. dashboard.app_instance creates the bare `app` object.
  2. dashboard.ui.layout.build_layout() is called and assigned to app.layout.
  3. `import dashboard.callbacks` registers every @callback against `app`
     as a side effect -- this must happen AFTER app.layout is set, so any
     callback validation that inspects the layout tree sees the real thing.
"""

import os

from dashboard.app_instance import app as dash_app, server
from dashboard.ui.layout import build_layout
from dashboard.logging_config import get_logger
from dashboard.config import DEFAULT_HOST, DEFAULT_PORT

dash_app.layout = build_layout()

import dashboard.callbacks  # noqa: E402,F401  (side effect: registers callbacks against `app`)

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
