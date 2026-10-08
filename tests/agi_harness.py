"""Runs the real AGI executable against an Asterisk protocol boundary double."""
import shlex
import subprocess
import sys
import threading
import time

from test_admin import ENTRY


def call(config, profile='welcome', callerid='555123', variables=None, digits=''):
    variables = dict(variables or {})
    commands = []
    process = subprocess.Popen([sys.executable, str(ENTRY), '--config', str(config), 'agi', profile],
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               universal_newlines=True, bufsize=1)
    timer = threading.Timer(6, process.kill)
    timer.start()
    start = time.monotonic()
    process.stdin.write('agi_uniqueid: 1700000000.1\nagi_callerid: ' + callerid + '\nagi_channel: SIP/caller-0001\n\n')
    process.stdin.flush()
    try:
        for line in process.stdout:
            commands.append(line.strip())
            args = shlex.split(line)
            response = '200 result=1\n'
            if args[:2] == ['GET', 'VARIABLE']:
                value = variables.get(args[2], '')
                response = '200 result=1 (' + value + ')\n' if value else '200 result=0\n'
            elif args[:2] == ['SET', 'VARIABLE']:
                variables[args[2].lstrip('_')] = args[3]
            elif args[:2] == ['GET', 'DATA']:
                response = '200 result=' + digits + '\n' if digits else '200 result=0 (timeout)\n'
            process.stdin.write(response)
            process.stdin.flush()
        process.stdin.close()
        process.wait(timeout=2)
        error = process.stderr.read()
        if process.returncode:
            raise AssertionError(error)
        return variables, commands, time.monotonic() - start
    finally:
        timer.cancel()
        if process.poll() is None:
            process.kill()
            process.wait()
        process.stdout.close()
        process.stderr.close()

