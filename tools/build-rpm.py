#!/usr/bin/python3
"""Build the same noarch RPM for releases and repository checkouts."""
import argparse
import gzip
import hashlib
import io
import json
import pathlib
import re
import shutil
import subprocess
import tarfile
import tempfile


def build(output):
    repository = pathlib.Path(__file__).resolve().parents[1]
    if not shutil.which('rpmbuild'):
        raise RuntimeError('Falta rpmbuild; instalar herramientas de construcción en el laboratorio')
    version = json.loads((repository / 'packaging/version.json').read_text())
    if subprocess.check_output(['git','-C',str(repository),'status','--porcelain'], universal_newlines=True).strip():
        raise RuntimeError('El repositorio debe estar limpio para identificar el RPM por commit')
    commit = subprocess.check_output(['git','-C',str(repository),'rev-parse','HEAD'], universal_newlines=True).strip()
    if not re.match(r'^[a-f0-9]{40}$', commit): raise RuntimeError('Commit inválido')
    version['commit'] = commit
    output = pathlib.Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=str(output)) as directory:
        workspace = pathlib.Path(directory)
        sources = workspace / 'SOURCES'
        sources.mkdir()
        archive = sources / ('callflow-hooks-'+version['version']+'.tar.gz')
        prefix = 'callflow-hooks-'+version['version']+'/'
        with archive.open('wb') as stream:
            with gzip.GzipFile(fileobj=stream, mode='wb', filename='', mtime=0) as zipped:
                with tarfile.open(fileobj=zipped, mode='w') as packed:
                    for top in ['module','native','packaging']:
                        for path in sorted((repository/top).rglob('*')):
                            if not path.is_file() or '__pycache__' in path.parts: continue
                            info = tarfile.TarInfo(prefix+path.relative_to(repository).as_posix())
                            data = path.read_bytes(); info.size = len(data); info.mode = 0o644
                            packed.addfile(info, io.BytesIO(data))
                    data = (json.dumps(version, sort_keys=True)+'\n').encode()
                    info = tarfile.TarInfo(prefix+'version.json'); info.size = len(data); info.mode = 0o644
                    packed.addfile(info, io.BytesIO(data))
        subprocess.check_call(['rpmbuild','-bb',str(repository/'packaging/callflow-hooks.spec'),
                               '--define','_topdir '+str(workspace), '--define','_binary_payload w9.gzdio',
                               '--define','cfh_version '+version['version'], '--define','cfh_release '+version['release'],
                               '--define','cfh_commit '+commit])
        packages = list((workspace/'RPMS/noarch').glob('*.rpm'))
        if len(packages) != 1: raise RuntimeError('Construcción RPM ambigua')
        package = output/packages[0].name
        shutil.copyfile(str(packages[0]), str(package))
    manifest = dict(version, package=package.name, sha256=hashlib.sha256(package.read_bytes()).hexdigest())
    (output/'manifest.json').write_text(json.dumps(manifest, sort_keys=True, indent=2)+'\n')
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='dist/rpm')
    args = parser.parse_args()
    try:
        print(json.dumps(build(args.output)))
    except (RuntimeError, OSError, ValueError, subprocess.CalledProcessError) as error:
        parser.exit(1, 'No se pudo construir el RPM: '+str(error)+'\n')
