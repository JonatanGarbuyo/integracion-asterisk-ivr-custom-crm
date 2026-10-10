"""PBX catalog selection -> public form -> .conf -> real AGI."""
import shutil
import hashlib
import unittest
from html.parser import HTMLParser

from boundary_support import AdminBoundary
from agi_harness import call
import test_web


class Selects(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.fields = {}
        self.field = None
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'select':
            self.field = attrs.get('name')
            self.fields[self.field] = []
        elif tag == 'option' and self.field:
            self.fields[self.field].append(attrs.get('value', ''))

    def handle_endtag(self, tag):
        if tag == 'select':
            self.field = None


@unittest.skipUnless(shutil.which('php'), 'PHP required in CI')
class PBXSelectors(AdminBoundary, unittest.TestCase):
    web = test_web.PBXForm.web

    def post(self):
        return dict(self.profile(), csrf_token='test-token',
                    configuration_version=self.request('describe')['configuration_version'])

    def view(self, **args):
        return self.web(dict(action='view', surface='embedded', pbx_widgets=True, **args))['html']

    def save(self, post, **args):
        return self.web(dict(action='save', surface='embedded', pbx_widgets=True, post=post, **args))

    def test_select_recording_and_queue_then_execute_dtmf_agi(self):
        fields = Selects(self.view()).fields
        self.assertIn('2', fields['input_prompt_recording_id'])
        self.assertNotIn('3', fields['input_prompt_recording_id'])
        self.assertIn('Queues', fields['gotocallflow_next_destination'])
        self.assertIn('ext-queues,6000,1', fields['Queuescallflow_next_destination'])
        post = self.post()
        post.update(next_destination_mode='pbx', gotocallflow_next_destination='Queues',
                    Queuescallflow_next_destination='ext-queues,6000,1',
                    fallback_destination_mode='pbx', gotocallflow_fallback_destination='Terminate_Call',
                    Terminate_Callcallflow_fallback_destination='app-blackhole,hangup,1',
                    input_prompt_mode='pbx', input_prompt_recording_id='2', input_source='dtmf')
        saved = self.save(post)
        self.assertEqual(saved['reloads'], 1)
        profile = self.request('describe')['profiles'][0]
        self.assertEqual(profile['next_destination'], 'ext-queues,6000,1')
        self.assertEqual(profile['fallback_destination'], 'app-blackhole,hangup,1')
        self.assertEqual(profile['input_prompt'], 'custom/bienvenido')
        variables, commands, _ = call(self.config, digits='20123456789')
        self.assertEqual(variables['CALLFLOW_NEXT_DESTINATION'], 'ext-queues,6000,1')
        self.assertIn('GET DATA "custom/bienvenido" 5000 20', commands)
        self.assertNotIn('private-token', saved['html'])
        post.pop('enabled')
        post['configuration_version'] = self.request('describe')['configuration_version']
        self.save(post)
        variables, _, _ = call(self.config)
        self.assertEqual(variables['CALLFLOW_NEXT_DESTINATION'], 'app-blackhole,hangup,1')

    def test_existing_manual_values_and_no_audio_are_preserved(self):
        profile = self.profile()
        profile['input_prompt'] = 'custom/manual'
        self.request('save', profile=profile, expected_version=self.request('describe')['configuration_version'])
        edit = self.view(get={'profile':'welcome'})
        self.assertIn('name="next_destination" value="ext-local,201,1"', edit)
        self.assertIn('name="input_prompt" value="custom/manual"', edit)
        post = self.post()
        self.assertNotIn('Ingresar manualmente', edit)
        post.update(next_destination_mode='pbx', gotocallflow_next_destination='cfh_existing',
                    cfh_existingcallflow_next_destination='ext-local,201,1',
                    fallback_destination_mode='pbx', gotocallflow_fallback_destination='cfh_existing',
                    cfh_existingcallflow_fallback_destination='ext-local,202,1',
                    input_prompt_mode='pbx', input_prompt_recording_id='cfh_existing', input_prompt='custom/manual')
        post['settings']['api_token'] = ''
        self.save(post)
        self.assertEqual(self.request('describe')['profiles'][0]['input_prompt'], 'custom/manual')
        post = self.post()
        post.update(input_prompt_mode='pbx', input_prompt_recording_id='')
        self.save(post)
        self.assertEqual(self.request('describe')['profiles'][0]['input_prompt'], '')

    def test_deleted_or_invalid_selection_keeps_configuration_and_safe_draft(self):
        self.request('save', profile=self.profile(), expected_version=self.request('describe')['configuration_version'])
        before = self.config.read_bytes()
        cases = [dict(input_prompt_mode='pbx', input_prompt_recording_id='999'),
                 dict(input_prompt_mode='pbx', input_prompt_recording_id='2 OR 1=1'),
                 dict(next_destination_mode='pbx', gotocallflow_next_destination='Queues', Queuescallflow_next_destination='ext-queues,9999,1'),
                 dict(next_destination_mode='pbx', gotocallflow_next_destination='settings')]
        for values in cases:
            post = self.post()
            post.update(values)
            failed = self.save(post)
            self.assertIn('role="alert"', failed['html'])
            self.assertEqual(self.config.read_bytes(), before)
            self.assertEqual(failed['reloads'], 0)
            self.assertIn('Borrador recuperado', self.view())
            self.assertNotIn('private-token', failed['html'])

    def test_invalid_manual_destination_is_escaped_and_not_sent_to_native_helper(self):
        post = self.post()
        post.update(next_destination_mode='manual', next_destination='"><script>alert(1)</script>')
        failed = self.save(post)
        self.assertNotIn('<script>alert(1)</script>', failed['html'])
        self.assertIn('&lt;script&gt;', failed['html'])
        self.assertFalse(self.config.exists())
        self.assertFalse(failed['destinations'])

    def test_invalid_next_destination_preserves_other_valid_selections_in_draft(self):
        post = self.post()
        post.update(next_destination_mode='pbx', gotocallflow_next_destination='Queues',
                    Queuescallflow_next_destination='ext-queues,9999,1',
                    fallback_destination_mode='pbx', gotocallflow_fallback_destination='Terminate_Call',
                    Terminate_Callcallflow_fallback_destination='app-blackhole,hangup,1',
                    input_prompt_mode='pbx', input_prompt_recording_id='2')
        failed = self.save(post)
        self.assertIn('Corregir las selecciones indicadas.', failed['html'])
        recovered = self.view()
        self.assertIn('name="input_prompt" value="custom/bienvenido"', recovered)
        self.assertIn('name="fallback_destination" value="app-blackhole,hangup,1"', recovered)
        self.assertFalse(self.config.exists())
        self.assertEqual(failed['reloads'], 0)

    def test_native_catalog_text_is_escaped_with_popover_options(self):
        markup = '"><script>alert(1)</script>'
        catalog = {'Queues': [dict(destination='ext-queues,6000,1', description=markup),
                              dict(destination='popover', description='Add new')],
                   markup: [dict(destination=markup, description='Invalid destination')],
                   'Atención': [dict(destination='ext-queues,6001,1', description='&lt;6001&gt; soporte')]}
        html = self.view(destination_catalog=catalog)
        self.assertNotIn('<script>alert(1)</script>', html)
        self.assertIn('&lt;script&gt;', html)
        fields = Selects(html).fields
        self.assertEqual(fields['Queuescallflow_next_destination'], ['ext-queues,6000,1', 'popover'])
        self.assertIn('popover', fields['Queuescallflow_fallback_destination'])
        key = 'cfh_category_' + hashlib.sha1('Atención'.encode()).hexdigest()
        self.assertIn(key, fields['gotocallflow_next_destination'])
        self.assertIn('&lt;6001&gt; soporte', html)
        self.assertNotIn('&amp;lt;6001', html)
        post = self.post()
        post.update(next_destination_mode='pbx', gotocallflow_next_destination=key)
        post[key + 'callflow_next_destination'] = 'ext-queues,6001,1'
        self.save(post, destination_catalog=catalog)
        self.assertEqual(self.request('describe')['profiles'][0]['next_destination'], 'ext-queues,6001,1')

    def test_category_names_with_spaces_and_underscores_have_distinct_keys(self):
        catalog = {'A B': [dict(destination='ext-queues,6000,1', description='first')],
                   'A_B': [dict(destination='ext-queues,6001,1', description='second')]}
        fields = Selects(self.view(destination_catalog=catalog)).fields
        first, second = ['cfh_category_' + hashlib.sha1(label.encode()).hexdigest() for label in ('A B', 'A_B')]
        self.assertIn(first, fields['gotocallflow_next_destination'])
        self.assertIn(second, fields['gotocallflow_next_destination'])
        self.assertEqual(fields[first + 'callflow_next_destination'], ['ext-queues,6000,1'])
        self.assertEqual(fields[second + 'callflow_next_destination'], ['ext-queues,6001,1'])
        post = self.post()
        post.update(next_destination_mode='pbx', gotocallflow_next_destination=second)
        post[second + 'callflow_next_destination'] = 'ext-queues,6001,1'
        self.save(post, destination_catalog=catalog)
        self.assertEqual(self.request('describe')['profiles'][0]['next_destination'], 'ext-queues,6001,1')

    def test_native_popover_metadata_and_newly_created_destination(self):
        html = self.view(with_popovers=True)
        fields = Selects(html).fields
        self.assertIn('popover', fields['Queuescallflow_next_destination'])
        self.assertIn('data-url="config.php?display=queues"', html)
        self.assertIn('data-class="queues" data-mod="queues"', html)
        self.assertIn('class="destdropdown2 queues"', html)
        post = self.post()
        post.update(next_destination_mode='pbx', gotocallflow_next_destination='Queues',
                    Queuescallflow_next_destination='popover')
        self.assertIn('role="alert"', self.save(post, with_popovers=True)['html'])
        self.assertFalse(self.config.exists())
        # After the provider creates a queue, a fresh POST sees its new catalog item.
        post['Queuescallflow_next_destination'] = 'ext-queues,6002,1'
        catalog = {'Queues':[dict(destination='ext-queues,6002,1',description='New queue')]}
        self.save(post, destination_catalog=catalog)
        self.assertEqual(self.request('describe')['profiles'][0]['next_destination'], 'ext-queues,6002,1')

    def test_editable_name_updates_destination_catalog_without_changing_context(self):
        post = self.post()
        post['display_name'] = 'Atención afiliados'
        saved = self.save(post, info_destination='callflow-profile-welcome,s,1', usage_destination='ext-local,201,1')
        self.assertEqual(saved['destination_info']['description'], 'CallFlow Hooks: Atención afiliados')
        self.assertIn('profile=welcome', saved['destination_info']['edit_url'])
        self.assertEqual(saved['destination_usage'][0]['dest'], 'ext-local,201,1')
        self.assertIn('CallFlow Hooks → Atención afiliados', saved['html'])
        self.assertNotIn('Pulsar Aplicar', saved['html'])
        post['display_name'] = 'Afiliados registrados'
        post['configuration_version'] = self.request('describe')['configuration_version']
        self.save(post)
        html = self.view(get={'profile':'welcome'})
        self.assertIn('name="display_name" value="Afiliados registrados"', html)
        self.assertIn('readonly', html)
        self.assertIn('CallFlow_Hooks', Selects(html).fields['gotocallflow_next_destination'])
        self.assertIn('callflow-profile-welcome,s,1', Selects(html).fields['CallFlow_Hookscallflow_next_destination'])
        variables, _, _ = call(self.config)
        self.assertEqual(variables['CALLFLOW_PROFILE_IDENTIFIER'], 'welcome')

    def test_empty_core_categories_keep_create_popovers(self):
        catalog = {label:[dict(destination='popover', description='Add new '+label)] for label in ('Extensions', 'Users')}
        html = self.view(destination_catalog=catalog)
        fields = Selects(html).fields
        for label in ('Extensions', 'Users'):
            self.assertEqual(fields[label+'callflow_next_destination'], ['popover'])
            self.assertIn('data-url="config.php?display='+label.lower()+'"', html)
            self.assertIn('data-class="'+label.lower()+'" data-mod="core"', html)
            self.assertIn('class="destdropdown2 core '+label.lower()+'"', html)
        nested = Selects(self.view(destination_catalog=catalog, nested_popover=True)).fields
        self.assertEqual(nested['Extensionscallflow_next_destination'], [])

    def test_invalid_configuration_isolated_from_catalog_but_blocks_usage_checks(self):
        self.config.write_text('[invalid]\nsecret=private-token\n')
        result = self.web(dict(action='view', callbacks_only=True))
        self.assertEqual(result['catalog'], [])
        self.assertFalse(result['info'])
        self.assertTrue(result['usage_failed'])
        self.assertIn('role="alert"', result['html'])
        self.assertNotIn('private-token', result['html'])

    def test_synchronize_profile_from_conf_without_legacy_duplicate(self):
        self.request('save', profile=self.profile(), expected_version=self.request('describe')['configuration_version'])
        result = self.save({'synchronize':'1', 'csrf_token':'test-token'})
        self.assertIn('Destinos sincronizados', result['html'])
        self.assertEqual(result['reloads'], 1)
        self.assertEqual(result['destinations'], [])
        self.assertIn('callflow-profile-welcome,s,1', Selects(self.view(get={'profile':'welcome'})).fields['CallFlow_Hookscallflow_next_destination'])

    def test_missing_pbx_widget_apis_keep_manual_form_usable(self):
        view = self.web({'action':'view', 'surface':'embedded'})['html']
        self.assertIn('name="input_prompt"', view)
        post = self.post()
        post['input_prompt'] = 'custom/manual'
        saved = self.web({'action':'save','surface':'embedded','post':post})
        self.assertEqual(saved['reloads'], 1)
        self.assertEqual(self.request('describe')['profiles'][0]['input_prompt'], 'custom/manual')

    def test_recording_labels_are_escaped_and_removed_recording_stays_manual(self):
        profile = self.profile()
        profile['input_prompt'] = 'custom/bienvenido'
        self.request('save', profile=profile, expected_version=self.request('describe')['configuration_version'])
        html = self.view(get={'profile':'welcome'}, recordings=[{'id':2, 'displayname':'<script>alert(1)</script>', 'filename':'custom/bienvenido'}])
        self.assertNotIn('<script>alert(1)</script>', html)
        self.assertIn('&lt;script&gt;', html)
        self.assertIn('value="2" selected', html)
        html = self.view(get={'profile':'welcome'}, recordings=[])
        self.assertIn('name="input_prompt" value="custom/bienvenido"', html)
        post = self.post()
        post.update(input_prompt_mode='manual', input_prompt='custom/bienvenido')
        self.save(post, recordings=[])
        self.assertEqual(self.request('describe')['profiles'][0]['input_prompt'], 'custom/bienvenido')
