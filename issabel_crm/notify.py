"""Transient, bounded emitters: no listener, durable payloads or retry queue."""
import fcntl
import json
import os
import subprocess
import sys

from .transport import request, worker_environment


def launch(config, payload):
    work = {'method': 'POST', 'url': config['notify_url'], 'token': config['notify_token'],
            'payload': payload, 'timeout': config['notify_timeout']}
    encoded = json.dumps(work).encode()
    descriptor = None
    try:
        # The installer owns this directory. Never create a spool on the answer path.
        for slot in range(config['notify_max_workers']):
            candidate = os.open(os.path.join(config['runtime_dir'], 'slot-' + str(slot)),
                                os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
            try:
                fcntl.flock(candidate, fcntl.LOCK_EX | fcntl.LOCK_NB)
                descriptor = candidate
                break
            except BlockingIOError:
                os.close(candidate)
        if descriptor is None:
            return 'saturated'
        process = subprocess.Popen(
            [sys.executable, '-m', 'issabel_crm.notify'], stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True,
            pass_fds=(descriptor,), start_new_session=True, env=worker_environment())
        try:
            pipe = process.stdin.fileno()
            # One bounded atomic write, never wait for a child or remote response.
            if len(encoded) > os.fpathconf(pipe, 'PC_PIPE_BUF'):
                process.kill()
                process.wait()
                return 'payload_too_large'
            flags = fcntl.fcntl(pipe, fcntl.F_GETFL)
            fcntl.fcntl(pipe, fcntl.F_SETFL, flags | os.O_NONBLOCK)
            os.write(pipe, encoded)
        except OSError:
            process.kill()
            process.wait()
            return 'launch_failed'
        finally:
            process.stdin.close()
        return 'launched'
    except OSError:
        return 'launch_failed'
    finally:
        if descriptor is not None:
            # Do not LOCK_UN: the child inherited the same open-file description.
            os.close(descriptor)


def main():
    from .diagnostic import record
    try:
        work = json.load(sys.stdin)
        result = request(work, work['timeout'])
        status = result.get('status', 0)
        outcome = 'delivered' if 200 <= status < 300 else result.get('error', 'http_error')
        record('notification_' + outcome, work['payload']['interaction_id'], stderr=False)
    except (OSError, ValueError, KeyError):
        record('notification_worker_failed', stderr=False)


if __name__ == '__main__':
    main()
