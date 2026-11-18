"""Launch web and forecast worker together; either failure stops the deployment."""
from contextlib import contextmanager
import os
import signal
import subprocess
import sys
import threading


@contextmanager
def local_worker():
    process = subprocess.Popen([sys.executable, '-m', 'dashboard.monthly.worker', '--watch-stdin'],
        stdin=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
    try:
        yield process
    finally:
        process.stdin.close()
        try:
            process.wait(timeout=25)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)


def main():
    stop = threading.Event()
    for signum in (signal.SIGTERM, signal.SIGINT):
        signal.signal(signum, lambda *_: stop.set())
    with local_worker() as worker:
        web = subprocess.Popen([sys.executable, '-m', 'gunicorn', 'app:server', '--bind',
            '0.0.0.0:' + os.environ.get('PORT', '8050'), '--workers', '1', '--threads', '4', '--timeout', '600'])
        try:
            while not stop.wait(0.5):
                if worker.poll() is not None or web.poll() is not None:
                    raise RuntimeError('Web or forecast worker exited; restart the application.')
        finally:
            if web.poll() is None:
                web.terminate()
            try:
                web.wait(timeout=15)
            except subprocess.TimeoutExpired:
                web.kill()
                web.wait(timeout=10)


if __name__ == '__main__':
    main()
