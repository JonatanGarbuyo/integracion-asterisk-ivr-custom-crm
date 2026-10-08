import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
ENTRY = ROOT / 'module' / 'backend' / 'entry.py'


class Administration(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.config = pathlib.Path(self.directory.name) / 'profiles.conf'

    def request(self, action, **data):
        process = subprocess.run(
            [sys.executable, str(ENTRY), '--config', str(self.config), 'admin'],
            input=json.dumps(dict(action=action, **data)), universal_newlines=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5)
        self.assertEqual(process.returncode, 0, process.stderr)
        return json.loads(process.stdout)

    def profile(self, identifier='welcome'):
        return dict(identifier=identifier, extension='example', enabled=True,
                    next_destination='ext-local,201,1',
                    fallback_destination='ext-local,202,1',
                    execution_budget_ms=800, input_source='none',
                    settings={'greeting': 'Buen día', 'api_token': 'private-token'})

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
