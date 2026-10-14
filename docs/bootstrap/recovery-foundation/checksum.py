#!/usr/bin/env python3
"""Deterministic handoff checksums for ticket #41 (staging only).

Generates and verifies docs/bootstrap/recovery-foundation/handoff.json so the
operator publishes exactly the bytes written by OpenCode. Hashes are computed
by this tool, never invented by the model.

Live destination: tools/recovery_checksum.py.

Python 3.6 compatible. No secrets, no network.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path, PurePosixPath

sys.dont_write_bytecode = True

VERSION = 1
TICKET = 41

# Handoff origins (this staging dir) mapped to live destinations.
DESTINATIONS = {
    'preserve.py': 'tools/recovery_preserve.py',
    'restore.py': 'tools/recovery_restore.py',
    'review.py': 'tools/recovery_review.py',
    'checksum.py': 'tools/recovery_checksum.py',
    'recovery-review.yml': '.github/workflows/recovery-review.yml',
    'README.md': 'docs/bootstrap/recovery-foundation/README.md',
}

WORKFLOWS_AFFECTED = ['.github/workflows/recovery-review.yml']


def is_safe(name):
    path = PurePosixPath(name)
    return not (path.is_absolute()
                or any(part in ('..', '.', '') for part in path.parts)
                or '\\' in name or any(ord(c) < 32 for c in name))


def digest(root):
    entries = []
    for path in sorted(root.rglob('*')):
        if path.is_dir():
            continue
        rel = path.relative_to(root).as_posix()
        if rel == 'handoff.json':
            continue
        if not is_safe(rel):
            raise RuntimeError('unsafe-path: ' + rel)
        if path.is_symlink():
            raise RuntimeError('symlink-refused: ' + rel)
        content = path.read_bytes()
        entries.append({'path': rel,
                        'dest': DESTINATIONS.get(rel, ''),
                        'bytes': len(content),
                        'sha256': hashlib.sha256(content).hexdigest(),
                        'mode': oct(path.stat().st_mode & 0o777)})
    return entries


def build(root):
    files = digest(root)
    if sorted(DESTINATIONS) != sorted([f['path'] for f in files
                                       if f['path'] in DESTINATIONS]):
        missing = sorted(set(DESTINATIONS) - set(f['path'] for f in files))
        raise RuntimeError('incomplete-handoff, missing: ' + ','.join(missing))
    return {'version': VERSION, 'ticket': TICKET,
            'tool': 'recovery-foundation/checksum.py',
            'files': files,
            'workflows_affected': WORKFLOWS_AFFECTED}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', default=str(
        Path(__file__).resolve().parent))
    parser.add_argument('--output', default='')
    parser.add_argument('--verify', default='',
                        help='Verify an existing handoff.json against --root')
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    if args.verify:
        try:
            expected = json.loads(Path(args.verify).read_text())
        except (OSError, ValueError):
            print(json.dumps({'status': 'failed',
                              'reason': 'handoff-unreadable'}))
            return 1
        try:
            actual = build(root)
        except (OSError, RuntimeError) as error:
            print(json.dumps({'status': 'failed', 'reason': str(error)}))
            return 1
        if actual == expected:
            print(json.dumps({'status': 'verified',
                              'files': len(actual['files'])}))
            return 0
        print(json.dumps({'status': 'failed', 'reason': 'handoff-mismatch'}))
        return 1
    try:
        document = build(root)
    except (OSError, RuntimeError) as error:
        print(json.dumps({'status': 'failed', 'reason': str(error)}))
        return 1
    text = json.dumps(document, indent=2, sort_keys=False) + '\n'
    if args.output:
        Path(args.output).write_text(text)
    print(text, end='')
    return 0


if __name__ == '__main__':
    sys.exit(main())
