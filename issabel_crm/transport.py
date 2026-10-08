import json
import os
import subprocess
import sys


def worker_environment():
    environment = dict(os.environ)
    environment['PYTHONPATH'] = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return environment


def request(work, timeout):
    work = dict(work, timeout=timeout)
    try:
        completed = subprocess.run(
            [sys.executable, '-m', 'issabel_crm.http_worker'],
            input=json.dumps(work).encode(), stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            timeout=timeout, check=False, close_fds=True, env=worker_environment())
    except subprocess.TimeoutExpired:
        return {'error': 'timeout'}
    except OSError:
        return {'error': 'launch_failed'}
    try:
        result = json.loads(completed.stdout.decode())
        return result if completed.returncode == 0 and isinstance(result, dict) else {'error': 'worker_failed'}
    except (ValueError, UnicodeError):
        return {'error': 'worker_failed'}
