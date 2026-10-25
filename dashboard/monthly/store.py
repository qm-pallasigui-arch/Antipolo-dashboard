"""Transactional monthly state; never shares tables or caches with legacy data."""
import json
import os
import secrets
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from .domain import DataError, now, parse_upload


class Store:
    def __init__(self, path=None):
        self.path = Path(path or os.environ.get('MONTHLY_DB', '.monthly/state.sqlite3'))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL, role TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1);
                CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY, user_id INTEGER NOT NULL, expires REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS login_failures(username TEXT, created REAL);
                CREATE TABLE IF NOT EXISTS datasets(id TEXT PRIMARY KEY, signature TEXT NOT NULL, payload TEXT NOT NULL,
                    state TEXT NOT NULL, uploader INTEGER NOT NULL, uploaded_at TEXT NOT NULL, activated_at TEXT, raw BLOB);
                CREATE UNIQUE INDEX IF NOT EXISTS one_active ON datasets(state) WHERE state='active';
                CREATE TABLE IF NOT EXISTS notifications(id INTEGER PRIMARY KEY, type TEXT, title TEXT, message TEXT,
                    severity TEXT, created_at TEXT, role_target TEXT, user_id INTEGER, related_module TEXT, related_record_id TEXT);
                CREATE TABLE IF NOT EXISTS notification_reads(notification_id INTEGER, user_id INTEGER, read_at TEXT,
                    PRIMARY KEY(notification_id,user_id));
                CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY, user_id INTEGER, action TEXT, record_id TEXT, created_at TEXT);
                CREATE TABLE IF NOT EXISTS notes(id INTEGER PRIMARY KEY, signature TEXT, user_id INTEGER, note TEXT, created_at TEXT);
                CREATE TABLE IF NOT EXISTS forecasts(id TEXT PRIMARY KEY, signature TEXT, block TEXT, status TEXT, payload TEXT, created_at TEXT);
                CREATE TABLE IF NOT EXISTS reports(id TEXT PRIMARY KEY, signature TEXT, block TEXT, user_id INTEGER, payload TEXT, created_at TEXT);
            ''')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=30)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def audit(self, user_id, action, record_id='', db=None):
        if db is None:
            with self.connect() as connection:
                return self.audit(user_id, action, record_id, connection)
        db.execute('INSERT INTO audit(user_id,action,record_id,created_at) VALUES (?,?,?,?)', (user_id, action, str(record_id), now()))

    def notify(self, kind, title, message, module, *, role=None, user_id=None, record_id='', severity='info', db=None):
        if db is None:
            with self.connect() as connection:
                return self.notify(kind, title, message, module, role=role, user_id=user_id, record_id=record_id, severity=severity, db=connection)
        db.execute('''INSERT INTO notifications(type,title,message,severity,created_at,role_target,user_id,related_module,related_record_id)
                      VALUES (?,?,?,?,?,?,?,?,?)''', (kind, title, message, severity, now(), role, user_id, module, str(record_id)))

    def notifications(self, user):
        with self.connect() as db:
            return [dict(r) for r in db.execute('''SELECT n.*, r.read_at FROM notifications n LEFT JOIN notification_reads r
                ON n.id=r.notification_id AND r.user_id=? WHERE (n.role_target IS NULL OR n.role_target=?)
                AND (n.user_id IS NULL OR n.user_id=?) ORDER BY n.id DESC''', (user['id'], user['role'], user['id']))]

    def mark_read(self, user):
        visible = self.notifications(user)
        with self.connect() as db:
            db.executemany('INSERT OR IGNORE INTO notification_reads VALUES (?,?,?)', [(r['id'], user['id'], now()) for r in visible])

    def active(self):
        with self.connect() as db:
            row = db.execute("SELECT payload FROM datasets WHERE state='active'").fetchone()
            return json.loads(row[0]) if row else None

    def candidate(self, candidate_id):
        with self.connect() as db:
            row = db.execute("SELECT payload FROM datasets WHERE id=? AND state='pending'", (candidate_id,)).fetchone()
            return json.loads(row[0]) if row else None

    def pending(self):
        with self.connect() as db:
            return [dict(r) for r in db.execute("SELECT id,uploaded_at FROM datasets WHERE state='pending' ORDER BY uploaded_at DESC")]

    def stage(self, user, raw, filename):
        require_admin(user)
        try:
            dataset = parse_upload(raw, Path(filename).name)
        except DataError as exc:
            self.notify('data_quality', 'Dataset validation failed', str(exc), 'Data & Quality', role='admin', severity='error')
            self.audit(user['id'], 'dataset_validation_failed')
            raise
        candidate_id = secrets.token_hex(16)
        dataset['candidate_id'] = candidate_id
        dataset['uploader'] = user['username']
        with self.connect() as db:
            db.execute('INSERT INTO datasets VALUES (?,?,?,?,?,?,?,?)', (candidate_id, dataset['dataset_signature'],
                json.dumps(dataset), 'pending', user['id'], now(), None, raw))
            self.audit(user['id'], 'dataset_upload', candidate_id, db)
        return dataset

    def discard(self, user, candidate_id, state='cancelled'):
        require_admin(user)
        if state not in ('cancelled', 'rejected'):
            raise DataError('Invalid candidate decision.')
        with self.connect() as db:
            db.execute("UPDATE datasets SET state=? WHERE id=? AND state='pending'", (state, candidate_id))
            self.audit(user['id'], 'dataset_' + state, candidate_id, db)

    def activate(self, user, candidate_id):
        require_admin(user)
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute("SELECT payload FROM datasets WHERE id=? AND state='pending'", (candidate_id,)).fetchone()
            if not row:
                raise DataError('Pending candidate not found. Review the candidate before activation.')
            dataset = json.loads(row[0])
            dataset['activated_at'] = now()
            db.execute("UPDATE datasets SET state='retired' WHERE state='active'")
            db.execute("UPDATE datasets SET state='active',activated_at=?,payload=? WHERE id=?", (now(), json.dumps(dataset), candidate_id))
            self.audit(user['id'], 'dataset_activation', candidate_id, db)
            self.notify('dataset', 'Dataset activated', dataset['source_file'], 'Data & Quality', record_id=dataset['dataset_signature'], db=db)
            self.notify('data_quality', 'Reporting coverage warnings', '\n'.join(dataset['warnings']), 'Data & Quality', db=db)
            for block in dataset['blocks']:
                self.notify('eligibility', block['icd10_block'] + (' — Forecast eligible' if block['eligible'] else ' — Not eligible for forecasting'),
                            block['reason'], 'Disease Trends', record_id=block['icd10_block'], db=db)
        return dataset

    def add_note(self, user, text):
        require_admin(user)
        dataset = self.active()
        if not dataset or not text or not text.strip():
            raise DataError('An active dataset and a nonempty source annotation are required.')
        with self.connect() as db:
            db.execute('INSERT INTO notes(signature,user_id,note,created_at) VALUES (?,?,?,?)',
                       (dataset['dataset_signature'], user['id'], text.strip()[:4000], now()))
            self.audit(user['id'], 'source_annotation', dataset['dataset_signature'], db)

    def notes(self, signature):
        with self.connect() as db:
            return [dict(r) for r in db.execute('SELECT note,created_at,user_id FROM notes WHERE signature=?', (signature,))]

    def latest_forecast(self, signature, block):
        with self.connect() as db:
            row = db.execute("SELECT payload FROM forecasts WHERE signature=? AND block=? AND status='completed' ORDER BY created_at DESC LIMIT 1", (signature, block)).fetchone()
            return json.loads(row[0]) if row else None


def require_admin(user):
    if not user or not user.get('active') or user.get('role') != 'admin':
        raise PermissionError('Administrator / Researcher permission required.')
