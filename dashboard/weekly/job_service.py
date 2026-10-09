"""Private worker API for a Vercel dashboard; deploy on a persistent Python host."""
import hmac
import os

from flask import Flask, jsonify, request

from dashboard.config import MAX_UPLOAD_BYTES
from dashboard.weekly.jobs import JobError, JobNotFound, Queue, TERMINAL, ensure_worker

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = MAX_UPLOAD_BYTES


@app.get('/healthz')
def health():
    return {'status': 'ok'}


@app.post('/jobs/<action>')
def dispatch(action):
    token = os.environ.get('WEEKLY_JOB_SERVICE_TOKEN', '')
    if not token or not hmac.compare_digest(request.headers.get('Authorization', ''), 'Bearer ' + token):
        return jsonify(error='Unauthorized worker request.'), 401
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return jsonify(error='A JSON object is required.'), 400
    try:
        queue = Queue()
        if action == 'submit':
            state = queue.submit(body['dataset'], body['disease'], body['config'])
        elif action == 'status':
            state = queue.status(body['id'])
        elif action == 'cancel':
            state = queue.cancel(body['id'])
        else:
            return jsonify(error='Unknown worker action.'), 404
        if state['status'] not in TERMINAL:
            ensure_worker(queue)
        return jsonify(state)
    except (JobError, ValueError, KeyError, TypeError) as exc:
        return jsonify(error=str(exc), code='job_not_found' if isinstance(exc, JobNotFound) else 'invalid_request'), 400
