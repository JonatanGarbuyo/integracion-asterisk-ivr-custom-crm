#!/usr/bin/python3
"""RPM scriptlets and read-only diagnostics; no remote services or call state."""
import argparse
import json
import os
import pathlib
import re
import subprocess
import sys


def command(arguments, timeout=60):
    result = subprocess.run(arguments, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            universal_newlines=True, timeout=timeout)
    if result.returncode:
        # External errors may contain database credentials. Identify only phase/tool.
        raise RuntimeError('Falló el comando '+pathlib.Path(arguments[0]).name)
    return result.stdout


class Lifecycle:
    def __init__(self, root):
        self.root = pathlib.Path(root)
        self.core = self.path('/usr/share/callflow-hooks')
        self.configuration = self.path('/etc/asterisk/callflow-hooks/profiles.conf')
        self.state = self.path('/var/lib/callflow-hooks/install-state.json')
        self.phase = 'preflight'

    def path(self, absolute):
        return self.root / absolute.lstrip('/')

    def probe(self, mode):
        script = self.core / 'pbx-state.php'
        if not script.exists():
            script = pathlib.Path(__file__).with_name('pbx-state.php')
        return json.loads(command(['php', str(script), mode, str(self.root)]))

    def preflight(self):
        if sys.version_info < (3, 6):
            raise RuntimeError('Se requiere Python >=3.6')
        command(['rpm', '-q', 'issabel-framework', 'issabelPBX'])
        for executable in ['module_admin', 'issabel-menumerge', 'issabel-menuremove', 'asterisk']:
            self.executable(executable)
        listing = command([self.executable('module_admin'), 'list'])
        if not re.search(r'^customappsreg\s+\S+\s+Enabled\s*$', listing, re.M):
            raise RuntimeError('Activar Custom Destinations antes de instalar')
        system = self.probe('preflight')
        if not system.get('php_ok'):
            raise RuntimeError('Se requiere PHP >=5.4 con openssl y proc_open')
        for key in ['user', 'web_user', 'group']:
            if not isinstance(system.get(key), str) or not re.match(r'^[a-z_][a-z0-9_-]*\$?$', system[key]):
                raise RuntimeError('Identidad de servicio inválida')
        if system['user'] == 'root' or system['web_user'] != system['user']:
            raise RuntimeError('Este paquete requiere PHP y Asterisk con el mismo usuario no root')
        processes = command(['ps', '-eo', 'user=,comm=']).splitlines()
        for name in ['asterisk', 'httpd']:
            workers = [line.split()[0] for line in processes if len(line.split()) == 2 and line.split()[1] == name and line.split()[0] != 'root']
            if not workers or set(workers) != {system['user']}:
                raise RuntimeError('Comprobar usuario efectivo del servicio '+name)
        return system

    def executable(self, name):
        # Prefer the distribution's paths; PATH is also the system boundary in tests.
        known = {'module_admin':'/var/lib/asterisk/bin/module_admin',
                 'issabel-menumerge':'/usr/bin/issabel-menumerge',
                 'issabel-menuremove':'/usr/bin/issabel-menuremove',
                 'amportal':'/usr/sbin/amportal', 'asterisk':'/usr/sbin/asterisk'}
        import shutil
        candidate = self.path(known[name])
        if candidate.is_file() and os.access(str(candidate), os.X_OK):
            return str(candidate)
        found = shutil.which(name)
        if not found:
            raise RuntimeError('Falta la herramienta '+name)
        return found

    def record(self, status):
        self.state.parent.mkdir(parents=True, exist_ok=True)
        version = json.loads((self.core / 'version.json').read_text())
        version.update(status=status, phase=self.phase)
        temporary = self.state.with_suffix('.tmp')
        temporary.write_text(json.dumps(version, sort_keys=True)+'\n')
        temporary.chmod(0o600)
        os.replace(str(temporary), str(self.state))

    def install(self):
        system = self.preflight()
        try:
            self.phase = 'configuration'
            self.record('installing')
            directory = self.configuration.parent
            directory.mkdir(parents=True, exist_ok=True)
            if directory.is_symlink() or self.configuration.is_symlink():
                raise RuntimeError('La configuración no puede ser un enlace simbólico')
            if not self.configuration.exists():
                self.configuration.touch(mode=0o600)
            directory.chmod(0o700)
            self.configuration.chmod(0o600)
            command(['chown', system['user']+':'+system['group'], str(directory), str(self.configuration)])
            lock = directory / 'profiles.conf.lock'
            if lock.exists():
                if lock.is_symlink(): raise RuntimeError('Lock de configuración inválido')
                command(['chown', system['user']+':'+system['group'], str(lock)])
            self.phase = 'pbx-module'
            self.record('installing')
            command([self.executable('module_admin'), 'install', 'callflowhooks'])
            # The PBX permission pass can widen configuration modes too.
            directory.chmod(0o700)
            self.configuration.chmod(0o600)
            command(['chown', system['user']+':'+system['group'], str(directory), str(self.configuration)])
            if lock.exists():
                lock.chmod(0o600)
                command(['chown', system['user']+':'+system['group'], str(lock)])
            # Module Administration's permission pass may assign web code to the
            # service user. Restore ownership only for this addon's code.
            command(['chown', '-R', 'root:root', str(self.core),
                     str(self.path('/var/www/html/modules/callflowhooks')),
                     str(self.path('/var/www/html/admin/modules/callflowhooks'))])
            # Same-version module_admin install can skip install.php entirely.
            self.phase = 'pbx-destinations'
            self.record('installing')
            if not self.probe('synchronize').get('ok'):
                raise RuntimeError('No se pudo validar configuración y sincronizar destinos')
            self.phase = 'native-menu'
            self.record('installing')
            command([self.executable('issabel-menumerge'), str(self.core / 'menu.xml')])
            self.phase = 'verify'
            self.record('installing')
            self.verify()
            self.phase = 'complete'
            self.record('installed')
        except Exception:
            self.record('failed')
            raise

    def verify(self):
        version = json.loads((self.core / 'version.json').read_text())
        listing = command([self.executable('module_admin'), 'list'])
        if not re.search(r'^callflowhooks\s+'+re.escape(version['version'])+r'\s+Enabled\s*$', listing, re.M):
            raise RuntimeError('El puente PBX no está habilitado con la versión instalada')
        framework = self.probe('framework')
        if not framework.get('menu') or not framework.get('acl'):
            raise RuntimeError('Falta registro de menú o ACL nativos')
        if not self.path('/var/www/html/modules/callflowhooks/index.php').is_file():
            raise RuntimeError('Falta la página nativa')
        if not self.probe('configuration').get('ok'):
            raise RuntimeError('Configuración o destinos incompletos')
        return version

    def status(self):
        version = self.verify()
        state = json.loads(self.state.read_text())
        if state.get('status') != 'installed' or any(state.get(k) != version.get(k) for k in ['version','release','commit']):
            raise RuntimeError('Instalación parcial: repetir la instalación y comprobar las fases')
        return version

    def remove(self):
        self.preflight()
        if self.probe('references').get('references'):
            raise RuntimeError('Retirar referencias a destinos CallFlow Hooks y aplicar PBX antes de desinstalar')
        channels = command([self.executable('asterisk'), '-rx', 'core show channels count'])
        if not re.search(r'^0 active channels\s*$', channels, re.M):
            raise RuntimeError('Esperar a que terminen las llamadas antes de desinstalar')
        self.phase = 'remove-pbx'
        self.record('removing')
        listing = command([self.executable('module_admin'), 'list'])
        if re.search(r'^callflowhooks\s+\S+\s+(?:Enabled|Disabled)', listing, re.M):
            command([self.executable('module_admin'), 'uninstall', 'callflowhooks'])
        # Explicit removal regenerates PBX configuration before code disappears.
        if not self.probe('reload').get('ok'):
            raise RuntimeError('No se pudo regenerar la PBX; el código se conserva, repetir desinstalación tras corregir')
        self.phase = 'remove-native-menu'
        framework = self.probe('framework')
        if framework.get('menu') or framework.get('acl'):
            command([self.executable('issabel-menuremove'), 'callflowhooks'])
        self.phase = 'removed'
        self.record('removed')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['preflight','install','status','remove'])
    parser.add_argument('--root', default='/', help='Raíz de diagnóstico/staging; RPM usa /')
    arguments = parser.parse_args()
    lifecycle = Lifecycle(arguments.root)
    try:
        if arguments.action in ['install','remove'] and os.geteuid() != 0:
            raise RuntimeError('Ejecutar como root')
        if arguments.action == 'preflight': lifecycle.preflight(); response = {'ok':True}
        elif arguments.action == 'status': response = lifecycle.status()
        else:
            getattr(lifecycle, arguments.action)()
            response = {'ok':True, 'phase':lifecycle.phase}
        print(json.dumps(response))
    except RuntimeError as error:
        print('CallFlow Hooks: fase '+lifecycle.phase+' incompleta. '+str(error), file=sys.stderr)
        return 1
    except (OSError, ValueError, KeyError, subprocess.TimeoutExpired):
        print('CallFlow Hooks: fase '+lifecycle.phase+' incompleta. Revisar dependencias, permisos y registro; repetir tras corregir.', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
