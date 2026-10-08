"""Native page -> real backend; only Issabel authentication/DB/generator are doubles."""
import json
import os
import shutil
import subprocess
import unittest

from boundary_support import AdminBoundary, ROOT
from agi_harness import call


@unittest.skipUnless(shutil.which('php'), 'PHP is required; mandatory PHP jobs run in CI')
class NativeForm(AdminBoundary, unittest.TestCase):
    def web(self, request):
        environment = dict(os.environ, CFH_TEST_CONFIG=str(self.config),
                           CFH_TEST_PYTHON=os.sys.executable)
        process = subprocess.run(['php', str(ROOT / 'tests' / 'issabel_boundary.php')],
                                 input=json.dumps(request), stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, universal_newlines=True,
                                 timeout=8, env=environment)
        self.assertEqual(process.returncode, 0, process.stderr)
        return json.loads(process.stdout)

    def test_native_form_renders_schema_registers_destinations_and_generates_entry(self):
        form = self.web({'action': 'view'})
        self.assertIn('Saludo', form['html'])
        self.assertIn('api_token', form['html'])
        version = self.request('describe')['configuration_version']
        post = dict(self.profile(), configuration_version=version, csrf_token='test-token')
        result = self.web({'action': 'save', 'post': post})
        self.assertIn('callflow-profile-welcome,s,1', result['destinations'])
        self.assertEqual(result['reloads'], 1)
        self.assertNotIn('private-token', result['html'])
        self.assertIn('Goto(${CALLFLOW_NEXT_DESTINATION})', result['dialplan'])
        self.assertIn('AGI(', result['dialplan'])
        self.assertIn('Set(CALLFLOW_NEXT_DESTINATION=ext-local,202,1)', result['dialplan'])
        variables, _, _ = call(self.config)
        self.assertEqual(variables['CALLFLOW_NEXT_DESTINATION'], 'ext-local,201,1')
        self.assertEqual(variables['CALLFLOW_CONFIGURATION_VERSION'], self.request('describe')['configuration_version'])
        self.assertEqual(json.loads(variables['CALLFLOW_CONTEXT_JSON'])['greeting'], 'Buen día')
        second = dict(self.profile('night'), configuration_version=self.request('describe')['configuration_version'],
                      csrf_token='test-token')
        result = self.web({'action': 'save', 'post': second})
        self.assertEqual(len(result['destinations']), 2)

    def test_permissions_csrf_and_invalid_save_preserve_configuration_and_registry(self):
        version = self.request('describe')['configuration_version']
        post = dict(self.profile(), configuration_version=version, csrf_token='test-token')
        denied = self.web({'action': 'save', 'denied': True, 'post': post})
        self.assertIn('Acceso denegado', denied['html'])
        self.assertFalse(self.config.exists())
        self.assertFalse(denied['destinations'])
        post['csrf_token'] = 'incorrect'
        rejected = self.web({'action': 'save', 'post': post})
        self.assertFalse(rejected['destinations'])
        self.assertFalse(self.config.exists())
        post['csrf_token'] = 'test-token'
        post['execution_budget_ms'] = 'not-a-number'
        rejected = self.web({'action': 'save', 'post': post})
        self.assertFalse(rejected['destinations'])
        self.assertFalse(self.config.exists())
        self.assertNotIn('private-token', rejected['html'])

