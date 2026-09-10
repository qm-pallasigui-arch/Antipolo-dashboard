# Minimal container for the dashboard. Runs via gunicorn (production WSGI
# server), not the Dash/Flask dev server -- app.run()'s debug reloader and
# single-threaded dev server are not meant for anything but local development.

FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=8050
EXPOSE 8050

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
	CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:%s/healthz' % os.environ.get('PORT', '8050'))"

# `app:server` = the Flask WSGI app exposed in app.py (dashboard.app_instance.server).
# One worker is intentional for the Render free tier: model fitting is CPU-bound
# and browser session state does not require server-side worker affinity.
CMD ["sh", "-c", "gunicorn app:server --bind 0.0.0.0:${PORT} --workers 1 --timeout 600"]
