#!/usr/bin/env python3
"""Install/apply/remove our addon, preserving generated and foreign configuration."""
import argparse
import grp
import os
from pathlib import Path
import pwd
import shutil
import stat
import sys
import tempfile

SOURCE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE_ROOT))
from issabel_crm.config import ConfigError, read_config
from issabel_crm.dialplan import render

BEGIN = '; BEGIN issabel-crm managed include\n'
END = '; END issabel-crm managed include\n'
BLOCK = BEGIN + '#include issabel_crm_extensions.conf\n' + END


def target(root, path):
    return root / path.lstrip('/')


def ownership(path, root, runtime=False):
    if root == Path('/'):
        account = pwd.getpwnam('asterisk')
        group = grp.getgrnam('asterisk')
        os.chown(str(path), account.pw_uid if runtime else 0, group.gr_gid)


def atomic_write(path, content, mode=0o640):
    path.parent.mkdir(parents=True, exist_ok=True)
    previous = path.stat() if path.exists() else None
    fd, temporary = tempfile.mkstemp(prefix='.' + path.name + '-', dir=str(path.parent))
    try:
        with os.fdopen(fd, 'wb') as output:
            output.write(content.encode('utf-8') if isinstance(content, str) else content)
            output.flush()
            os.fsync(output.fileno())
            os.fchmod(output.fileno(), stat.S_IMODE(previous.st_mode) if previous else mode)
            if previous:
                os.fchown(output.fileno(), previous.st_uid, previous.st_gid)
        os.replace(temporary, str(path))
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def include(root, enabled):
    path = target(root, '/etc/asterisk/extensions_custom.conf')
    text = path.read_text() if path.exists() else ''
    if text.count(BEGIN) != text.count(END) or text.count(BEGIN) > 1:
        raise ConfigError('Managed include markers are damaged')
    if BEGIN in text:
        start = text.index(BEGIN)
        end = text.index(END, start) + len(END)
        text = text[:start] + text[end:]
    if enabled:
        if '#include issabel_crm_extensions.conf' in text:
            raise ConfigError('Unmanaged addon include already exists')
        text += ('' if not text or text.endswith('\n') else '\n') + BLOCK
    atomic_write(path, text)
    ownership(path, root)


def install(root):
    if root == Path('/'):
        # Fail before writing if the PBX account/runtime is missing.
        pwd.getpwnam('asterisk')
        grp.getgrnam('asterisk')
    config_path = target(root, '/etc/asterisk/issabel_crm.conf')
    config_source = config_path if config_path.exists() else SOURCE_ROOT / 'config/issabel_crm.conf.example'
    config = read_config(str(config_source))
    # Check include ownership before modifying files.
    custom = target(root, '/etc/asterisk/extensions_custom.conf')
    current = custom.read_text() if custom.exists() else ''
    if current.count(BEGIN) != current.count(END) or current.count(BEGIN) > 1:
        raise ConfigError('Managed include markers are damaged')
    if '#include issabel_crm_extensions.conf' in current and BEGIN not in current:
        raise ConfigError('Unmanaged addon include already exists')
    library = target(root, '/usr/lib/issabel-crm')
    for source in (SOURCE_ROOT / 'issabel_crm').glob('*.py'):
        atomic_write(library / 'issabel_crm' / source.name, source.read_bytes(), 0o644)
    atomic_write(library / 'addon.py', Path(__file__).read_bytes(), 0o755)
    for source in (SOURCE_ROOT / 'bin').glob('*.agi'):
        path = target(root, '/var/lib/asterisk/agi-bin') / source.name
        atomic_write(path, source.read_bytes(), 0o755)
        ownership(path, root)
    for name in ('issabel_crm.conf', 'issabel_crm_secrets.conf'):
        path = target(root, '/etc/asterisk') / name
        if not path.exists():
            atomic_write(path, (SOURCE_ROOT / 'config' / (name + '.example')).read_bytes())
        ownership(path, root)
    # Default runtime dir is recreated on reboot by systemd-tmpfiles.
    tmpfiles = target(root, '/usr/lib/tmpfiles.d/issabel-crm.conf')
    atomic_write(tmpfiles, 'd /run/issabel-crm 0750 asterisk asterisk -\n', 0o644)
    enable(root, config)


def enable(root, config=None):
    config = config or read_config(str(target(root, '/etc/asterisk/issabel_crm.conf')))
    dialplan = target(root, '/etc/asterisk/issabel_crm_extensions.conf')
    atomic_write(dialplan, render(config))
    ownership(dialplan, root)
    runtime = target(root, config['runtime_dir'])
    if not runtime.exists():
        runtime.mkdir(parents=True, mode=0o750)
        ownership(runtime, root, runtime=True)
    for name in ('issabel_crm.conf', 'issabel_crm_secrets.conf'):
        path = target(root, '/etc/asterisk') / name
        ownership(path, root)
        os.chmod(str(path), 0o640)
    include(root, True)


def apply(root, candidate):
    content = candidate.read_bytes()
    config = read_config(text=content.decode('utf-8'))
    config_path = target(root, '/etc/asterisk/issabel_crm.conf')
    dialplan = target(root, '/etc/asterisk/issabel_crm_extensions.conf')
    # Validate all input before replacing either file. Config replacement is atomic.
    text = render(config)
    atomic_write(config_path, content)
    ownership(config_path, root)
    os.chmod(str(config_path), 0o640)
    atomic_write(dialplan, text)
    ownership(dialplan, root)


def uninstall(root):
    include(root, False)
    for name in ('issabel-crm-identify.agi', 'issabel-crm-answer.agi'):
        path = target(root, '/var/lib/asterisk/agi-bin') / name
        if path.exists():
            path.unlink()
    library = target(root, '/usr/lib/issabel-crm')
    if library.exists():
        shutil.rmtree(str(library))
    for path in ('/etc/asterisk/issabel_crm_extensions.conf', '/usr/lib/tmpfiles.d/issabel-crm.conf'):
        file = target(root, path)
        if file.exists():
            file.unlink()
    # Keep maps, secrets, and lock files. No other PBX configuration is removed.


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=('install', 'apply', 'validate', 'uninstall', 'enable', 'disable'))
    parser.add_argument('--root', type=Path, default=Path('/'))
    parser.add_argument('--config', type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    try:
        if args.action in ('validate', 'apply') and not args.config:
            parser.error('--config is required')
        if args.action == 'install':
            install(root)
        elif args.action == 'enable':
            enable(root)
        elif args.action == 'disable':
            include(root, False)
        elif args.action == 'uninstall':
            uninstall(root)
        elif args.action == 'apply':
            apply(root, args.config)
        else:
            read_config(str(args.config))
        print('OK: ' + args.action + '. Reload Asterisk after dialplan changes.')
    except (ConfigError, OSError, KeyError, UnicodeError):
        print('ERROR: invalid configuration, missing dependency or filesystem failure.', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
