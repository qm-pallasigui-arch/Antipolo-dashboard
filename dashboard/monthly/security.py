"""Password hashing, revocable sessions and protection of every Dash request."""
import hmac
import os
import secrets
import time
from datetime import datetime, timedelta, timezone

from flask import abort, g, redirect, render_template_string, request, session, send_file
from pathlib import Path
from werkzeug.security import check_password_hash, generate_password_hash

from .store import require_admin
from .domain import LIMITATIONS
from .repositories.batch_repository import BatchRepository
from .components import panel_header_markup, application_shell_markup
from .navigation import NAV_PAGES, NAV_LABELS, ROLE_LABELS
from urllib.parse import quote

PAGE = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{{title}} · Antipolo</title><link rel="stylesheet" href="/monthly-theme.css"><script src="/monthly-ui.js" defer></script>
<body>{% set content %}{% if g.user %}<div class="m-page-heading m-account-heading"><h1>{{title}}</h1></div>{% endif %}<div class="m-auth {{'m-account-layout' if 'Security' in title else 'm-panel'}}">
{% if not g.user %}<div class="m-page-heading"><h1>{{title}}</h1></div>{% endif %}
{% if error %}<div class="m-notice m-notice--error" role="alert">{{error}}</div>{% endif %}{{body|safe}}</div>{% endset %}
{% if g.user %}{{shell(content)}}{% else %}<div class="monthly-app m-auth-shell m-login-shell"><header class="m-app-header"><div class="m-brand">
<div class="m-brand-mark" aria-hidden="true"><span></span><span></span><span></span></div><span class="m-login-brand">Antipolo Disease Forecasting</span></div></header><main>{{content}}</main></div>{% endif %}
</body></html>'''




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
        creator = db.execute('SELECT username FROM users WHERE id=?', (actor['id'],)).fetchone()[0] if actor else 'initial setup'
        store.notify('security', 'Authorized account created', f'Account “{username.strip().lower()}” was created by {creator}.', 'Security', role='admin', db=db)
        return cursor.lastrowid


def change_user(store, actor, user_id, role, active):
    require_admin(actor)
    if role not in ('admin', 'viewer') or active not in (0, 1):
        raise ValueError('Invalid account role or active status.')
    if user_id == actor['id'] and (role != 'admin' or not active):
        raise ValueError('You cannot demote or disable your own administrator account. Ask another administrator to make this change.')
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
        store.notify('security', 'Account permissions updated', f'Account “{user["username"]}” is now {"active" if active else "inactive"} with the role {ROLE_LABELS[role]}.', 'Security', role='admin', db=db)


def reset_password(store, actor, user_id, password):
    require_admin(actor)
    if len(password) < 12:
        raise ValueError('Use a password of at least 12 characters.')
    with store.connect() as db:
        db.execute('BEGIN IMMEDIATE')
        user = db.execute('SELECT username FROM users WHERE id=?', (user_id,)).fetchone()
        if not user:
            raise ValueError('User not found.')
        db.execute('UPDATE users SET password_hash=? WHERE id=?', (generate_password_hash(password), user_id))
        db.execute('DELETE FROM sessions WHERE user_id=?', (user_id,))
        db.execute('DELETE FROM login_failures WHERE username=?', (user['username'],))
        store.audit(actor['id'], 'password_reset', user_id, db)
        store.notify('security', 'Password reset completed',
                     f'An administrator reset the password for {user["username"]}. Existing sessions were signed out.',
                     'Security', role='admin', record_id=user_id, db=db)


def current_user():
    if not getattr(g, 'user', None):
        abort(401)
    return g.user


def install_security(server, store):
    @server.context_processor
    def shell_context():
        user = getattr(g, 'user', None)
        return dict(shell=lambda content: application_shell_markup(content, user=user, dataset=store.active(), unread=store.unread_count(user), current=request.path), panel_header=panel_header_markup, roles=ROLE_LABELS, limitations=LIMITATIONS, links=[(NAV_LABELS.get(p, p), '/?module=' + quote(p)) for p in NAV_PAGES],
                    unread=store.unread_count(user) if user else 0,
                    dataset_state='Dataset active' if user and store.active() else 'No dataset loaded')

    secret = os.environ.get('MONTHLY_SECRET_KEY')
    if store.database_url and not secret:
        raise ValueError('Set MONTHLY_SECRET_KEY for PostgreSQL/cloud deployment.')
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
        if request.path in ('/login', '/password-help', '/healthz', '/monthly-theme.css', '/monthly-ui.js'):
            return None
        if not g.user:
            if request.path.startswith('/_dash') or request.method != 'GET':
                abort(401)
            return redirect('/login')
        return None

    @server.after_request
    def prevent_private_page_caching(response):
        if request.path in ('/login', '/password-help', '/logout', '/account', '/') or request.path.startswith('/_dash'):
            response.headers['Cache-Control'] = 'no-store'
        return response

    @server.get('/monthly-theme.css')
    def monthly_theme():
        return send_file(Path(__file__).resolve().parents[1] / 'assets' / 'monthly.css', mimetype='text/css')

    @server.get('/monthly-ui.js')
    def monthly_script():
        return send_file(Path(__file__).resolve().parents[1] / 'assets' / 'monthly-ui.js', mimetype='text/javascript')

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
        body = render_template_string('''<form method="post" data-busy-form><input type="hidden" name="csrf" value="{{csrf}}">
            <label for="login-username">Username or email</label><input id="login-username" name="username" value="{{username}}" required autocomplete="username" autocapitalize="none" spellcheck="false">
            <label for="login-password">Password</label><div class="m-password-field">
            <input id="login-password" name="password" type="password" required autocomplete="current-password" aria-describedby="caps-lock">
            <button type="button" class="m-password-toggle" data-password-toggle="login-password" aria-controls="login-password" aria-pressed="false">Show password</button></div>
            <p id="caps-lock" role="status" hidden>Caps Lock is on.</p>
            <button type="submit" class="m-login-submit" data-busy-label="Signing in…">Sign in</button><p data-form-status role="status"></p></form>
            <a class="m-recovery-link" href="/password-help">Forgot password?</a>''', csrf=session['csrf'], username=request.form.get('username', ''))
        return render_template_string(PAGE, title='Sign in', error=error, body=body, compact=True)

    @server.route('/password-help', methods=['GET', 'POST'])
    def password_help():
        session.setdefault('csrf', secrets.token_hex(24))
        sent = request.args.get('sent') == '1'
        if request.method == 'POST':
            username = request.form.get('username', '').strip().lower()
            cutoff = (datetime.now(timezone.utc) - timedelta(minutes=15)).isoformat()
            with store.connect() as db:
                db.execute('BEGIN IMMEDIATE')
                user = db.execute('SELECT id,username FROM users WHERE username=?', (username,)).fetchone()
                if user and not db.execute("SELECT id FROM notifications WHERE title='Password reset requested' AND related_record_id=? AND created_at>?", (str(user['id']), cutoff)).fetchone():
                    store.notify('security', 'Password reset requested',
                                 f'A signed-out visitor requested help for {user["username"]}. Verify their identity through your established contact channel before resetting the password in Security / Accounts. This request alone does not verify identity.',
                                 'Security', role='admin', record_id=user['id'], db=db)
                    store.audit(None, 'password_reset_requested', user['id'], db)
            return redirect('/password-help?sent=1', code=303)
        body = render_template_string('''{% if sent %}<p role="status">If this account exists, an administrator has been notified. Repeated requests within 15 minutes are combined.</p><p>An administrator must verify your identity before resetting your password. No password has been changed.</p>{% else %}
            <p>Send a password-reset request to the administrators in this app.</p>
            <form method="post" data-busy-form><input type="hidden" name="csrf" value="{{csrf}}">
            <label for="recovery-username">Username or email</label><input id="recovery-username" name="username" required autocomplete="username" autocapitalize="none" spellcheck="false">
            <button type="submit" class="m-login-submit" data-busy-label="Sending request…">Notify administrator</button><p data-form-status role="status"></p></form>{% endif %}
            <a class="m-recovery-link" href="/login">Return to sign in</a>''', csrf=session['csrf'], sent=sent)
        return render_template_string(PAGE, title='Password help', error='', body=body, compact=True)

    @server.route('/logout', methods=['GET', 'POST'])
    def logout():
        dataset = store.active()
        batch = BatchRepository(store).latest(dataset['dataset_signature']) if dataset else None
        running = batch and batch['status'] in ('queued', 'running', 'cancelling')
        if request.method == 'POST' and (not running or request.form.get('confirm_running') == 'yes'):
            with store.connect() as db:
                db.execute('DELETE FROM sessions WHERE token=?', (session.get('token'),))
                store.audit(g.user['id'], 'logout', db=db)
            session.clear()
            return redirect('/login')
        body = render_template_string('<dialog open class="m-signout-dialog" aria-label="Confirm sign out"><p>{% if running %}A forecast is running. Signing out does not cancel it; sign in again to check its progress.{% else %}Sign out of your account?{% endif %}</p><form method="post"><input type="hidden" name="csrf" value="{{csrf}}"><div class="m-actions"><button name="confirm_running" value="yes">Confirm sign out</button><a class="m-button m-button--secondary" href="/">Cancel sign out</a></div></form></dialog>', csrf=session['csrf'], running=running)
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
                    session['account_notice'] = 'Account created successfully.'
                elif request.form.get('action') == 'reset_password':
                    if request.form.get('identity_verified') != 'yes':
                        raise ValueError('Verify the account owner’s identity before resetting the password.')
                    reset_password(store, g.user, int(request.form['user_id']), request.form.get('password', ''))
                    return redirect('/account?reset=1')
                else:
                    change_user(store, g.user, int(request.form['user_id']), request.form.get('role'), int(request.form['active']))
                    session['account_notice'] = 'Account changes saved. Existing sessions for that account were signed out.'
                return redirect('/account')
            except (ValueError, __import__('sqlite3').IntegrityError) as exc:
                error = str(exc) if not isinstance(exc, __import__('sqlite3').IntegrityError) else 'Username already exists.'
        with store.connect() as db:
            users = db.execute('SELECT id,username,role,active FROM users ORDER BY id').fetchall()
        body = render_template_string('''<a href="/">Return to dashboard</a><p>Administrators upload and activate datasets, generate forecasts and manage accounts. Viewers inspect results and export reports.</p>{% if reset %}<p role="status">Password reset completed. Share the new password securely with the verified account owner.</p>{% endif %}{% if notice %}<p class="m-notice m-notice--success" role="status">{{notice}}</p>{% endif %}<div class="m-layout-grid m-security-grid"><section class="m-panel m-span-4" id="m-create-account">{{panel_header("Create authorized user")}}<form method="post">
            <input type="hidden" name="csrf" value="{{csrf}}"><input type="hidden" name="action" value="create">
            <label>Username/email <input name="username" required minlength="3"></label>
            <label for="create-password">Initial password</label><div class="m-password-field"><input id="create-password" name="password" type="password" required minlength="12" autocomplete="new-password" aria-describedby="password-help">
            <button type="button" class="m-password-toggle" data-password-toggle="create-password" aria-controls="create-password" aria-pressed="false">Show password</button></div><p id="password-help">Use at least 12 characters.</p>
            <label>Role <select name="role"><option value="viewer">Authorized Viewer / Health User</option><option value="admin">Administrator / Researcher</option></select></label><button class="m-button m-button--primary">Create account</button></form></section>
            <section class="m-panel m-span-8" id="m-manage-accounts">{{panel_header("Manage accounts")}}{% for u in users %}<article class="m-account-record"><form method="post" class="m-user-row" data-dirty-form onsubmit="return confirm('Save these account changes? Existing sessions for this account will be signed out.')"><strong>{{u.username}}{% if u.id == g.user.id %} (your account){% endif %}</strong>
            <input type="hidden" name="csrf" value="{{csrf}}"><input type="hidden" name="user_id" value="{{u.id}}">
            <label>Role<select name="role" {% if u.id == g.user.id %}disabled{% endif %}>{% for role in ['admin','viewer'] %}<option value="{{role}}" {{'selected' if role==u.role else ''}}>{{roles[role]}}</option>{% endfor %}</select></label>
            <label>Account status<select name="active" {% if u.id == g.user.id %}disabled{% endif %}><option value="1" {{'selected' if u.active else ''}}>Active</option><option value="0" {{'selected' if not u.active else ''}}>Inactive</option></select></label><button class="m-button m-button--secondary" disabled>Save account</button></form>{% if u.id == g.user.id %}<p class="m-muted">You cannot demote or disable your own administrator account. Ask another administrator to make this change.</p>{% endif %}
            <details class="m-disclosure"><summary>Reset password for {{u.username}}</summary><div class="m-disclosure-body"><form method="post" onsubmit="return confirm('Reset this password and sign out all existing sessions for this account?')">
            <input type="hidden" name="csrf" value="{{csrf}}"><input type="hidden" name="action" value="reset_password"><input type="hidden" name="user_id" value="{{u.id}}">
            <p>Verify identity using your established contact channel. A notification alone does not prove account ownership. Share the new password securely.</p>
            <label>Identity verification<select name="identity_verified" required><option value="">Choose after verification</option><option value="yes">I verified the account owner’s identity</option></select></label>
            <label for="reset-password-{{u.id}}">New password</label><div class="m-password-field"><input id="reset-password-{{u.id}}" name="password" type="password" required minlength="12" autocomplete="new-password">
            <button type="button" class="m-password-toggle" data-password-toggle="reset-password-{{u.id}}" aria-controls="reset-password-{{u.id}}" aria-pressed="false">Show password</button></div><button class="m-button m-button--secondary">Reset password</button></form></div></details></article>{% endfor %}</section></div>''', users=users, csrf=session['csrf'], reset=request.args.get('reset') == '1', notice=session.pop('account_notice', ''))
        return render_template_string(PAGE, title='Security · User management', body=body, error=error)
