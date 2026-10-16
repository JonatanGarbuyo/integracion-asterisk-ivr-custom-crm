"""Deletion coordinator -> native API boundary and real versioned .conf backend."""
import json
import os
import shutil
import subprocess
import unittest

from boundary_support import AdminBoundary, ROOT


@unittest.skipUnless(shutil.which('php'), 'PHP is required; mandatory PHP jobs run in CI')
class ProfileDeletion(AdminBoundary, unittest.TestCase):
    destination = 'callflow-profile-welcome,s,1'

    def setUp(self):
        super().setUp()
        self.request('save', profile=self.profile(),
                     expected_version=self.request('describe')['configuration_version'])

    def php(self, action='delete', **data):
        data.setdefault('version', self.request('describe')['configuration_version'])
        environment = dict(os.environ, CFH_TEST_CONFIG=str(self.config),
                           CFH_TEST_PYTHON=os.sys.executable)
        process = subprocess.run(['php', str(ROOT / 'tests/profile_deletion_boundary.php')],
                                 input=json.dumps(dict(action=action, **data)),
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                 universal_newlines=True, env=environment, timeout=8)
        self.assertEqual(process.returncode, 0, process.stderr)
        return json.loads(process.stdout)

    def owned_row(self):
        return dict(custom_dest=self.destination, description='Old managed entry',
                    notes='Managed by CallFlow Hooks')

    def test_usage_flattens_native_ivr_registry_without_exposing_secrets(self):
        item = dict(dest=self.destination, description='IVR: reception',
                    edit_url='config.php?display=ivr&extdisplay=7')
        result = self.php('usage', usage={'ivr': [item]})
        self.assertTrue(result['ok'])
        self.assertEqual(result['result'], [item])
        self.assertNotIn('private-token', json.dumps(result))
        self.assertEqual(result['reloads'], 0)

    def test_current_references_block_deletion_and_preserve_registry_and_bytes(self):
        before = self.config.read_bytes()
        usage = {'ivr': [dict(dest=self.destination, description='IVR: reception')]}
        result = self.php(usage=usage, row=self.owned_row())
        self.assertFalse(result['ok'])
        self.assertIn('still used', result['error'])
        self.assertEqual(self.config.read_bytes(), before)
        self.assertEqual(result['rows'][self.destination], self.owned_row())
        self.assertEqual(result['reloads'], 0)

    def test_owned_legacy_destination_is_removed_with_profile_and_reload_requested(self):
        result = self.php(row=self.owned_row())
        self.assertTrue(result['ok'], result)
        self.assertNotIn(self.destination, result['rows'])
        self.assertIn('unrelated,s,1', result['rows'])
        self.assertEqual(result['result']['profiles'], [])
        self.assertEqual(self.request('describe')['profiles'], [])
        self.assertEqual(result['reloads'], 1)

    def test_native_profile_without_legacy_row_can_be_deleted(self):
        result = self.php()
        self.assertTrue(result['ok'], result)
        self.assertEqual(self.request('describe')['profiles'], [])
        self.assertEqual(result['reloads'], 1)

    def test_foreign_row_and_unavailable_or_malformed_usage_fail_closed(self):
        before = self.config.read_bytes()
        cases = [dict(row=dict(self.owned_row(), notes='Managed elsewhere')),
                 dict(missing_usage=True), dict(missing_registry=True),
                 dict(missing_active_modules=True), dict(registry_error=True), dict(registry_malformed=True),
                 dict(usage_error=True), dict(usage='malformed'),
                 dict(usage={'ivr': ['malformed']}),
                 dict(usage={'ivr': [dict(dest=self.destination, description=42)]})]
        for case in cases:
            result = self.php(**case)
            self.assertFalse(result['ok'], case)
            self.assertNotIn('private-database-password', result['error'])
            self.assertEqual(self.config.read_bytes(), before)
            self.assertEqual(result['reloads'], 0)

    def test_cleanup_error_or_void_noop_never_deletes_profile(self):
        before = self.config.read_bytes()
        for flags in (dict(cleanup_error=True), dict(cleanup_noop=True)):
            result = self.php(row=self.owned_row(), **flags)
            self.assertFalse(result['ok'])
            self.assertEqual(self.config.read_bytes(), before)
            self.assertEqual(result['rows'][self.destination], self.owned_row())
            self.assertEqual(result['reloads'], 0)

    def test_stale_missing_and_invalid_profiles_do_not_touch_registry(self):
        before = self.config.read_bytes()
        for flags in (dict(version='old'), dict(identifier='missing'), dict(identifier='../welcome')):
            result = self.php(row=self.owned_row(), **flags)
            self.assertFalse(result['ok'])
            self.assertEqual(self.config.read_bytes(), before)
            self.assertEqual(result['rows'][self.destination], self.owned_row())
            self.assertEqual(result['reloads'], 0)

    def test_edit_during_legacy_cleanup_preserves_profile_and_secret_without_false_success(self):
        result = self.php(row=self.owned_row(), concurrent_edit=True)
        self.assertFalse(result['ok'])
        profile = self.request('describe')['profiles'][0]
        self.assertEqual(profile['display_name'], 'Concurrent edit')
        self.assertIn('api_token', profile['configured_secrets'])
        self.assertIn('private-token', self.config.read_text())
        self.assertNotIn(self.destination, result['rows'])
        self.assertEqual(result['reloads'], 0)
