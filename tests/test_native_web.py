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
        if hasattr(self, 'core'):
            environment['CFH_TEST_CORE'] = str(self.core)
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

    def test_invalid_save_keeps_draft_on_error_and_reload_and_can_be_corrected(self):
        post = dict(self.profile(), csrf_token='test-token',
                    configuration_version=self.request('describe')['configuration_version'])
        post['next_destination'] = '201'
        post['settings']['style'] = 'breve'
        result = self.web(action='save', bootstrap=True, post=post)
        self.assertIn('contexto,extensión,prioridad', result['html'])
        for html in [result['html'], self.web(action='view', bootstrap=True)['html']]:
            self.assertIn('name="identifier" value="welcome"', html)
            self.assertIn('name="next_destination" value="201"', html)
            self.assertIn('value="breve" selected', html)
            self.assertIn('Guardar perfil', html)
            self.assertIn('Descartar borrador', html)
            self.assertNotIn('private-token', html)
        self.assertFalse(self.config.exists())
        self.assertFalse(result['destinations'])
        self.assertNotIn('private-token', self.config.with_suffix('.conf.session').read_text())
        post['next_destination'] = 'ext-local,201,1'
        saved = self.web(action='save', post=post, bootstrap=True)
        self.assertIn('Perfil guardado', saved['html'])
        self.assertIn('callflow-profile-welcome,s,1', saved['destinations'])
        self.assertEqual(self.request('describe')['profiles'][0]['settings']['style'], 'breve')

    def test_discard_draft_does_not_change_configuration(self):
        version = self.request('describe')['configuration_version']
        post = dict(self.profile(), csrf_token='test-token', configuration_version=version)
        post['execution_budget_ms'] = 'bad'
        result = self.web(action='save', post=post)
        self.assertIn('número entero', result['html'])
        self.assertIn('name="execution_budget_ms" value="bad"', result['html'])
        result = self.web(action='save', post={'discard_draft':'1','csrf_token':'test-token'})
        self.assertNotIn('value="bad"', result['html'])
        self.assertNotIn('Descartar borrador', self.web(action='view')['html'])
        self.assertEqual(self.request('describe')['configuration_version'], version)

    def test_stale_save_reports_conflict_and_preserves_existing_secret(self):
        version = self.request('describe')['configuration_version']
        self.request('save', profile=self.profile(), expected_version=version)
        before = self.config.read_bytes()
        post = dict(self.profile(), csrf_token='test-token', configuration_version=version)
        post['settings']['greeting'] = 'Saludo pendiente'
        post['settings']['api_token'] = 'new-private-token'
        result = self.web(action='save', post=post)
        self.assertIn('configuración cambió', result['html'])
        self.assertIn('Saludo pendiente', result['html'])
        self.assertIn('Volvé a ingresar', result['html'])
        self.assertNotIn('new-private-token', result['html'])
        self.assertNotIn('new-private-token', self.config.with_suffix('.conf.session').read_text())
        self.assertEqual(self.config.read_bytes(), before)
        self.assertIn('readonly', self.web(action='view')['html'])

    @unittest.skipIf(os.geteuid() == 0, 'Permission boundary requires nonroot PHP CI runner')
    def test_write_permission_failure_keeps_draft_and_valid_configuration(self):
        self.request('save', profile=self.profile(), expected_version=self.request('describe')['configuration_version'])
        self.web(action='view')
        before = self.config.read_bytes()
        post = dict(self.profile(), csrf_token='test-token',
                    configuration_version=self.request('describe')['configuration_version'])
        post['settings']['greeting'] = 'Texto conservado'
        self.addCleanup(self.config.parent.chmod, 0o700)
        self.config.parent.chmod(0o500)
        result = self.web(action='save', post=post)
        self.assertIn('permisos', result['html'])
        self.assertIn('Texto conservado', result['html'])
        self.assertIn('Guardar perfil', result['html'])
        self.assertEqual(self.config.read_bytes(), before)

    def test_synchronize_from_empty_new_form_bypasses_browser_required_fields(self):
        self.request('save', profile=self.profile(), expected_version=self.request('describe')['configuration_version'])
        form = self.web(action='view', get={'new':'1'})['html']
        self.assertRegex(form, r'<button[^>]*name="synchronize"[^>]*formnovalidate')
        result = self.web(action='save', post={'synchronize':'1','csrf_token':'test-token'})
        self.assertIn('callflow-profile-welcome,s,1', result['destinations'])
        self.assertIn('Destinos sincronizados', result['html'])

    def test_extension_field_error_accepts_schema_names_with_uppercase(self):
        import pathlib
        self.core = pathlib.Path(self.directory.name)/'core'
        self.core.mkdir()
        shutil.copytree(str(ROOT/'module/backend'), str(self.core/'backend'))
        shutil.copytree(str(ROOT/'module/extensions'), str(self.core/'extensions'))
        self.extensions = self.core/'extensions'
        manifest = self.extensions/'example/manifest.json'
        schema = json.loads(manifest.read_text())
        schema['fields']['customerName'] = {'type':'string','label':'Nombre de cliente','default':'','required':True,'max_length':80}
        manifest.write_text(json.dumps(schema))
        post = dict(self.profile(), csrf_token='test-token', configuration_version=self.request('describe')['configuration_version'])
        result = self.web(action='save', post=post)
        self.assertIn('Nombre de cliente: Campo obligatorio.', result['html'])
        self.assertFalse(self.config.exists())
