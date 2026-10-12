"""Profile management/localization through the real PHP -> JSON process boundary."""
import json
import os
import re
import shutil
import subprocess
import unittest
from boundary_support import UIProfileBoundary, ROOT


@unittest.skipUnless(shutil.which('php'), 'PHP required in native-form CI')
class ProfileManagement(UIProfileBoundary, unittest.TestCase):
    def web(self, language='en_US', **request):
        environment = dict(os.environ, CFH_TEST_CONFIG=str(self.config), CFH_TEST_PYTHON=os.sys.executable)
        result = subprocess.run(['php',str(ROOT/'tests/issabel_boundary.php')], input=json.dumps(dict(language=language,**request)),
                                stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,env=environment,timeout=8)
        self.assertEqual(result.returncode,0,result.stderr)
        return json.loads(result.stdout)

    def post(self):
        return dict(self.profile(),csrf_token='test-token',configuration_version=self.request('describe')['configuration_version'])

    def saved(self):
        return self.web(action='save',post=self.post())

    def deletion(self, **updates):
        post=dict(delete_profile='1',identifier='welcome',csrf_token='test-token',confirm_delete='1',configuration_version=self.request('describe')['configuration_version'])
        post.update(updates)
        return post

    def test_english_and_spanish_render_use_catalogs_keep_names_and_values(self):
        for language, label, limit in [('en_US','Fail Over Destination','Handler Time Limit'),('es_ES','Destino de contingencia','Límite del handler')]:
            for surface in ('embedded','unembedded'):
                html=self.web(action='view',language=language,surface=surface,pbx_widgets=True)['html']
                self.assertIn(label,html)
                self.assertIn(limit,html)
                self.assertIn('name="execution_budget_seconds" id="callflowhooks-execution_budget_ms" value="1"',html)
                self.assertIn('name="input_timeout_seconds" id="callflowhooks-input_timeout_ms" value="5"',html)
                self.assertNotIn('Destino ante fallo',html)
                if language=='en_US':
                    for own in ('Guardar perfil','Extensión del handler','Sin audio','Nombre del perfil','Habilitado','Seleccionar categoría'):
                        self.assertNotIn(own,html)
        escaped=self.web(action='view',unsafe_translation=True)['html']
        self.assertIn('&lt;b&gt;New Profile&lt;/b&gt;',escaped)
        self.assertNotIn('<b>New Profile</b>',escaped)
        fresh=self.web(action='view')['html']
        identifier=re.search(r'type="hidden" name="identifier" value="(p[a-f0-9]{32})"',fresh).group(1)
        self.assertNotIn('Profile Identifier',fresh)
        self.assertNotIn('callflowhooks-identifier',fresh)
        self.assertIn('name="display_name"',fresh)
        self.assertIn('required',fresh)
        post=self.post();post.update(identifier=identifier,display_name='')
        rejected=self.web(action='save',post=post)['html']
        self.assertIn('Required field.',rejected)
        self.assertIn('type="hidden" name="identifier" value="'+identifier+'"',rejected)
        self.assertFalse(self.request('describe')['profiles'])
        post.update(display_name='Front desk')
        self.web(action='save',post=post)
        destination='callflow-profile-'+identifier+',s,1'
        self.assertEqual(self.request('describe')['profiles'][0]['identifier'],identifier)
        post=self.post();post.update(identifier=identifier,display_name='Renamed desk');post['settings']['api_token']=''
        renamed=self.web(action='save',post=post,info_destination=destination)
        self.assertIn('Renamed desk',renamed['destination_info']['description'])
        self.assertEqual(self.request('describe')['profiles'][0]['custom_destination'],destination)
        self.assertIn('private-token',self.config.read_text())
        self.saved()
        for language in ('en_US','es_ES'):
            self.assertIn('welcome',self.web(action='view',language=language,get={'profile':'welcome'})['html'])
        self.assertEqual(self.request('describe')['profiles'][0]['settings']['greeting'],'Buen día')

    def test_seconds_integer_selection_preserves_old_fractional_configuration_until_save(self):
        original=self.profile();original.update(execution_budget_ms=50,input_timeout_ms=1500)
        self.request('save',profile=original,expected_version=self.request('describe')['configuration_version'])
        before=self.config.read_bytes()
        html=self.web(action='view',get={'profile':'welcome'})['html']
        self.assertIn('value="0.05"',html);self.assertIn('value="1.5"',html)
        self.assertNotIn('Fractions of a second',html)
        self.assertNotIn('up to three decimal places',html)
        post=self.post();post.update(execution_budget_seconds='0.05',input_timeout_seconds='1.5')
        self.web(action='save',post=post)
        self.assertEqual(self.config.read_bytes(),before)
        # Old cached HTTP submissions in milliseconds cannot bypass the integer UI.
        post=self.post();post.update(execution_budget_ms=50,input_timeout_ms=1500)
        self.web(action='save',post=post)
        self.assertEqual(self.config.read_bytes(),before)
        post=self.post();post.update(execution_budget_seconds='02',input_timeout_seconds='03');post['settings']['api_token']=''
        self.web(action='save',post=post)
        item=self.request('describe')['profiles'][0]
        self.assertEqual((item['execution_budget_ms'],item['input_timeout_ms']),(2000,3000))
        self.assertIn('private-token',self.config.read_text())

    def test_invalid_seconds_draft_recovers_exact_raw_text_and_translates_after_language_change(self):
        before=self.request('describe')['configuration_version']
        for raw in ('','0','1.5','1.000','6','NaN','1e0','<script>'):
            post=self.post();post['execution_budget_seconds']=raw;post['input_timeout_seconds']='1'
            html=self.web(action='save',post=post,language='es_ES')['html']
            self.assertIn('Ingresar segundos enteros entre 1 y 5',html)
            self.assertIn('Borrador recuperado',html)
            self.assertNotIn('<script>',html)
            self.assertEqual(self.request('describe')['configuration_version'],before)
            english=self.web(action='view',language='en_US')['html']
            self.assertIn('Enter a whole number of seconds between 1 and 5',english)
            self.assertNotIn('Ingresar segundos',english)
            self.assertNotIn('private-token',self.config.with_suffix('.conf.session').read_text())

    def test_backend_parameterized_errors_translate_and_draft_keeps_nonsecret_values(self):
        post=self.post();post['settings']['greeting']='x'*81
        english=self.web(action='save',post=post)['html']
        self.assertIn('Enter text up to 80 characters.',english)
        self.assertNotIn('Ingresar texto',english)
        self.assertIn('Ingresar texto de hasta 80 caracteres.',self.web(action='view',language='es_ES')['html'])
        post=self.post();post['input_max_digits']=0
        self.assertIn('Enter an integer between 1 and 40.',self.web(action='save',post=post)['html'])

    def test_delete_confirmation_csrf_get_safety_then_clean_catalog_and_remaining_context(self):
        self.saved(); version=self.request('describe')['configuration_version']
        other=self.profile('other');self.request('save',profile=other,expected_version=version)
        self.web(action='view',get={'profile':'welcome','delete_profile':'1','confirm_delete':'1'})
        self.assertEqual(len(self.request('describe')['profiles']),2)
        for updates, message in [({'csrf_token':'bad'},'form has expired'),({'confirm_delete':'0'},'Confirm profile deletion')]:
            result=self.web(action='save',post=self.deletion(**updates))
            self.assertIn(message,result['html'])
            self.assertEqual(len(self.request('describe')['profiles']),2)
        result=self.web(action='save',post=self.deletion())
        self.assertIn('Profile deleted.',result['html']);self.assertEqual(result['reloads'],1)
        self.assertNotIn('callflow-profile-welcome,s,1',result['destinations'])
        self.assertNotIn('callflow-profile-welcome:',result['dialplan'])
        self.assertIn('callflow-profile-other:',result['dialplan'])
        self.assertEqual(self.request('describe')['profiles'][0]['identifier'],'other')
        self.assertIn('private-token',self.config.read_text())

    def test_delete_authentication_and_unrelated_draft_preservation(self):
        self.saved()
        original=self.config.read_bytes()
        for restrictions in ({'denied':True},{'surface':'embedded','framework_denied':True},{'surface':'embedded','missing_framework_acl':True}):
            html=self.web(action='save',post=self.deletion(),**restrictions)['html']
            self.assertIn('Access denied',html)
            self.assertEqual(self.config.read_bytes(),original)
        post=self.post();post['identifier']='other';post['execution_budget_seconds']='invalid'
        self.web(action='save',post=post)
        draft=self.config.with_suffix('.conf.session')
        self.assertEqual(json.loads(draft.read_text())['profile']['identifier'],'other')
        self.web(action='save',post=self.deletion())
        self.assertEqual(json.loads(draft.read_text())['profile']['identifier'],'other')
        self.assertIn('Draft recovered',self.web(action='view')['html'])

    def test_usage_list_escapes_names_links_and_rechecks_post_reference(self):
        self.saved()
        refs={'ivr':[{'dest':'callflow-profile-welcome,s,1','description':'IVR: <script>name</script>','edit_url':'config.php?display=ivr&id=2'}],
              'routes':[{'dest':'callflow-profile-welcome,s,1','description':'Route & name','edit_url':'javascript:alert(1)'}]}
        html=self.web(action='view',get={'profile':'welcome'},references=refs)['html']
        self.assertIn('Used as Destination by 2 Object(s)',html)
        self.assertLess(html.index('id="title"'),html.index('Used as Destination'))
        self.assertLess(html.index('Used as Destination'),html.index('name="delete_profile"'))
        self.assertLess(html.index('name="delete_profile"'),html.index('<hr>'))
        self.assertLess(html.index('<hr>'),html.index('name="display_name"'))
        self.assertIn('<span class="help">?<span>',html)
        self.assertIn('/admin/images/core_delete.png',html)
        self.assertLess(html.index('</form>'),html.index('class="popover-form"'))
        self.assertIn('&lt;script&gt;name&lt;/script&gt;',html)
        self.assertIn('config.php?display=ivr&amp;id=2',html)
        self.assertNotIn('href="javascript:',html)
        self.web(action='view',get={'profile':'welcome'})
        result=self.web(action='save',post=self.deletion(),references=refs,language='es_ES')
        self.assertIn('Este perfil todavía está usado',result['html'])
        self.assertIn('Editar perfil: welcome',result['html'])
        self.assertEqual(len(self.request('describe')['profiles']),1)

    def test_usage_missing_failed_invalid_blocks_delete_preserves_access(self):
        self.saved()
        for switch in ('missing_usage_api','usage_failure','usage_invalid'):
            result=self.web(action='view',get={'profile':'welcome'},**{switch:True})
            self.assertIn('Deletion is disabled.',result['html'])
            self.assertIn('name="delete_profile" value="1" type="submit" disabled',result['html'])
            result=self.web(action='save',post=self.deletion(),**{switch:True})
            self.assertIn('profile deletion is unavailable.',result['html'])
            self.assertEqual(len(self.request('describe')['profiles']),1)
