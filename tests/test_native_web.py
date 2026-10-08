"""Native Issabel entry -> backend -> real AGI; framework/DB are boundary doubles."""
import json
import os
import shutil
import subprocess
import unittest

from boundary_support import AdminBoundary, ROOT
from agi_harness import call


@unittest.skipUnless(shutil.which('php'), 'PHP required in CI')
class IssabelForm(AdminBoundary, unittest.TestCase):
    def web(self, **request):
        request['surface'] = 'native'
        environment = dict(os.environ, CFH_TEST_CONFIG=str(self.config), CFH_TEST_PYTHON=os.sys.executable)
        result = subprocess.run(['php', str(ROOT / 'tests/issabel_boundary.php')],
                                input=json.dumps(request), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                universal_newlines=True, env=environment, timeout=8)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_native_form_routes_and_saves_profile_used_by_ivr(self):
        form = self.web(action='view', bootstrap=True)
        self.assertIn('index.php?menu=callflowhooks', form['html'])
        self.assertNotIn('config.php?display=', form['html'])
        post = dict(self.profile(), csrf_token='test-token',
                    configuration_version=self.request('describe')['configuration_version'])
        saved = self.web(action='save', post=post, bootstrap=True)
        self.assertIn('callflow-profile-welcome,s,1', saved['destinations'])
        self.assertIn('Aplicar', saved['html'])
        variables, _, _ = call(self.config)
        self.assertEqual(variables['CALLFLOW_NEXT_DESTINATION'], 'ext-local,201,1')
        self.assertNotIn('private-token', saved['html'])
        edit = self.web(action='view', get={'profile': 'welcome'})
        self.assertIn('readonly', edit['html'])

    def test_native_acl_session_and_csrf_reject_without_saving(self):
        post = dict(self.profile(), csrf_token='test-token',
                    configuration_version=self.request('describe')['configuration_version'])
        for rejected in ({'denied': True}, {'invalid_session': True}):
            result = self.web(action='save', post=post, **rejected)
            self.assertIn('Acceso denegado', result['html'])
            self.assertFalse(result['destinations'])
            self.assertFalse(self.config.exists())
        post['csrf_token'] = 'bad'
        result = self.web(action='save', post=post)
        self.assertIn('Formulario vencido', result['html'])
        self.assertFalse(self.config.exists())

    def test_bootstrap_failure_is_safe_and_does_not_save(self):
        result = self.web(action='view', bootstrap=True, bootstrap_failure=True)
        self.assertIn('PBX', result['html'])
        self.assertNotIn('database-private-password', result['html'])
        self.assertFalse(self.config.exists())
        self.assertFalse(result['destinations'])
