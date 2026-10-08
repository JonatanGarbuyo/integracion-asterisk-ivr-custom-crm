"""RPM lifecycle CLI; Issabel/system executables are boundary doubles."""
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

from boundary_support import ROOT


class PackageLifecycle(unittest.TestCase):
    def setUp(self):
        (ROOT/'artifacts').mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=str(ROOT / 'artifacts'))
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name)
        self.bin = self.root / 'bin'
        self.bin.mkdir()
        self.log = self.root / 'commands.jsonl'
        self.state = self.root / 'boundary.json'
        self.state.write_text(json.dumps({'enabled': False, 'menu': False, 'acl': False}))
        self.configuration = self.root / 'etc/asterisk/callflow-hooks/profiles.conf'
        self.configuration.parent.mkdir(parents=True)
        self.configuration.write_text('; preserve-existing-credential\n')
        core = self.root / 'usr/share/callflow-hooks'
        core.mkdir(parents=True)
        (core / 'version.json').write_text(json.dumps({'version':'0.2.0', 'release':'1', 'commit':'a'*40}))
        native = self.root / 'var/www/html/modules/callflowhooks'
        native.mkdir(parents=True)
        (native / 'index.php').write_text('native fixture')
        (core / 'menu.xml').write_text((ROOT / 'native/menu.xml').read_text())
        script = '''#!{python}
import json,os,pathlib,sys
name=pathlib.Path(sys.argv[0]).name
state=pathlib.Path(os.environ['BOUNDARY_STATE'])
data=json.loads(state.read_text())
with open(os.environ['BOUNDARY_LOG'],'a') as stream: stream.write(json.dumps([name]+sys.argv[1:])+'\\n')
if name=='rpm': print('4.0.0\\n2.11.0')
elif name=='ps': print('asterisk httpd\\nasterisk asterisk\\nroot httpd')
elif name=='php':
 if 'framework' in sys.argv: print(json.dumps({{'menu':data['menu'],'acl':data['acl']}}))
 elif 'reload' in sys.argv: print(json.dumps({{'ok':not bool(os.environ.get('BOUNDARY_RELOAD_FAIL'))}}))
 elif 'synchronize' in sys.argv:
  data['destinations']=not bool(os.environ.get('BOUNDARY_INVALID_CONFIG'))
  print(json.dumps({{'ok':data['destinations']}}))
 elif 'configuration' in sys.argv: print(json.dumps({{'ok':data.get('destinations',False) and not bool(os.environ.get('BOUNDARY_INVALID_CONFIG'))}}))
 else: print(json.dumps({{'user':'asterisk','group':'asterisk','web_user':'asterisk','php_ok':True,'references':bool(os.environ.get('BOUNDARY_REFERENCES'))}}))
elif name=='module_admin':
 if sys.argv[1]=='list':
  print('customappsreg 2.11.0 Enabled')
  if data['enabled']: print('callflowhooks 0.2.0 Enabled')
 elif sys.argv[1]=='install':
  if not data['enabled']:
   data['enabled']=True
   pathlib.Path(os.environ['BOUNDARY_CONFIG']).chmod(0o644)
 elif sys.argv[1]=='uninstall': data['enabled']=False
elif name=='issabel-menumerge':
 if os.environ.get('BOUNDARY_MENU_FAIL'): sys.exit(1)
 data['menu']=True; data['acl']=True
elif name=='issabel-menuremove':
 if sys.argv[1]!='callflowhooks': sys.exit(1)
 data['menu']=False; data['acl']=False
elif name=='asterisk': print('0 active channels\\n0 active calls')
state.write_text(json.dumps(data))
'''.format(python=sys.executable)
        for name in ['rpm','ps','php','chown','module_admin','issabel-menumerge','issabel-menuremove','asterisk','amportal']:
            executable = self.bin / name
            executable.write_text(script)
            executable.chmod(0o755)
        self.environment = dict(os.environ, PATH=str(self.bin)+os.pathsep+os.environ['PATH'],
                                BOUNDARY_STATE=str(self.state), BOUNDARY_LOG=str(self.log),
                                BOUNDARY_CONFIG=str(self.configuration))

    def lifecycle(self, action, **environment):
        return subprocess.run([sys.executable, str(ROOT / 'packaging/lifecycle.py'), action, '--root', str(self.root)],
                              env=dict(self.environment, **environment), stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, universal_newlines=True, timeout=15)

    def test_install_and_reinstall_register_native_menu_and_preserve_configuration(self):
        original = self.configuration.read_bytes()
        for _ in range(2):
            result = self.lifecycle('install')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(self.configuration.read_bytes(), original)
            self.assertEqual(self.configuration.stat().st_mode & 0o777, 0o600)
            self.assertNotIn('preserve-existing-credential', result.stdout+result.stderr)
        state = json.loads(self.state.read_text())
        self.assertTrue(state['enabled'] and state['menu'] and state['acl'])
        result = self.lifecycle('status')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['commit'], 'a'*40)

    def test_partial_menu_failure_is_reported_and_can_be_repaired(self):
        result = self.lifecycle('install', BOUNDARY_MENU_FAIL='1')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('native-menu', result.stderr)
        self.assertNotEqual(self.lifecycle('status').returncode, 0)
        self.assertEqual(self.configuration.read_text(), '; preserve-existing-credential\n')
        result = self.lifecycle('install')
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_reinstall_repairs_destinations_even_when_module_install_is_skipped(self):
        self.assertEqual(self.lifecycle('install').returncode, 0)
        state = json.loads(self.state.read_text())
        state['destinations'] = False
        self.state.write_text(json.dumps(state))
        self.assertNotEqual(self.lifecycle('status').returncode, 0)
        result = self.lifecycle('install')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(json.loads(self.state.read_text())['destinations'])
        result = self.lifecycle('install', BOUNDARY_INVALID_CONFIG='1')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('pbx-destinations', result.stderr)
        self.assertNotEqual(self.lifecycle('status').returncode, 0)

    def test_remove_rejects_ivr_references_then_preserves_profiles(self):
        self.assertEqual(self.lifecycle('install').returncode, 0)
        original = self.configuration.read_bytes()
        result = self.lifecycle('remove', BOUNDARY_REFERENCES='1')
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(json.loads(self.state.read_text())['enabled'])
        result = self.lifecycle('remove')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.configuration.read_bytes(), original)
        state = json.loads(self.state.read_text())
        self.assertFalse(state['menu'] or state['enabled'] or state['acl'])

    def test_failed_pbx_reload_blocks_removal_and_can_be_retried(self):
        self.assertEqual(self.lifecycle('install').returncode, 0)
        result = self.lifecycle('remove', BOUNDARY_RELOAD_FAIL='1')
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(json.loads(self.state.read_text())['menu'])
        result = self.lifecycle('remove')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(json.loads(self.state.read_text())['menu'])
