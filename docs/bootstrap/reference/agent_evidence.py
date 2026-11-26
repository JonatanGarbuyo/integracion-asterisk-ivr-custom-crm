#!/usr/bin/env python3
"""Export only a terminated worker's validated, committed candidate. No credentials."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
from agent_flow import clean_environment, protected

MAX_FILES = 200
MAX_FILE_BYTES = 256 * 1024
MAX_SOURCE_BYTES = 2 * 1024 * 1024
MAX_PATCH_BYTES = 4 * 1024 * 1024


class Unavailable(RuntimeError):
    pass


def read_git(repo, args, limit=MAX_PATCH_BYTES):
    environment = clean_environment()
    environment.update({'GIT_CONFIG_GLOBAL': os.devnull, 'GIT_CONFIG_NOSYSTEM': '1'})
    with tempfile.TemporaryFile() as output:
        try:
            subprocess.run(['git', '-c', 'core.fsmonitor=false', '-c', 'core.hooksPath=/dev/null'] + args,
                           cwd=str(repo), env=environment, stdout=output, stderr=subprocess.DEVNULL,
                           check=True, timeout=120)
        except (OSError, subprocess.SubprocessError):
            raise Unavailable('git-read-failed')
        output.seek(0)
        content = output.read(limit + 1)
        if len(content) > limit:
            raise Unavailable('output-limit')
        return content


def excluded_path(name):
    path = PurePosixPath(name)
    if (path.is_absolute() or any(part in ('..', '.', '') for part in path.parts)
            or '\\' in name or any(ord(c) < 32 for c in name) or protected(name)):
        return 'protected-or-unsafe-path'
    if (path.suffix.lower() in ('.pem', '.key', '.p12', '.pfx', '.log', '.db', '.sqlite', '.sqlite3')
            or any(part in ('.git', '.claude', '.opencode', 'secrets', 'credentials')
                   or part.startswith(('.env', '.dev.vars')) for part in path.parts)
            or path.name in ('auth.json', 'profiles.conf', '.dev.vars')):
        return 'sensitive-or-operational-path'
    return None


def snapshot(repo, base, head, output, terminated):
    manifest = {'version': 1, 'status': 'unavailable', 'base_sha': base, 'head_sha': head,
                'committed_only': True, 'termination_confirmed': terminated, 'truncated': False,
                'changed_count': 0, 'files': [], 'exclusions': [],
                'limits': {'files': MAX_FILES, 'file_bytes': MAX_FILE_BYTES,
                           'source_bytes': MAX_SOURCE_BYTES, 'patch_bytes': MAX_PATCH_BYTES}}
    if not terminated:
        manifest['reason'] = 'termination-unconfirmed'
        return manifest
    if output == repo or repo in output.parents or output.exists():
        manifest['reason'] = 'output-not-isolated-or-new'
        return manifest
    try:
        if not all(re.fullmatch('[0-9a-f]{40}', value) for value in (base, head)):
            raise Unavailable('commit-invalid')
        actual = read_git(repo, ['rev-parse', 'HEAD']).decode().strip()
        if actual != head or read_git(repo, ['status', '--porcelain', '--untracked-files=all']).strip():
            raise Unavailable('workspace-not-clean-at-head')
        read_git(repo, ['merge-base', '--is-ancestor', base, head])
        names = read_git(repo, ['diff', '--no-renames', '--name-only', '-z', base, head]).decode().split('\0')
        names = [name for name in names if name]
        manifest['changed_count'] = len(names)
        if len(names) > MAX_FILES:
            manifest['truncated'] = True
            raise Unavailable('file-count-limit')
        files, total = [], 0
        for name in names:
            reason = excluded_path(name)
            if reason:
                manifest['exclusions'].append({'path': name, 'reason': reason})
                continue
            tree = read_git(repo, ['ls-tree', '-z', head, '--', name]).decode().rstrip('\0')
            if not tree:
                files.append(({'path': name, 'deleted': True}, None))
                continue
            fields, path = tree.split('\t', 1)
            mode, kind, blob = fields.split()
            if path != name or kind != 'blob' or mode not in ('100644', '100755'):
                manifest['exclusions'].append({'path': name, 'reason': 'not-regular-source'})
                continue
            size = int(read_git(repo, ['cat-file', '-s', blob]).decode())
            if size > MAX_FILE_BYTES or total + size > MAX_SOURCE_BYTES:
                manifest['truncated'] = True
                manifest['exclusions'].append({'path': name, 'reason': 'source-size-limit'})
                continue
            content = read_git(repo, ['cat-file', 'blob', blob], MAX_FILE_BYTES)
            total += len(content)
            files.append(({'path': name, 'mode': mode, 'blob_sha': blob,
                           'bytes': len(content), 'sha256': hashlib.sha256(content).hexdigest(),
                           'artifact': 'sources/' + name}, content))
        if manifest['exclusions']:
            manifest.update(status='incomplete', reason='excluded-source')
        else:
            patch = read_git(repo, ['diff', '--no-ext-diff', '--no-textconv', '--no-renames', '--binary',
                                   '--full-index', base, head], MAX_PATCH_BYTES)
            if read_git(repo, ['rev-parse', 'HEAD']).decode().strip() != head or read_git(
                    repo, ['status', '--porcelain', '--untracked-files=all']).strip():
                raise Unavailable('workspace-changed')
            manifest['tree_sha'] = read_git(repo, ['rev-parse', head + '^{tree}']).decode().strip()
            output.mkdir(parents=True, mode=0o700)
            for entry, content in files:
                if content is not None:
                    target = output / entry['artifact']
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(content)
                    target.chmod(0o600)
                manifest['files'].append(entry)
            (output / 'candidate.patch').write_bytes(patch)
            (output / 'candidate.patch').chmod(0o600)
            manifest['patch'] = {'artifact': 'candidate.patch', 'bytes': len(patch),
                                 'sha256': hashlib.sha256(patch).hexdigest()}
            manifest.update(status='complete', source_bytes=total)
    except (Unavailable, OSError, ValueError, UnicodeError) as error:
        manifest['reason'] = str(error) if isinstance(error, Unavailable) else 'snapshot-failed'
        if manifest['reason'] == 'output-limit':
            manifest['truncated'] = True
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=['snapshot'])
    parser.add_argument('--workspace', required=True)
    parser.add_argument('--base', required=True)
    parser.add_argument('--head', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--worker-terminated', action='store_true')
    args = parser.parse_args()
    output = Path(args.output).resolve()
    manifest = snapshot(Path(args.workspace).resolve(), args.base, args.head, output, args.worker_terminated)
    if manifest['status'] in ('complete', 'incomplete'):
        output.mkdir(parents=True, exist_ok=True)
        (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
        (output / 'manifest.json').chmod(0o600)
    print(json.dumps(manifest))
    return 0 if manifest['status'] == 'complete' else 1


if __name__ == '__main__':
    sys.exit(main())
