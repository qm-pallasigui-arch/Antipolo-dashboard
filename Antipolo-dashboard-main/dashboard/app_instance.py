"""
Creates the single shared Dash `app` object.

Why this file exists at all: layout.py needs to attach `app.layout`, and the
callbacks/ modules need to register `@app.callback` (or `@callback`, which
targets whichever app is active) against that same app. If layout.py or
callbacks/ imported `app` from a top-level app.py that *also* imports layout
and callbacks to wire them up, that's a circular import. Pulling the bare
`Dash(...)` construction into its own tiny module breaks the cycle: everyone
else imports one-directionally FROM here, and only app.py (the entrypoint)
imports layout/callbacks to assemble things, after this module already exists.
"""

from dash import Dash
from werkzeug.exceptions import RequestEntityTooLarge

from dashboard.config import MAX_UPLOAD_BYTES

app = Dash(__name__, title="Antipolo Disease Surveillance \u00b7 Hybrid Forecast Prototype")
app.server.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_BYTES


@app.server.errorhandler(RequestEntityTooLarge)
def handle_oversized_request(_error):
	return {"error": "The uploaded file is too large. Please upload a smaller file."}, 413

# Exposes the underlying Flask server for WSGI deployment, e.g.:
#   gunicorn "dashboard.app_instance:server"
server = app.server
