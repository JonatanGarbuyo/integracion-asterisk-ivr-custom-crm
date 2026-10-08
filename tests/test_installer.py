"""Public installer CLI with GitHub/RPM/system boundary doubles."""
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

from boundary_support import ROOT


class RepositoryInstaller(unittest.TestCase):
    def setUp(self):
        (ROOT/'artifacts').mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=str(ROOT / 'artifacts'))
        self.addCleanup(self.temp.cleanup)
        self.workspace = pathlib.Path(self.temp.name)
        self.log = self.workspace/'rpm.log'
        self.bin = self.workspace/'bin'
        self.bin.mkdir()
        self.package = b'known release RPM fixture'
        self.manifest = dict(version='0.2.0', release='1', commit='a'*40,
                             package='issabel-callflow-hooks-0.2.0-1.noarch.rpm',
                             sha256=hashlib.sha256(self.package).hexdigest())
        script = '''#!{python}
import os,pathlib,sys
with open(os.environ['RPM_LOG'],'a') as stream: stream.write(' '.join(sys.argv[1:])+'\\n')
if '-qp' in sys.argv:
 print('issabel-callflow-hooks|0.2.0|1|noarch|https://github.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm/tree/'+os.environ.get('PACKAGE_COMMIT','a'*40))
'''.format(python=sys.executable)
        (self.bin/'rpm').write_text(script)
        (self.bin/'rpm').chmod(0o755)
        control = self.bin/'callflow-hooksctl'
        control.write_text('#!'+sys.executable+'\nimport os,sys\nsys.exit(1 if os.environ.get("STATUS_FAIL") else 0)\n')
        control.chmod(0o755)
        converter = self.bin/'rpm2cpio'
        converter.write_text('#!'+sys.executable+'\nprint("package fixture")\n')
        converter.chmod(0o755)
        extract = self.bin/'cpio'
        extract.write_text('#!'+sys.executable+'\nimport pathlib,sys\nsys.stdin.read()\np=pathlib.Path("usr/share/callflow-hooks");p.mkdir(parents=True,exist_ok=True)\n(p/"lifecycle.py").write_text("print(\\"preflight fixture\\")\\n")\n')
        extract.chmod(0o755)
        self.environment = dict(os.environ, PATH=str(self.bin)+os.pathsep+os.environ['PATH'],
                                RPM_LOG=str(self.log), RELEASE_MANIFEST=json.dumps(self.manifest))
        # The external GitHub boundary is replaced; real CLI and checksums execute.
        self.launcher = self.workspace/'network_boundary.py'
        self.launcher.write_text('''import io,json,os,runpy,sys,urllib.request
def response(url,timeout=None):
 if url.endswith('/manifest.json'): return io.BytesIO(os.environ['RELEASE_MANIFEST'].encode())
 return io.BytesIO(b'known release RPM fixture')
urllib.request.urlopen=response
sys.argv=[sys.argv[1]]+sys.argv[2:]
runpy.run_path(sys.argv[0],run_name='__main__')
''')

    def install(self, prepare=True, **environment):
        arguments = [sys.executable,str(self.launcher),str(ROOT/'tools/install.py'),
                     '--release','v0.2.0','--output',str(self.workspace/'download')]
        if prepare: arguments.append('--prepare-only')
        return subprocess.run(arguments,
                              env=dict(self.environment, **environment), stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, universal_newlines=True, timeout=10)

    def test_release_download_verifies_version_commit_and_checksum_without_installing(self):
        result = self.install()
        self.assertEqual(result.returncode, 0, result.stderr)
        package = self.workspace/'download'/self.manifest['package']
        self.assertEqual(package.read_bytes(), self.package)
        self.assertNotIn('-Uvh', self.log.read_text())
        self.assertIn('a'*40, result.stdout)

    @unittest.skipUnless(os.geteuid() == 0, 'Root installation boundary runs in CI container')
    def test_install_executes_rpm_and_checks_postinstall_status(self):
        result = self.install(prepare=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('-Uvh --replacepkgs', self.log.read_text())
        self.assertTrue(json.loads(result.stdout.splitlines()[0])['installed'])
        result = self.install(prepare=False, STATUS_FAIL='1')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('instalación parcial', result.stderr)

    def test_wrong_checksum_version_or_package_commit_never_installs(self):
        bad_hash = dict(self.manifest, sha256='0'*64)
        wrong_version = dict(self.manifest, version='0.9.0')
        for environment in [{'RELEASE_MANIFEST': json.dumps(bad_hash)},
                            {'RELEASE_MANIFEST': json.dumps(wrong_version)},
                            {'PACKAGE_COMMIT': 'b'*40}]:
            result = self.install(**environment)
            self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('-Uvh', self.log.read_text())

