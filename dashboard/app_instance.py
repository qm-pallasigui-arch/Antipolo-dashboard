"""Shared Dash/Flask instance; the entrypoint installs monthly views and callbacks."""

from dash import Dash
from werkzeug.exceptions import RequestEntityTooLarge

from dashboard.config import MAX_UPLOAD_BYTES

app = Dash(__name__, title="Antipolo Monthly ICD-10 Consultations", update_title=None)
app.server.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_BYTES


@app.server.errorhandler(RequestEntityTooLarge)
def handle_oversized_request(_error):
	return {"error": "The uploaded file is too large. Please upload a smaller file."}, 413

# Exposes the underlying Flask server for WSGI deployment, e.g.:
#   gunicorn "dashboard.app_instance:server"
server = app.server
