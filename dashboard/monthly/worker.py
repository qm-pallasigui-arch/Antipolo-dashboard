"""Persistent queue supervisor. Run with python -m dashboard.monthly.worker."""
import argparse
import json
import logging
import os
import signal
import sys
import threading

from .process_tree import ProcessTree


def execute():
    # Handshake ensures process-tree containment exists before model code runs.
    settings = json.loads(sys.stdin.readline())
    if os.name != 'nt':
        def parent_closed():
            sys.stdin.read()
            os.killpg(os.getpgrp(), signal.SIGKILL)
        threading.Thread(target=parent_closed, daemon=True).start()
    from .store import Store
    from .forecasting.config import PrototypeModelConfig
    from .repositories.batch_repository import BatchRepository
    from .services.forecast_service import ForecastService
    store = Store(settings['path'], database_url=settings['database_url'],
                  is_prototype=settings['is_prototype'], model_config=PrototypeModelConfig(**settings['configuration']))
    batch = BatchRepository(store).get(settings['batch_id'])
    if not batch or batch['status'] != 'running':
        return
    with store.connect() as db:
        row = db.execute('SELECT id,role,active FROM users WHERE id=?', (batch['actor_id'],)).fetchone()
    user = dict(row) if row else None
    ForecastService(store).run_all(user, batch=batch)


def run_once(store, stop=None, *, command=None):
    """Supervise one claimed batch, returning False when the queue is empty."""
    from .repositories.batch_repository import BatchRepository
    stop = stop or threading.Event()
    repo = BatchRepository(store)
    batch = repo.take_next()
    if not batch:
        return False
    tree = None
    reason, status = 'Forecast process stopped before completion. Generate forecasts again.', 'interrupted'
    try:
        tree = ProcessTree(command or [sys.executable, '-m', 'dashboard.monthly.worker', '--execute'])
        tree.process.stdin.write(json.dumps(dict(path=str(store.path.resolve()), database_url=store.database_url,
            configuration=store.model_config.snapshot(), is_prototype=store.is_prototype, batch_id=batch['id'])) + '\n')
        tree.process.stdin.flush()
        while tree.process.poll() is None:
            if stop.wait(0.5):
                reason = 'Forecast worker shut down. Generate forecasts again.'
                break
            current = repo.get(batch['id'])
            if current['status'] == 'cancelling':
                status, reason = 'cancelled', 'Forecast cancelled. Completed results are retained; no new ranking was generated.'
                break
            if current['status'] != 'running':
                break
            with store.connect() as db:
                active = db.execute("SELECT signature FROM datasets WHERE state='active'").fetchone()
            if not active or active[0] != batch['signature']:
                reason = 'Active dataset changed. Generate forecasts for the new dataset.'
                break
    except Exception:
        logging.getLogger(__name__).exception('Forecast supervisor failed: %s', batch['id'])
    finally:
        if tree:
            tree.stop()
        # Never release ownership before the process tree is stopped and reaped.
        current = repo.get(batch['id'])
        if current and current['status'] == 'cancelling':
            status, reason = 'cancelled', 'Forecast cancelled. Completed results are retained; no new ranking was generated.'
        repo.stopped(batch, status, reason)
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--watch-stdin', action='store_true', help='Stop when the local launcher closes its pipe.')
    args = parser.parse_args()
    from dashboard.logging_config import configure_logging
    configure_logging()
    if args.execute:
        execute()
        return
    from .store import Store
    store = Store()
    stop = threading.Event()
    for signum in (signal.SIGINT, signal.SIGTERM):
        signal.signal(signum, lambda *_: stop.set())
    if args.watch_stdin:
        def closed():
            sys.stdin.read()
            stop.set()
        threading.Thread(target=closed, daemon=True).start()
    while not stop.is_set():
        try:
            if not run_once(store, stop):
                stop.wait(1)
        except Exception:
            logging.getLogger(__name__).exception('Worker queue unavailable; retrying')
            stop.wait(5)


if __name__ == '__main__':
    main()
