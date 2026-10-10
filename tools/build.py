#!/usr/bin/env python3
"""Build a dependency-free addon tarball and its SHA-256 checksum."""
import argparse
import gzip
import hashlib
import io
from pathlib import Path
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from issabel_crm import __version__


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=ROOT / 'dist')
    options = parser.parse_args()
    options.output.mkdir(parents=True, exist_ok=True)
    name = 'issabel-crm-' + __version__
    archive = options.output / (name + '.tar.gz')
    files = []
    for folder in ('issabel_crm', 'bin', 'config', 'tools', 'lab', 'tests', 'packaging'):
        files += [p for p in (ROOT / folder).rglob('*')
                  if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc']
    files += [ROOT / 'README.md', ROOT / 'docs/naming.md']
    files += list((ROOT / 'docs/testing').glob('*.md'))
    with open(str(archive), 'wb') as output:
        with gzip.GzipFile(filename='', fileobj=output, mode='wb', mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode='w') as tar:
                for path in sorted(files):
                    content = path.read_bytes()
                    info = tarfile.TarInfo(name + '/' + str(path.relative_to(ROOT)))
                    info.size = len(content)
                    info.mode = 0o755 if path.parent.name == 'bin' else 0o644
                    info.mtime = 0
                    tar.addfile(info, io.BytesIO(content))
    checksum = hashlib.sha256(archive.read_bytes()).hexdigest()
    (options.output / (name + '.tar.gz.sha256')).write_text(checksum + '  ' + archive.name + '\n')
    print(str(archive))


if __name__ == '__main__':
    main()
