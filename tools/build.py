#!/usr/bin/env python3
"""Build a native Module Administration archive; never touch a live PBX."""
import argparse
import gzip
import io
import pathlib
import tarfile

parser = argparse.ArgumentParser()
parser.add_argument('--output', default='dist/callflowhooks-0.1.0.tgz')
args = parser.parse_args()
root = pathlib.Path(__file__).resolve().parents[1] / 'module'
output = pathlib.Path(args.output)
output.parent.mkdir(parents=True, exist_ok=True)
with output.open('wb') as stream:
    with gzip.GzipFile(fileobj=stream, mode='wb', mtime=0, filename='') as compressed:
        with tarfile.open(fileobj=compressed, mode='w') as archive:
            for path in sorted(root.rglob('*')):
                if not path.is_file() or '__pycache__' in path.parts:
                    continue
                data = path.read_bytes()
                info = tarfile.TarInfo('callflowhooks/' + path.relative_to(root).as_posix())
                info.size = len(data)
                info.mode = 0o755 if path.name == 'entry.py' else 0o644
                info.mtime = 0
                archive.addfile(info, io.BytesIO(data))
print(output)
