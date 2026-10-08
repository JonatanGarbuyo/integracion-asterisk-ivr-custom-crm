"""Build and inspect the distributable RPM through its public interfaces."""
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

from boundary_support import ROOT


@unittest.skipUnless(shutil.which('rpmbuild') and shutil.which('rpm'), 'RPM tools required in package CI')
class NativePackage(unittest.TestCase):
    def test_rpm_contains_native_module_bridge_shared_runtime_and_pinned_metadata(self):
        (ROOT/'artifacts').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=str(ROOT/'artifacts')) as directory:
            work = pathlib.Path(directory)
            checkout = work/'checkout'
            checkout.mkdir()
            for path in ['module','native','packaging','tools']:
                shutil.copytree(str(ROOT/path),str(checkout/path),ignore=shutil.ignore_patterns('__pycache__'))
            (checkout/'.gitignore').write_text('dist/\n')
            subprocess.check_call(['git','init','-q',str(checkout)])
            subprocess.check_call(['git','-C',str(checkout),'add','.'])
            subprocess.check_call(['git','-C',str(checkout),'-c','user.name=Package test',
                                   '-c','user.email=package@example.invalid','commit','-qm','package fixture'])
            commit = subprocess.check_output(['git','-C',str(checkout),'rev-parse','HEAD'],universal_newlines=True).strip()
            output = work/'rpm'
            result = subprocess.run([sys.executable,str(checkout/'tools/build-rpm.py'),'--output',str(output)],
                                    stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=90)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            manifest = json.loads((output/'manifest.json').read_text())
            self.assertEqual(manifest['commit'],commit)
            package = output/manifest['package']
            listing = subprocess.check_output(['rpm','-qpl',str(package)],universal_newlines=True)
            for path in ['/var/www/html/modules/callflowhooks/index.php',
                         '/var/www/html/admin/modules/callflowhooks/functions.inc.php',
                         '/usr/share/callflow-hooks/backend/entry.py',
                         '/usr/share/callflow-hooks/menu.xml', '/usr/share/callflow-hooks/version.json']:
                self.assertIn(path,listing)
            self.assertNotIn('/var/www/html/admin/modules/callflowhooks/backend/',listing)
            scripts = subprocess.check_output(['rpm','-qp','--scripts',str(package)],universal_newlines=True)
            self.assertIn('lifecycle.py install',scripts)
            self.assertIn('lifecycle.py remove',scripts)
            # Run the user's checkout preparation command against the real RPM.
            result = subprocess.run([sys.executable,str(checkout/'tools/install.py'),'--checkout',str(checkout),
                                     '--ref',commit,'--prepare-only','--output',str(work/'prepared')],
                                    stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=90)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(json.loads(result.stdout)['commit'],commit)
