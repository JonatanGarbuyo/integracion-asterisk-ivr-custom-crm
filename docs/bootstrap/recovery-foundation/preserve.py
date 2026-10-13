#!/usr/bin/env python3
"""Preserve a terminated worker's candidate: committed + uncommitted, with result.json.

Handoff source for ticket #41 (staging only). The operator copies these bytes
without completing implementation. Live destination: tools/recovery_preserve.py.

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

VERSION = 1
MAX_FILES = 200
MAX_FILE_BYTES = 256 * 1024
MAX_SOURCE_BYTES = 2 * 1024 * 1024
MAX_PATCH_BYTES = 4 * 1024 * 1024

ALLOWED_ROOTS = ("module/", "native/", "extensions/", "packaging/",
                 "tests/", "docs/", "tools/")
PROTECTED = (".github", ".git", ".opencode", ".claude", "AGENTS.md",
             "opencode.json", "opencode.jsonc",
             "tools/agent_", "tests/automation", "docs/agents",
             "docs/planning", "CONTEXT.md", "README.md")


class Unavailable(RuntimeError):
    pass


def clean_environment():
    source = os.environ
    return {key: source[key] for key in ("PATH", "LANG", "LC_ALL",
                                        "TMPDIR", "SYSTEMROOT") if key in source}


def read_git(repo, args, limit=MAX_PATCH_BYTES):
    environment = clean_environment()
    environment.update({'GIT_CONFIG_GLOBAL': os.devnull,
                        'GIT_CONFIG_NOSYSTEM': '1'})
    with tempfile.TemporaryFile() as output:
        try:
            subprocess.run(['git', '-c', 'core.fsmonitor=false',
                            '-c', 'core.hooksPath=/dev/null'] + args,
                           cwd=str(repo), env=environment, stdout=output,
                           stderr=subprocess.DEVNULL, check=True, timeout=120)
        except (OSError, subprocess.SubprocessError):
            raise Unavailable('git-read-failed')
        output.seek(0)
        content = output.read(limit + 1)
        if len(content) > limit:
            raise Unavailable('output-limit')
        return content


def protected_path(path):
    for root in ALLOWED_ROOTS:
        if path.startswith(root):
            break
    else:
        return True
    for item in PROTECTED:
        if path == item or path.startswith(item + "/") or (
                item.endswith("_") and path.startswith(item)):
            return True
    for part in PurePosixPath(path).parts:
        if part.startswith(".env") or part == "AGENTS.md":
            return True
    return False


def excluded_path(name):
    path = PurePosixPath(name)
    if (path.is_absolute() or any(part in ('..', '.', '') for part in path.parts)
            or '\\' in name or any(ord(c) < 32 for c in name)
            or protected_path(name)):
        return 'protected-or-unsafe-path'
    if (path.suffix.lower() in ('.pem', '.key', '.p12', '.pfx', '.log',
                                '.db', '.sqlite', '.sqlite3')
            or any(part in ('.git', '.claude', '.opencode', 'secrets',
                            'credentials')
                   or part.startswith(('.env', '.dev.vars'))
                   for part in path.parts)
            or path.name in ('auth.json', 'profiles.conf', '.dev.vars')):
        return 'sensitive-or-operational-path'
    return None


def outcome_of(result_path, explicit):
    if explicit:
        return explicit
    try:
        data = json.loads(Path(result_path).read_text())
    except (OSError, ValueError):
        return 'unknown'
    reason = str(data.get('reason', '') or data.get('status', ''))
    # Never conflate: timeout stays timeout, check failure stays check-failed.
    if 'timeout' in reason:
        return 'timeout'
    if reason in ('command-failed', 'gate-failed', 'checks-failed',
                  'review-failed', 'check-failed'):
        return 'check-failed'
    if 'review' in reason:
        return 'review-failed'
    return reason or 'unknown'


def capture_committed(repo, base, head, manifest):
    names = read_git(repo, ['diff', '--no-renames', '--name-only',
                            '-z', base, head]).decode().split('\0')
    names = [name for name in names if name]
    section = {'changed_count': len(names), 'files': [], 'exclusions': [],
               'truncated': False, 'status': 'complete'}
    manifest['committed_changed_count'] = len(names)
    if len(names) > MAX_FILES:
        section['truncated'] = True
        section['status'] = 'incomplete'
        section['reason'] = 'file-count-limit'
        return section, [], b''
    files, total = [], 0
    for name in names:
        reason = excluded_path(name)
        if reason:
            section['exclusions'].append({'path': name, 'reason': reason})
            continue
        tree = read_git(repo, ['ls-tree', '-z', head, '--', name]
                        ).decode().rstrip('\0')
        if not tree:
            files.append(({'path': name, 'deleted': True}, None))
            continue
        fields, path = tree.split('\t', 1)
        mode, kind, blob = fields.split()
        if path != name or kind != 'blob' or mode not in ('100644', '100755'):
            section['exclusions'].append({'path': name,
                                          'reason': 'not-regular-source'})
            continue
        size = int(read_git(repo, ['cat-file', '-s', blob]).decode())
        if size > MAX_FILE_BYTES or total + size > MAX_SOURCE_BYTES:
            section['truncated'] = True
            section['exclusions'].append({'path': name,
                                          'reason': 'source-size-limit'})
            continue
        content = read_git(repo, ['cat-file', 'blob', blob], MAX_FILE_BYTES)
        total += len(content)
        files.append(({'path': name, 'mode': mode, 'blob_sha': blob,
                       'bytes': len(content),
                       'sha256': hashlib.sha256(content).hexdigest(),
                       'artifact': 'sources/' + name}, content))
    if section['exclusions']:
        section['status'] = 'incomplete'
        section['reason'] = 'excluded-source'
        return section, [], b''
    patch = read_git(repo, ['diff', '--no-ext-diff', '--no-textconv',
                            '--no-renames', '--binary', '--full-index',
                            base, head], MAX_PATCH_BYTES)
    if read_git(repo, ['rev-parse', 'HEAD']).decode().strip() != head:
        raise Unavailable('workspace-changed')
    section['source_bytes'] = total
    return section, [(entry, content) for entry, content in files], patch


def capture_uncommitted(repo, head, manifest):
    status = read_git(repo, ['status', '--porcelain',
                             '--untracked-files=all']).decode()
    if not status.strip():
        return {'status': 'complete', 'changed_count': 0, 'files': [],
                'exclusions': [], 'truncated': False, 'source_bytes': 0}, \
            [], b''
    # Full uncommitted patch (tracked + untracked) via a throwaway index so
    # the workspace index/HEAD is never mutated.
    tmp = tempfile.NamedTemporaryFile(delete=False)
    tmp.close()
    try:
        environment = clean_environment()
        environment.update({'GIT_CONFIG_GLOBAL': os.devnull,
                            'GIT_CONFIG_NOSYSTEM': '1',
                            'GIT_INDEX_FILE': tmp.name})
        gitdir = read_git(repo, ['rev-parse', '--git-dir']).decode().strip()
        if not os.path.isabs(gitdir):
            gitdir = os.path.join(str(repo), gitdir)
        environment['GIT_DIR'] = gitdir
        try:
            subprocess.run(['git', 'add', '-A'],
                           cwd=str(repo), env=environment,
                           stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL,
                           check=True, timeout=120)
            with tempfile.TemporaryFile() as output:
                subprocess.run(['git', 'diff', '--cached', '--no-ext-diff',
                                '--no-textconv', '--no-renames', '--binary',
                                '--full-index'],
                               cwd=str(repo), env=environment, stdout=output,
                               stderr=subprocess.DEVNULL,
                               check=True, timeout=120)
                output.seek(0)
                patch = output.read(MAX_PATCH_BYTES + 1)
                if len(patch) > MAX_PATCH_BYTES:
                    raise Unavailable('output-limit')
        except (OSError, subprocess.SubprocessError):
            raise Unavailable('git-read-failed')
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass
    names = read_git(repo, ['diff', '--no-renames', '--name-only',
                            '-z', 'HEAD']).decode().split('\0')
    untracked = read_git(repo, ['ls-files', '--others', '--exclude-standard',
                                '-z']).decode().split('\0')
    names = [n for n in names if n] + [n for n in untracked if n]
    # Deduplicate while keeping order.
    seen = set()
    ordered = []
    for name in names:
        if name not in seen:
            seen.add(name)
            ordered.append(name)
    section = {'changed_count': len(ordered), 'files': [], 'exclusions': [],
               'truncated': False, 'status': 'complete'}
    if len(ordered) > MAX_FILES:
        section.update(truncated=True, status='incomplete',
                       reason='file-count-limit')
        return section, [], b''
    files, total = [], 0
    for name in ordered:
        reason = excluded_path(name)
        if reason:
            section['exclusions'].append({'path': name, 'reason': reason})
            continue
        target = repo / name
        try:
            st = target.lstat()
        except OSError:
            files.append(({'path': name, 'deleted': True}, None))
            continue
        import stat as statmod
        if not statmod.S_ISREG(st.st_mode):
            section['exclusions'].append({'path': name,
                                          'reason': 'not-regular-source'})
            continue
        try:
            content = target.read_bytes()
        except OSError:
            raise Unavailable('snapshot-failed')
        if len(content) > MAX_FILE_BYTES or total + len(content) > MAX_SOURCE_BYTES:
            section['truncated'] = True
            section['exclusions'].append({'path': name,
                                          'reason': 'source-size-limit'})
            continue
        mode = '100755' if (st.st_mode & 0o111) else '100644'
        files.append(({'path': name, 'mode': mode,
                       'bytes': len(content),
                       'sha256': hashlib.sha256(content).hexdigest(),
                       'artifact': 'uncommitted_sources/' + name}, content))
    if section['exclusions']:
        section['status'] = 'incomplete'
        section['reason'] = 'excluded-source'
        return section, [], b''
    section['source_bytes'] = total
    return section, files, patch


def preserve(workspace, base, head, result_path, output, terminated,
             outcome, ticket, run):
    manifest = {'version': VERSION, 'status': 'unavailable',
                'ticket': ticket, 'run': run,
                'base_sha': base, 'head_sha': head,
                'termination_confirmed': terminated,
                'termination_outcome': outcome_of(result_path, outcome),
                'truncated': False, 'changed_count': 0,
                'files': [], 'exclusions': [],
                'limits': {'files': MAX_FILES, 'file_bytes': MAX_FILE_BYTES,
                           'source_bytes': MAX_SOURCE_BYTES,
                           'patch_bytes': MAX_PATCH_BYTES}}
    if not terminated:
        manifest['reason'] = 'termination-unconfirmed'
        return manifest
    if output == workspace or workspace in output.parents or output.exists():
        manifest['reason'] = 'output-not-isolated-or-new'
        return manifest
    try:
        if not all(re.fullmatch('[0-9a-f]{40}', value) for value in (base, head)):
            raise Unavailable('commit-invalid')
        actual = read_git(workspace, ['rev-parse', 'HEAD']).decode().strip()
        if actual != head:
            # Committed HEAD must match; uncommitted dirt is captured below.
            raise Unavailable('head-mismatch')
        read_git(workspace, ['merge-base', '--is-ancestor', base, head])
        committed,centries, cpatch = capture_committed(workspace, base, head,
                                                       manifest)
        uncommitted, uentries, upatch = capture_uncommitted(workspace, head,
                                                            manifest)
        manifest['committed'] = {k: v for k, v in committed.items()
                                 if k != 'reason' or 'reason' in committed}
        manifest['uncommitted'] = {k: v for k, v in uncommitted.items()
                                   if k != 'reason' or 'reason' in uncommitted}
        manifest['exclusions'] = (committed.get('exclusions', []) +
                                  uncommitted.get('exclusions', []))
        manifest['truncated'] = bool(committed.get('truncated') or
                                     uncommitted.get('truncated'))
        manifest['changed_count'] = (committed.get('changed_count', 0) +
                                     uncommitted.get('changed_count', 0))
        if committed.get('status') != 'complete' or \
                uncommitted.get('status') != 'complete':
            manifest['status'] = 'incomplete'
            manifest['reason'] = (committed.get('reason') or
                                  uncommitted.get('reason') or
                                  'excluded-source')
            return manifest
        if read_git(workspace, ['rev-parse', 'HEAD']).decode().strip() != head:
            raise Unavailable('workspace-changed')
        manifest['tree_sha'] = read_git(
            workspace, ['rev-parse', head + '^{tree}']).decode().strip()
        output.mkdir(parents=True, mode=0o700)
        for entry, content in centries:
            if content is not None:
                target = output / entry['artifact']
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(content)
                target.chmod(0o600)
            manifest['files'].append(entry)
        for entry, content in uentries:
            if content is not None:
                target = output / entry['artifact']
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(content)
                target.chmod(0o600)
            manifest['files'].append(entry)
        (output / 'candidate.patch').write_bytes(cpatch)
        (output / 'candidate.patch').chmod(0o600)
        manifest['patch'] = {'artifact': 'candidate.patch',
                             'bytes': len(cpatch),
                             'sha256': hashlib.sha256(cpatch).hexdigest()}
        (output / 'uncommitted.patch').write_bytes(upatch)
        (output / 'uncommitted.patch').chmod(0o600)
        manifest['uncommitted_patch'] = {
            'artifact': 'uncommitted.patch', 'bytes': len(upatch),
            'sha256': hashlib.sha256(upatch).hexdigest()}
        try:
            original = Path(result_path).read_bytes()
        except OSError:
            raise Unavailable('result-missing')
        (output / 'result.json').write_bytes(original)
        (output / 'result.json').chmod(0o600)
        manifest['result'] = {'artifact': 'result.json',
                              'bytes': len(original),
                              'sha256': hashlib.sha256(original).hexdigest()}
        manifest['source_bytes'] = (committed.get('source_bytes', 0) +
                                    uncommitted.get('source_bytes', 0))
        manifest['status'] = 'complete'
    except (Unavailable, OSError, ValueError, UnicodeError) as error:
        manifest['reason'] = str(error) if isinstance(error, Unavailable) \
            else 'snapshot-failed'
        if manifest['reason'] == 'output-limit':
            manifest['truncated'] = True
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=['preserve'])
    parser.add_argument('--workspace', required=True)
    parser.add_argument('--base', required=True)
    parser.add_argument('--head', required=True)
    parser.add_argument('--result', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--worker-terminated', action='store_true')
    parser.add_argument('--outcome', default='')
    parser.add_argument('--ticket', type=int, default=41)
    parser.add_argument('--run', default='unknown')
    args = parser.parse_args(argv)
    output = Path(args.output).resolve()
    manifest = preserve(Path(args.workspace).resolve(), args.base,
                        args.head, args.result, output,
                        args.worker_terminated, args.outcome or '',
                        args.ticket, args.run)
    if manifest['status'] in ('complete', 'incomplete'):
        try:
            output.mkdir(parents=True, exist_ok=True)
            (output / 'manifest.json').write_text(
                json.dumps(manifest, indent=2) + '\n')
            (output / 'manifest.json').chmod(0o600)
        except OSError:
            pass
    print(json.dumps(manifest))
    return 0 if manifest['status'] == 'complete' else 1


if __name__ == '__main__':
    sys.exit(main())
