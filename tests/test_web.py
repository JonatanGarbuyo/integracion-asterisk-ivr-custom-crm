"""Native page -> real backend; only Issabel authentication/DB/generator are doubles."""
import json
import os
import shutil
import subprocess
import unittest

from test_admin import Administration, ROOT


@unittest.skipUnless(shutil.which('php'), 'PHP is required; mandatory PHP jobs run in CI')
class NativeForm(Administration):
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
        second = dict(self.profile('night'), configuration_version=self.request('describe')['configuration_version'],
                      csrf_token='test-token')
        result = self.web({'action': 'save', 'post': second})
        self.assertEqual(len(result['destinations']), 2)

