"""Asterisk boundary double: runs the real AGI and speaks its wire protocol."""
import os
import shlex
import signal
import threading
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run_agi(mode, config, variables=None, digits=None, uniqueid='1700000000.1', export_pythonpath=True, entrypoint=None, hangup_after=None):
    variables = dict(variables or {})
    digits = list(digits or [])
    commands = []
    digit_stream = []
    env = dict(os.environ, CALLFLOW_HOOKS_CONFIG_FILE=str(config), PYTHONPATH=str(ROOT))
    command = [sys.executable, '-m', 'issabel_crm', mode]
    if not export_pythonpath:
        env.pop('PYTHONPATH', None)
        command = [sys.executable, '-c',
            'import sys; sys.path.insert(0, ' + repr(str(ROOT)) + '); '
            'from issabel_crm.__main__ import main; main()', mode]
    if entrypoint:
        command = [sys.executable, str(entrypoint)]
    process = subprocess.Popen(
        command, cwd=str(ROOT if export_pythonpath else Path(config).parent), env=env,
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        universal_newlines=True, bufsize=1)
    started = time.monotonic()
    process.stdin.write('agi_uniqueid: ' + uniqueid + '\nagi_channel: PJSIP/caller-0001\n\n')
    process.stdin.flush()
    timer = None
    if hangup_after is not None:
        timer = threading.Timer(hangup_after, lambda: process.send_signal(signal.SIGHUP))
        timer.daemon = True
        timer.start()
    for line in process.stdout:
        commands.append(line.strip())
        args = shlex.split(line)
        response = '200 result=1\n'
        if args[:2] == ['GET', 'VARIABLE']:
            value = variables.get(args[2].lstrip('_'))
            response = ('200 result=1 (' + value + ')\n') if value else '200 result=0\n'
        elif args[:3] == ['GET', 'FULL', 'VARIABLE']:
            value = variables.get('CHANNEL(linkedid)', uniqueid)
            response = '200 result=1 (' + value + ')\n'
        elif args[:2] == ['SET', 'VARIABLE']:
            variables[args[2].lstrip('_')] = args[3]
        elif args[:2] == ['GET', 'OPTION']:
            token = digits.pop(0) if digits else ''
            digit_stream = list(token + ('#' if token and token[-1] not in '*#' else ''))
            response = '200 result=' + str(ord(digit_stream.pop(0)) if digit_stream else 0) + ' endpos=8000\n'
        elif args[:3] == ['WAIT', 'FOR', 'DIGIT']:
            response = '200 result=' + str(ord(digit_stream.pop(0)) if digit_stream else 0) + '\n'
        if args[:2] == ['STREAM', 'FILE']:
            response = '200 result=0 endpos=8000\n'
        try:
            process.stdin.write(response)
            process.stdin.flush()
        except BrokenPipeError:
            break
    if timer:
        timer.cancel()
    try:
        process.stdin.close()
    except BrokenPipeError:
        pass
    process.wait(timeout=5)
    errors = process.stderr.read()
    process.stdout.close()
    process.stderr.close()
    if process.returncode:
        raise AssertionError('AGI failed: ' + errors)
    return variables, commands, time.monotonic() - started, errors
