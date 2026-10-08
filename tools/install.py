#!/usr/bin/python3
"""Install a pinned GitHub release or a clean repository checkout."""
import argparse
import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request

REPOSITORY = 'https://github.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm'


def command(arguments, timeout=120):
    result = subprocess.run(arguments, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            universal_newlines=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError('Falló '+pathlib.Path(arguments[0]).name+'; revisar dependencias o instalación parcial')
    return result.stdout.strip()


def download(url, destination, maximum):
    with urllib.request.urlopen(url, timeout=30) as source:
        with destination.open('wb') as target:
            length = 0
            while True:
                chunk = source.read(65536)
                if not chunk: break
                length += len(chunk)
                if length > maximum: raise RuntimeError('Descarga fuera del límite')
                target.write(chunk)


def validate(manifest, directory, expected_version=None):
    if not isinstance(manifest, dict): raise RuntimeError('Manifiesto inválido')
    if not re.match(r'^[0-9]+\.[0-9]+\.[0-9]+$', manifest.get('version','')) or not re.match(r'^[0-9]+$', manifest.get('release','')):
        raise RuntimeError('Versión de manifiesto inválida')
    if expected_version is not None and manifest['version'] != expected_version:
        raise RuntimeError('El manifiesto no corresponde a la versión solicitada')
    if not re.match(r'^[a-f0-9]{40}$', manifest.get('commit','')) or not re.match(r'^[a-f0-9]{64}$', manifest.get('sha256','')):
        raise RuntimeError('Commit o checksum inválidos')
    filename = 'issabel-callflow-hooks-'+manifest['version']+'-'+manifest['release']+'.noarch.rpm'
    if manifest.get('package') != filename: raise RuntimeError('Nombre de paquete inválido')
    package = directory/filename
    if hashlib.sha256(package.read_bytes()).hexdigest() != manifest['sha256']:
        raise RuntimeError('Checksum del RPM incorrecto')
    actual = command(['rpm','-qp','--queryformat','%{NAME}|%{VERSION}|%{RELEASE}|%{ARCH}|%{URL}',str(package)])
    expected = '|'.join(['issabel-callflow-hooks',manifest['version'],manifest['release'],'noarch',REPOSITORY+'/tree/'+manifest['commit']])
    if actual != expected: raise RuntimeError('Metadatos del RPM no corresponden al manifiesto')
    return package


def checkout_revision(args):
    checkout = pathlib.Path(args.checkout).resolve()
    if not args.ref or not re.match(r'^[a-f0-9]{40}$', args.ref): raise RuntimeError('--checkout requiere --ref con el commit completo')
    if command(['git','-C',str(checkout),'rev-parse','HEAD']) != args.ref:
        raise RuntimeError('El checkout no está en el commit solicitado')
    if command(['git','-C',str(checkout),'status','--porcelain']): raise RuntimeError('El checkout debe estar limpio')
    return checkout


def prepare(args, directory):
    if args.release:
        if not re.match(r'^v[0-9]+\.[0-9]+\.[0-9]+$', args.release): raise RuntimeError('Elegir un tag vX.Y.Z explícito')
        url = REPOSITORY+'/releases/download/'+args.release+'/'
        manifest_file = directory/'manifest.json'
        download(url+'manifest.json', manifest_file, 65536)
        manifest = json.loads(manifest_file.read_text())
        if not isinstance(manifest, dict): raise RuntimeError('Manifiesto de release inválido')
        # Validate filenames before using untrusted manifest data in paths or URLs.
        filename = 'issabel-callflow-hooks-'+args.release[1:]+'-'+str(manifest.get('release',''))+'.noarch.rpm'
        if not re.match(r'^issabel-callflow-hooks-[0-9]+\.[0-9]+\.[0-9]+-[0-9]+\.noarch\.rpm$', filename) or manifest.get('package') != filename:
            raise RuntimeError('Paquete de release inválido')
        download(url+filename, directory/filename, 32*1024*1024)
        package = validate(manifest, directory, args.release[1:])
    else:
        checkout = checkout_revision(args)
        command([sys.executable,str(checkout/'tools/build-rpm.py'),'--output',str(directory)])
        manifest = json.loads((directory/'manifest.json').read_text())
        if manifest.get('commit') != args.ref: raise RuntimeError('La construcción no corresponde al commit solicitado')
        package = validate(manifest, directory)
    return manifest, package


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--release', help='Tag explícito vX.Y.Z con RPM y manifest.json publicados')
    source.add_argument('--checkout', help='Checkout limpio para construir el mismo RPM')
    parser.add_argument('--ref', help='Commit completo del checkout')
    parser.add_argument('--prepare-only', action='store_true', help='Descargar/construir y verificar sin instalar')
    parser.add_argument('--output', help='Directorio de preparación; obligatorio con --prepare-only')
    args = parser.parse_args()
    temporary = None
    try:
        if args.release and args.ref: raise RuntimeError('--ref se usa sólo con --checkout')
        if args.prepare_only and not args.output: raise RuntimeError('--prepare-only requiere --output')
        if not args.prepare_only and os.geteuid() != 0: raise RuntimeError('Ejecutar como root para instalar')
        if not shutil.which('rpm'): raise RuntimeError('El sistema requiere RPM')
        if not args.prepare_only and args.checkout:
            # Check the target before spending build time or replacing package files.
            checkout = checkout_revision(args)
            command([sys.executable,str(checkout/'packaging/lifecycle.py'),'preflight'])
        if args.output:
            directory = pathlib.Path(args.output).resolve(); directory.mkdir(parents=True, exist_ok=True)
        else:
            temporary = tempfile.TemporaryDirectory(prefix='callflow-install-'); directory = pathlib.Path(temporary.name)
        manifest, package = prepare(args, directory)
        if not args.prepare_only:
            if args.release:
                # Extract only the preflight tools from the verified package to a
                # private directory. No package files have been replaced yet.
                if not shutil.which('rpm2cpio') or not shutil.which('cpio'):
                    raise RuntimeError('Faltan rpm2cpio/cpio para comprobar la PBX antes de instalar')
                payload = directory/'payload'; payload.mkdir(exist_ok=True)
                archive = directory/'payload.cpio'
                with archive.open('wb') as stream:
                    subprocess.check_call(['rpm2cpio',str(package)],stdout=stream)
                with archive.open('rb') as stream:
                    subprocess.check_call(['cpio','-id','--no-absolute-filenames',
                                           './usr/share/callflow-hooks/lifecycle.py','./usr/share/callflow-hooks/pbx-state.php'],
                                          stdin=stream,cwd=str(payload),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                command([sys.executable,str(payload/'usr/share/callflow-hooks/lifecycle.py'),'preflight'])
            command(['rpm','-Uvh','--replacepkgs',str(package)])
            command(['callflow-hooksctl','status'])
        print(json.dumps(dict(manifest, installed=not args.prepare_only), sort_keys=True))
        if not args.prepare_only: print('Abrir PBX → CallFlow Hooks. Revisar destinos y aplicar configuración desde PBX.')
    except (RuntimeError, OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        print('No se completó la instalación: '+(str(error) if isinstance(error,RuntimeError) else 'error de descarga, formato o herramienta'),file=sys.stderr)
        return 1
    finally:
        if temporary: temporary.cleanup()
    return 0


if __name__ == '__main__':
    sys.exit(main())
