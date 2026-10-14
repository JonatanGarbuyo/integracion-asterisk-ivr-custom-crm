#!/usr/bin/env python3
"""Verify provenance/checksums/completeness and restore a candidate bundle.

Handoff source for ticket #41 (staging only). The operator copies these bytes
without completing implementation. Live destination: tools/recovery_restore.py.

Only manifest + sources + patch are restoration sources. result.json,
transcripts and logs are provenance only and are never applied as source.

Python 3.6 compatible. No secrets, no network, no GitHub token.
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path, PurePosixPath

sys.dont_write_bytecode = True

MAX_PATCH_BYTES = 4 * 1024 * 1024

SENSITIVE_SUFFIXES = ('.pem', '.key', '.p12', '.pfx', '.log', '.db',
                      '.sqlite', '.sqlite3')
SENSITIVE_PARTS = ('.git', '.claude', '.opencode', 'secrets', 'credentials')
SENSITIVE_NAMES = ('auth.json', 'profiles.conf', '.dev.vars')


class Refused(RuntimeError):
    pass


def clean_environment():
    source = os.environ
    return {key: source[key] for key in ("PATH", "LANG", "LC_ALL",
                                        "TMPDIR", "SYSTEMROOT") if key in source}


def git_text(repo, args):
    environment = clean_environment()
    environment.update({'GIT_CONFIG_GLOBAL': os.devnull,
                        'GIT_CONFIG_NOSYSTEM': '1'})
    try:
        out = subprocess.run(['git', '-c', 'core.fsmonitor=false',
                              '-c', 'core.hooksPath=/dev/null'] + args,
                             cwd=str(repo), env=environment,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.DEVNULL,
                             check=True, timeout=120).stdout
    except (OSError, subprocess.SubprocessError):
        raise Refused('git-read-failed')
    return out


def unsafe_path(name):
    path = PurePosixPath(name)
    if (path.is_absolute() or any(part in ('..', '.', '') for part in path.parts)
            or '\\' in name or any(ord(c) < 32 for c in name)):
        return True
    if (path.suffix.lower() in SENSITIVE_SUFFIXES
            or any(part in SENSITIVE_PARTS
                   or part.startswith(('.env', '.dev.vars'))
                   for part in path.parts)
            or path.name in SENSITIVE_NAMES):
        return True
    return False


def check_entry(bundle, entry, prefix):
    name = entry.get('path', '')
    if not isinstance(name, str) or not name or unsafe_path(name):
        raise Refused('unsafe-or-sensitive-path')
    artifact = entry.get('artifact', '')
    if not isinstance(artifact, str) or not artifact.startswith(prefix):
        raise Refused('artifact-outside-delivery')
    apart = PurePosixPath(artifact)
    if apart.is_absolute() or '..' in apart.parts:
        raise Refused('artifact-outside-delivery')
    if entry.get('deleted'):
        return None
    if entry.get('mode') not in ('100644', '100755'):
        raise Refused('not-regular-source')
    target = bundle / artifact
    try:
        if target.is_symlink():
            raise Refused('symlink-refused')
        content = target.read_bytes()
    except OSError:
        raise Refused('incomplete-bundle')
    if len(content) != entry.get('bytes'):
        raise Refused('tampered-bundle')
    if hashlib.sha256(content).hexdigest() != entry.get('sha256'):
        raise Refused('tampered-bundle')
    return content


def check_patch(bundle, info, name):
    if info is None:
        return b''
    target = bundle / info.get('artifact', '')
    apart = PurePosixPath(info.get('artifact', ''))
    if apart.is_absolute() or '..' in apart.parts:
        raise Refused('artifact-outside-delivery')
    try:
        if target.is_symlink():
            raise Refused('symlink-refused')
        content = target.read_bytes()
    except OSError:
        raise Refused('incomplete-bundle')
    if len(content) > MAX_PATCH_BYTES:
        raise Refused('truncated-bundle')
    if len(content) != info.get('bytes'):
        raise Refused('tampered-bundle')
    if hashlib.sha256(content).hexdigest() != info.get('sha256'):
        raise Refused('tampered-bundle')
    if name == 'uncommitted.patch' and len(content) == 0:
        return b''
    return content


def restore(bundle, worktree):
    result = {'status': 'failed'}
    try:
        manifest = json.loads((bundle / 'manifest.json').read_text())
    except (OSError, ValueError):
        result['reason'] = 'incomplete-bundle'
        return result
    try:
        if manifest.get('version') != 1:
            raise Refused('provenance-invalid')
        base = manifest.get('base_sha', '')
        head = manifest.get('head_sha', '')
        if not all(re.fullmatch('[0-9a-f]{40}', v) for v in (base, head)):
            raise Refused('provenance-invalid')
        if not manifest.get('termination_confirmed'):
            raise Refused('termination-unconfirmed')
        if manifest.get('status') != 'complete':
            raise Refused('incomplete-bundle')
        if manifest.get('truncated'):
            raise Refused('truncated-bundle')
        if manifest.get('exclusions'):
            raise Refused('incomplete-bundle')
        entries = manifest.get('files', [])
        if not isinstance(entries, list):
            raise Refused('incomplete-bundle')
        committed_entries = [e for e in entries
                             if str(e.get('artifact', '')).startswith('sources/')]
        uncommitted_entries = [
            e for e in entries
            if str(e.get('artifact', '')).startswith('uncommitted_sources/')]
        for entry in committed_entries:
            check_entry(bundle, entry, 'sources/')
        for entry in uncommitted_entries:
            check_entry(bundle, entry, 'uncommitted_sources/')
        cpatch = check_patch(bundle, manifest.get('patch'),
                             'candidate.patch')
        upatch = check_patch(bundle, manifest.get('uncommitted_patch'),
                             'uncommitted.patch')
        # Worktree must be a clean checkout of the registered base.
        actual = git_text(worktree, ['rev-parse', 'HEAD']).decode().strip()
        if actual != base:
            raise Refused('base-mismatch')
        if git_text(worktree, ['status', '--porcelain',
                               '--untracked-files=all']).strip():
            raise Refused('worktree-not-clean')
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(cpatch)
            cpatch_path = tmp.name
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(upatch)
            upatch_path = tmp.name
        try:
            environment = clean_environment()
            environment.update({'GIT_CONFIG_GLOBAL': os.devnull,
                                'GIT_CONFIG_NOSYSTEM': '1'})
            try:
                subprocess.run(['git', 'apply', '--index', '--binary',
                                cpatch_path],
                               cwd=str(worktree), env=environment,
                               stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL,
                               check=True, timeout=300)
            except (OSError, subprocess.SubprocessError):
                raise Refused('patch-does-not-apply')
            tree = git_text(worktree, ['write-tree']).decode().strip()
            if tree != manifest.get('tree_sha'):
                raise Refused('tampered-bundle')
            if upatch:
                try:
                    subprocess.run(['git', 'apply', '--binary', upatch_path],
                                   cwd=str(worktree), env=environment,
                                   stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL,
                                   check=True, timeout=300)
                except (OSError, subprocess.SubprocessError):
                    raise Refused('patch-does-not-apply')
            # Verify restored worktree bytes match the manifest sources.
            for entry in committed_entries + uncommitted_entries:
                if entry.get('deleted'):
                    if (worktree / entry['path']).exists():
                        raise Refused('tampered-bundle')
                    continue
                target = worktree / entry['path']
                try:
                    if target.is_symlink():
                        raise Refused('symlink-refused')
                    content = target.read_bytes()
                except OSError:
                    raise Refused('tampered-bundle')
                if hashlib.sha256(content).hexdigest() != entry.get('sha256'):
                    raise Refused('tampered-bundle')
        finally:
            for path in (cpatch_path, upatch_path):
                try:
                    os.unlink(path)
                except OSError:
                    pass
        result.update(status='restored', base=base, head=head,
                      files=len(entries))
    except Refused as error:
        result['reason'] = str(error)
    except (OSError, ValueError, KeyError, UnicodeError):
        result['reason'] = 'restore-runtime-failure'
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=['restore'])
    parser.add_argument('--bundle', required=True)
    parser.add_argument('--worktree', required=True)
    args = parser.parse_args(argv)
    result = restore(Path(args.bundle).resolve(),
                     Path(args.worktree).resolve())
    print(json.dumps(result))
    return 0 if result.get('status') == 'restored' else 1


if __name__ == '__main__':
    sys.exit(main())
