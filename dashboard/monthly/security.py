"""Password hashing, revocable sessions and protection of every Dash request."""
import hmac
import os
import secrets
import time
from datetime import timedelta

from flask import abort, g, redirect, render_template_string, request, session, send_file
from pathlib import Path
from werkzeug.security import check_password_hash, generate_password_hash

from .store import require_admin

PAGE = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{{title}} · Antipolo</title><link rel="stylesheet" href="/monthly-theme.css">
<body><div class="monthly-app m-auth-shell"><header class="m-app-header"><div class="m-brand">
<div class="m-brand-mark" aria-hidden="true"><span></span><span></span><span></span></div>
<div><h1>Antipolo Disease Forecasting</h1><p>Monthly ICD-10 consultations · Ages 5–19</p></div></div></header>
<main class="m-auth m-panel {{'m-auth--wide' if 'Security' in title else ''}}"><div class="m-page-heading"><h2>{{title}}</h2><p>Antipolo City, Rizal</p></div>
{% if error %}<div class="m-notice m-notice--error" role="alert">{{error}}</div>{% endif %}{{body|safe}}</main>
<footer class="m-app-footer">Authorized access · Monthly consultation reporting and research</footer></div></body></html>'''



def create_user(store, username, password, role='viewer', actor=None, bootstrap=False):
    if role not in ('admin', 'viewer') or not username or len(username.strip()) < 3 or len(password) < 12:
        raise ValueError('Use a username of at least 3 characters, a password of at least 12 characters, and an admin/viewer role.')
    with store.connect() as db:
        db.execute('BEGIN IMMEDIATE')
        if bootstrap:
            if db.execute('SELECT COUNT(*) FROM users').fetchone()[0]:
                raise ValueError('Bootstrap is only available before the first account is created.')
            role = 'admin'
        else:
            require_admin(actor)
        cursor = db.execute('INSERT INTO users(username,password_hash,role) VALUES (?,?,?)',
                            (username.strip().lower(), generate_password_hash(password), role))
        store.audit(actor['id'] if actor else cursor.lastrowid, 'user_created', cursor.lastrowid, db)
        store.notify('security', 'Authorized account created', username.strip().lower(), 'Security', role='admin', db=db)
        return cursor.lastrowid


def change_user(store, actor, user_id, role, active):
    require_admin(actor)
    if role not in ('admin', 'viewer') or active not in (0, 1):
        raise ValueError('Invalid account role or active status.')
    with store.connect() as db:
        db.execute('BEGIN IMMEDIATE')
        user = db.execute('SELECT * FROM users WHERE id=?', (user_id,)).fetchone()
        if not user:
            raise ValueError('User not found.')
        if user['role'] == 'admin' and user['active'] and (role != 'admin' or not active):
            if db.execute("SELECT COUNT(*) FROM users WHERE role='admin' AND active=1").fetchone()[0] <= 1:
                raise ValueError('Keep at least one active administrator.')
        db.execute('UPDATE users SET role=?,active=? WHERE id=?', (role, active, user_id))
        db.execute('DELETE FROM sessions WHERE user_id=?', (user_id,))
        store.audit(actor['id'], 'user_updated', user_id, db)
        store.notify('security', 'Account permissions updated', f'Account {user_id}', 'Security', role='admin', db=db)


def current_user():
    if not getattr(g, 'user', None):
        abort(401)
    return g.user


def install_security(server, store):
    secret = os.environ.get('MONTHLY_SECRET_KEY')
    if not secret:
        secret_file = store.path.parent / 'session.key'
        try:
            with secret_file.open('x', encoding='utf-8') as handle:
                handle.write(secrets.token_hex(32))
        except FileExistsError:
            pass
        secret = secret_file.read_text(encoding='utf-8').strip()
    server.config.update(SECRET_KEY=secret, SESSION_COOKIE_NAME='antipolo_monthly_session',
                         SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Strict',
                         SESSION_COOKIE_SECURE=os.environ.get('MONTHLY_COOKIE_SECURE') == '1',
                         PERMANENT_SESSION_LIFETIME=timedelta(hours=8))

    @server.before_request
    def protect():
        limit = server.config.get('MAX_CONTENT_LENGTH')
        if limit and request.content_length and request.content_length > limit:
            abort(413)
        g.user = None
        token = session.get('token')
        if token:
            with store.connect() as db:
                row = db.execute('''SELECT u.* FROM users u JOIN sessions s ON u.id=s.user_id
                    WHERE s.token=? AND s.expires>? AND u.active=1''', (token, time.time())).fetchone()
                if row:
                    g.user = dict(row)
        if request.method == 'POST':
            # Forms use CSRF tokens. Dash JSON uses browser same-origin enforcement
            # plus an exact Origin check; cross-site requests are never accepted.
            origin = request.headers.get('Origin')
            if origin and origin != request.host_url.rstrip('/'):
                abort(403)
            if request.path == '/_dash-update-component':
                if not request.is_json or request.headers.get('Sec-Fetch-Site') == 'cross-site':
                    abort(403)
            else:
                expected, supplied = session.get('csrf', ''), request.form.get('csrf', '')
                if not expected or not hmac.compare_digest(expected, supplied):
                    if request.path == '/login':
                        # An old tab, restarted server or replaced cookie can invalidate
                        # the form. Never authenticate that POST; issue a fresh GET.
                        session['csrf'] = secrets.token_hex(24)
                        return redirect('/login?expired=1', code=303)
                    abort(403)
        if request.path in ('/login', '/healthz', '/monthly-theme.css'):
            return None
        if not g.user:
            if request.path.startswith('/_dash') or request.method != 'GET':
                abort(401)
            return redirect('/login')
        return None

    @server.after_request
    def prevent_private_page_caching(response):
        if request.path in ('/login', '/logout', '/account', '/') or request.path.startswith('/_dash'):
            response.headers['Cache-Control'] = 'no-store'
        return response

    @server.get('/monthly-theme.css')
    def monthly_theme():
        return send_file(Path(__file__).resolve().parents[1] / 'assets' / 'monthly.css', mimetype='text/css')

    @server.route('/login', methods=['GET', 'POST'])
    def login():
        session.setdefault('csrf', secrets.token_hex(24))
        error = ('Your sign-in form expired or cookies changed. Please enter your credentials again. '
                 'Allow cookies for this site if this keeps happening.' if request.args.get('expired') == '1' else '')
        if request.method == 'POST':
            username = request.form.get('username', '').strip().lower()
            password = request.form.get('password', '')
            with store.connect() as db:
                db.execute('DELETE FROM login_failures WHERE created<?', (time.time() - 900,))
                failures = db.execute('SELECT COUNT(*) FROM login_failures WHERE username=?', (username,)).fetchone()[0]
                row = db.execute('SELECT * FROM users WHERE username=?', (username,)).fetchone()
                valid = failures < 10 and row and check_password_hash(row['password_hash'], password) and row['active']
                if valid:
                    old_token = session.get('token')
                    if old_token:
                        db.execute('DELETE FROM sessions WHERE token=?', (old_token,))
                    session.clear()
                    session.permanent = True
                    session['token'] = secrets.token_hex(32)
                    session['csrf'] = secrets.token_hex(24)
                    db.execute('INSERT INTO sessions VALUES (?,?,?)', (session['token'], row['id'], time.time() + 28800))
                    db.execute('DELETE FROM login_failures WHERE username=?', (username,))
                    store.audit(row['id'], 'login', db=db)
                    return redirect('/')
                db.execute('INSERT INTO login_failures VALUES (?,?)', (username, time.time()))
                store.audit(None, 'login_failed', db=db)
                error = 'Login failed. Check credentials and account status; after repeated failures wait 15 minutes.'
        body = render_template_string('''<form method="post"><input type="hidden" name="csrf" value="{{csrf}}">
            <label>Username or email <input name="username" required autocomplete="username"></label>
            <label>Password <input name="password" type="password" required autocomplete="current-password"></label>
            <button>Sign in</button></form><p>First setup: an operator must create the initial administrator using the documented setup command.</p>''', csrf=session['csrf'])
        return render_template_string(PAGE, title='Sign in', error=error, body=body)

    @server.route('/logout', methods=['GET', 'POST'])
    def logout():
        if request.method == 'POST':
            with store.connect() as db:
                db.execute('DELETE FROM sessions WHERE token=?', (session.get('token'),))
                store.audit(g.user['id'], 'logout', db=db)
            session.clear()
            return redirect('/login')
        body = render_template_string('<form method="post"><input type="hidden" name="csrf" value="{{csrf}}"><button>Confirm sign out</button></form><a href="/">Return to dashboard</a>', csrf=session['csrf'])
        return render_template_string(PAGE, title='Sign out', body=body, error='')

    @server.route('/account', methods=['GET', 'POST'])
    def account():
        if g.user['role'] != 'admin':
            abort(403)
        error = ''
        if request.method == 'POST':
            try:
                if request.form.get('action') == 'create':
                    create_user(store, request.form.get('username'), request.form.get('password', ''), request.form.get('role'), g.user)
                else:
                    change_user(store, g.user, int(request.form['user_id']), request.form.get('role'), int(request.form['active']))
                return redirect('/account')
            except (ValueError, __import__('sqlite3').IntegrityError) as exc:
                error = str(exc) if not isinstance(exc, __import__('sqlite3').IntegrityError) else 'Username already exists.'
        with store.connect() as db:
            users = db.execute('SELECT id,username,role,active FROM users ORDER BY id').fetchall()
        body = render_template_string('''<a href="/">Return to dashboard</a><h2>Create authorized user</h2><form method="post">
            <input type="hidden" name="csrf" value="{{csrf}}"><input type="hidden" name="action" value="create">
            <label>Username/email <input name="username" required minlength="3"></label>
            <label>Initial password <input name="password" type="password" required minlength="12" autocomplete="new-password"></label>
            <label>Role <select name="role"><option value="viewer">Authorized Viewer / Health User</option><option value="admin">Administrator / Researcher</option></select></label><button>Create account</button></form>
            <h2>Manage accounts</h2>{% for u in users %}<form method="post" class="m-user-row" onsubmit="return confirm('Save these account changes? Existing sessions for this account will be signed out.')"><strong>{{u.username}}</strong>
            <input type="hidden" name="csrf" value="{{csrf}}"><input type="hidden" name="user_id" value="{{u.id}}">
            <label>Role<select name="role">{% for role in ['admin','viewer'] %}<option {{'selected' if role==u.role else ''}}>{{role}}</option>{% endfor %}</select></label>
            <label>Account status<select name="active"><option value="1" {{'selected' if u.active else ''}}>Active</option><option value="0" {{'selected' if not u.active else ''}}>Inactive</option></select></label><button>Save account</button></form>{% endfor %}''', users=users, csrf=session['csrf'])
        return render_template_string(PAGE, title='Security · User management', body=body, error=error)
