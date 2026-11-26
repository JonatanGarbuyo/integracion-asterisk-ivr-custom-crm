"""Deletion through the public JSON administrator, preserving unrelated data."""
import json
import os
import stat
import subprocess
import sys
import unittest

from boundary_support import AdminBoundary, ENTRY


class ProfileDeletion(AdminBoundary, unittest.TestCase):
    def saved(self, identifier='welcome'):
        return self.request('save', profile=self.profile(identifier),
                            expected_version=self.request('describe')['configuration_version'])

    def test_delete_one_profile_preserves_other_profile_secret_and_redacts_response(self):
        self.saved()
        second = self.saved('afterhours')
        result = self.request('delete', identifier='welcome',
                              expected_version=second['configuration_version'])
        self.assertTrue(result['ok'], result)
        self.assertEqual([p['identifier'] for p in result['profiles']], ['afterhours'])
        self.assertNotIn('private-token', json.dumps(result))
        self.assertIn('private-token', self.config.read_text())
        self.assertNotIn('[profile:welcome]', self.config.read_text())
        self.assertEqual(stat.S_IMODE(self.config.stat().st_mode), 0o600)
        remaining = result['configuration_version']
        self.assertTrue(self.request('delete', identifier='afterhours', expected_version=remaining)['ok'])
        self.assertEqual(self.request('describe')['profiles'], [])

    def test_invalid_missing_and_stale_delete_leave_file_exactly_unchanged(self):
        empty = self.request('describe')['configuration_version']
        saved = self.saved()
        before = self.config.read_bytes()
        cases = [('welcome', empty, 'stale_configuration'),
                 ('missing', saved['configuration_version'], 'validation_error'),
                 ('../welcome', saved['configuration_version'], 'validation_error'),
                 (None, saved['configuration_version'], 'validation_error')]
        for identifier, version, code in cases:
            result = self.request('delete', identifier=identifier, expected_version=version)
            self.assertFalse(result['ok'], result)
            self.assertEqual(result['error_code'], code)
            self.assertEqual(self.config.read_bytes(), before)

    def test_manual_profile_reference_blocks_deletion_without_rewriting_or_leaking(self):
        self.saved()
        self.saved('afterhours')
        self.config.write_text(self.config.read_text().replace(
            'next_destination = ext-local,201,1',
            'next_destination = callflow-profile-welcome,s,1', 1))
        import hashlib
        before = self.config.read_bytes()
        result = self.request('delete', identifier='welcome',
                              expected_version=hashlib.sha256(before).hexdigest())
        # Direct profile chains are rejected by the existing configuration rules;
        # deletion must also fail closed for this manually edited configuration.
        self.assertFalse(result['ok'])
        self.assertNotIn('private-token', json.dumps(result))
        self.assertEqual(self.config.read_bytes(), before)

    @unittest.skipIf(os.geteuid() == 0, 'Requires the nonroot CI runner')
    def test_write_failure_preserves_profile_and_other_secrets(self):
        saved = self.saved()
        before = self.config.read_bytes()
        self.addCleanup(self.config.parent.chmod, 0o700)
        self.config.parent.chmod(0o500)
        result = self.request('delete', identifier='welcome',
                              expected_version=saved['configuration_version'])
        self.assertFalse(result['ok'])
        self.assertEqual(result['error_code'], 'permission_denied')
        self.assertEqual(self.config.read_bytes(), before)

    def test_storage_failure_returns_safe_io_error_and_cleans_temporary_file(self):
        saved = self.saved()
        before = self.config.read_bytes()
        request = dict(action='delete', identifier='welcome',
                       expected_version=saved['configuration_version'])
        for operation in ('fsync', 'replace'):
            # Only the external filesystem operation fails; the real JSON
            # administrator, configuration validation and writer execute.
            harness = '''import errno, os, runpy, sys
def fail(*args):
    raise OSError(errno.EIO, 'private-token')
setattr(os, sys.argv[1], fail)
entry, config = sys.argv[2:]
sys.path.insert(0, os.path.dirname(entry))
sys.argv = [entry, '--config', config, 'admin']
runpy.run_path(entry, run_name='__main__')
'''
            process = subprocess.run([sys.executable, '-c', harness, operation,
                                      str(ENTRY), str(self.config)],
                                     input=json.dumps(request), universal_newlines=True,
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5)
            self.assertEqual(process.returncode, 0, process.stderr)
            response = json.loads(process.stdout)
            self.assertFalse(response['ok'])
            self.assertEqual(response['error_code'], 'io_error')
            self.assertNotIn('private-token', process.stdout + process.stderr)
            self.assertEqual(self.config.read_bytes(), before)
            self.assertEqual(list(self.config.parent.glob('.profiles-*')), [])
