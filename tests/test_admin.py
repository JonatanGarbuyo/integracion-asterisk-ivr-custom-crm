import json
import pathlib
import unittest
from boundary_support import AdminBoundary

class Administration(AdminBoundary, unittest.TestCase):

    def test_schema_form_saves_two_independent_profiles_and_redacts_secrets(self):
        form = self.request('describe')
        self.assertTrue(form['ok'])
        self.assertEqual(form['extensions'][0]['fields']['greeting']['default'], 'Hola')
        first = self.request('save', profile=self.profile(), expected_version=form['configuration_version'])
        self.assertTrue(first['ok'], first)
        second = self.profile('afterhours')
        second['next_destination'] = 'ext-local,203,1'
        self.assertTrue(self.request('save', profile=second,
                                    expected_version=first['configuration_version'])['ok'])
        listing = self.request('describe')
        self.assertEqual([p['identifier'] for p in listing['profiles']], ['afterhours', 'welcome'])
        self.assertEqual(listing['profiles'][0]['custom_destination'], 'callflow-profile-afterhours,s,1')
        self.assertNotIn('private-token', json.dumps(listing))
        self.assertIn('private-token', self.config.read_text())

    def test_invalid_and_stale_saves_preserve_valid_configuration_and_blank_secret(self):
        first = self.request('save', profile=self.profile(),
                             expected_version=self.request('describe')['configuration_version'])
        original = self.config.read_bytes()
        bad = self.profile()
        bad['next_destination'] = '${SHELL(echo injected)},s,1'
        self.assertFalse(self.request('save', profile=bad,
                                     expected_version=first['configuration_version'])['ok'])
        self.assertEqual(self.config.read_bytes(), original)
        edited = self.profile()
        edited['settings']['api_token'] = ''
        edited['settings']['greeting'] = 'Hello'
        self.assertTrue(self.request('save', profile=edited,
                                    expected_version=first['configuration_version'])['ok'])
        self.assertIn('private-token', self.config.read_text())
        self.assertFalse(self.request('save', profile=self.profile('stale'),
                                     expected_version=first['configuration_version'])['ok'])

    def test_manual_malformed_configuration_returns_safe_error(self):
        self.config.write_text('[profile:bad\nsecret-value')
        response = self.request('describe')
        self.assertFalse(response['ok'])
        self.assertNotIn('secret-value', json.dumps(response))

    def test_extension_cannot_publish_credentials_as_schema_defaults(self):
        self.extensions = pathlib.Path(self.directory.name) / 'extensions'
        module = self.extensions / 'unsafe'
        module.mkdir(parents=True)
        manifest = dict(identifier='unsafe', title='Unsafe', contract_version=1,
                        command=['@python', 'handler.py'],
                        fields={'token': {'type': 'secret', 'label': 'Token', 'default': 'credential-leak'}})
        (module / 'manifest.json').write_text(json.dumps(manifest))
        response = self.request('describe')
        self.assertFalse(response['ok'])
        self.assertNotIn('credential-leak', json.dumps(response))
