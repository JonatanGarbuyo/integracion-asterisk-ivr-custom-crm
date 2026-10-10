#!/usr/bin/env python3
"""Trusted quality checks for an agent's candidate; no provider or GitHub keys."""
import os
import pathlib
import subprocess
import sys


def commands(workspace):
    required = ('module/backend/entry.py', 'module/module.xml', 'tests/test_call.py', 'tests/test_admin.py', 'tools/build-rpm.py')
    if not all((workspace / path).is_file() for path in required):
        raise RuntimeError('La rama no contiene el addon y sus pruebas; usar la base aprobada de PR #30 durante el bootstrap.')
    checks = [[sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-v']]
    checks += [['php', '-l', str(path.relative_to(workspace))]
               for directory in ('module', 'native', 'packaging')
               for path in sorted((workspace / directory).rglob('*.php'))]
    checks.append([sys.executable, 'tools/build-rpm.py'])
    for version in ('3.6', '3.9', '3.12'):
        checks.append(['docker', 'run', '--rm', '-v', str(workspace)+':/project:ro', '-w', '/project',
                       'python:'+version, 'python', '-m', 'unittest', 'discover', '-s', 'tests', '-v'])
    # PHP8.2's official Debian image needs Python for our real backend boundaries.
    # Tests run as nobody so the permission-denied case is actually exercised.
    php_checks = ('set -eu; apt-get update -qq; apt-get install -y -qq python3; '
                  'python3 -c \'import pathlib, subprocess; '
                  '[subprocess.run(["php", "-l", str(p)], check=True) for d in '
                  '("module", "native", "packaging") for p in pathlib.Path(d).rglob("*.php")]\'; '
                  'su -s /bin/sh nobody -c "python3 -m unittest discover -s tests -p \'*web.py\' -v"; '
                  'su -s /bin/sh nobody -c "python3 -m unittest discover -s tests -p test_pbx_state.py -v"')
    checks.append(['docker', 'run', '--rm', '-v', str(workspace)+':/project:ro', '-w', '/project',
                   'php:8.2-cli', 'sh', '-c', php_checks])
    return checks


def main():
    workspace = pathlib.Path(sys.argv[1]).resolve()
    # Deliberate allowlist: tests and containers do not inherit credentials/config.
    environment = {key: os.environ[key] for key in ('PATH', 'LANG', 'LC_ALL', 'TMPDIR') if key in os.environ}
    try:
        for command in commands(workspace):
            print('Check: '+command[0], flush=True)
            subprocess.run(command, cwd=str(workspace), env=environment, check=True, timeout=900)
    except (RuntimeError, OSError, subprocess.SubprocessError) as error:
        message = str(error) if isinstance(error, RuntimeError) else 'Falló un check obligatorio; revisar su salida.'
        print(message, file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
