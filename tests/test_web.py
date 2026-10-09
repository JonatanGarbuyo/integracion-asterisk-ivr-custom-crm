"""IssabelPBX page -> real backend; authentication/DB/generator are doubles."""
import json
import os
import shutil
import subprocess
import unittest

from boundary_support import AdminBoundary, ROOT
from agi_harness import call


@unittest.skipUnless(shutil.which('php'), 'PHP is required; mandatory PHP jobs run in CI')
class PBXForm(AdminBoundary, unittest.TestCase):
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


    def test_embedded_navigation_create_update_and_runtime(self):
        import xml.etree.ElementTree as ET
        metadata = ET.parse(str(ROOT/'module/module.xml')).getroot()
        self.assertEqual(metadata.findtext('embedcategory'), 'Inbound Call Control')
        form = self.web({'action':'view', 'surface':'embedded'})['html']
        self.assertIn('class="rnav"', form)
        self.assertIn('class="popover-form"', form)
        self.assertIn('action="index.php?menu=pbxadmin', form)
        self.assertIn('name="display" value="callflowhooks"', form)
        post = dict(self.profile(), configuration_version=self.request('describe')['configuration_version'], csrf_token='test-token')
        created = self.web({'action':'save', 'surface':'embedded', 'post':post})
        self.assertIn('Custom Destinations', created['html'])
        self.assertEqual(created['reloads'], 1)
        listing = self.web({'action':'view', 'surface':'embedded'})['html']
        self.assertIn('Nuevo perfil', listing)
        self.assertNotIn('name="identifier"', listing)
        edit = self.web({'action':'view', 'surface':'embedded', 'get':{'profile':'welcome'}})['html']
        self.assertIn('id="current"', edit)
        self.assertIn('Editar perfil: welcome', edit)
        self.assertIn('<table>', edit)
        post['configuration_version'] = self.request('describe')['configuration_version']
        post['next_destination'] = 'ext-local,203,1'
        post['settings']['api_token'] = ''
        updated = self.web({'action':'save', 'surface':'embedded', 'post':post})
        self.assertIn('Perfil actualizado', updated['html'])
        self.assertNotIn('En el IVR, seleccionar', updated['html'])
        self.assertEqual(updated['reloads'], 1)
        variables, _, _ = call(self.config)
        self.assertEqual(variables['CALLFLOW_NEXT_DESTINATION'], 'ext-local,203,1')
        self.assertNotIn('private-token', updated['html'])

    def test_embedded_framework_privilege_and_invalid_draft(self):
        post = dict(self.profile(), configuration_version=self.request('describe')['configuration_version'], csrf_token='test-token')
        for post_dispatch in (False, True):
            denied = self.web({'action':'save','surface':'embedded','framework_denied':True,
                               'post_dispatch':post_dispatch,'post':post})
            self.assertIn('Acceso denegado', denied['html'])
            self.assertFalse(self.config.exists())
            self.assertFalse(denied['destinations'])
        post['next_destination'] = '201'
        failed = self.web({'action':'save','surface':'embedded','post':post})
        self.assertIn('contexto,extensión,prioridad', failed['html'])
        restored = self.web({'action':'view','surface':'embedded'})['html']
        self.assertIn('name="next_destination" value="201"', restored)
        self.assertIn('menu=pbxadmin', restored)
        self.assertNotIn('private-token', restored)
        self.assertFalse(self.config.exists())

    def test_framework_identity_cannot_bypass_acl_via_unembedded_page(self):
        post = dict(self.profile(), configuration_version=self.request('describe')['configuration_version'], csrf_token='test-token')
        # AMP_user still permits all sections as in the Issabel 4 wrapper.
        for rejected in ({'framework_denied':True}, {'missing_framework_acl':True}):
            result = self.web(dict(action='save', surface='framework_direct', post=post, **rejected))
            self.assertIn('Acceso denegado', result['html'])
            self.assertFalse(self.config.exists())
            self.assertFalse(result['destinations'])
        allowed = self.web({'action':'save','surface':'framework_direct','post':post})
        self.assertIn('callflow-profile-welcome,s,1', allowed['destinations'])
        self.assertIn('action="config.php?display=callflowhooks', allowed['html'])
