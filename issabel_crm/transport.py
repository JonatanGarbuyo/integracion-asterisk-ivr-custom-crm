import json
import os
import subprocess
import sys
import time


def worker_environment():
    environment = dict(os.environ)
    environment['PYTHONPATH'] = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return environment


def request(work, timeout):
    started = time.monotonic()
    work = dict(work, timeout=timeout)
    encoded = json.dumps(work).encode()
    try:
        with subprocess.Popen(
                [sys.executable, '-m', 'issabel_crm.http_worker'], stdin=subprocess.PIPE,
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, close_fds=True,
                env=worker_environment()) as worker:
            try:
                remaining = timeout - (time.monotonic() - started)
                if remaining <= 0:
                    worker.kill()
                    worker.communicate()
                    return {'error': 'timeout'}
                output, _ = worker.communicate(encoded, timeout=remaining)
            except subprocess.TimeoutExpired:
                worker.kill()
                worker.communicate()
                return {'error': 'timeout'}
            except BaseException:
                # Includes caller hangup: never leave a DNS/HTTP worker behind.
                worker.kill()
                worker.wait()
                raise
            returncode = worker.returncode
    except OSError:
        return {'error': 'launch_failed'}
    try:
        result = json.loads(output.decode())
        if time.monotonic() - started >= timeout:
            return {'error': 'timeout'}
        return result if returncode == 0 and isinstance(result, dict) else {'error': 'worker_failed'}
    except (ValueError, UnicodeError):
        return {'error': 'worker_failed'}
