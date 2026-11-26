"""Public artifact CLI and real Git; no internal collaborators mocked."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[2] / 'tools/agent_evidence.py'


class CandidateEvidence(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.repo = self.root / 'source'
        self.repo.mkdir()
        self.git('init', '-q')
        self.git('config', 'user.name', 'Fixture')
        self.git('config', 'user.email', 'fixture@example.invalid')
        self.source = self.repo / 'docs/bootstrap/recovery-foundation/example.py'
        self.source.parent.mkdir(parents=True)
        self.source.write_text('# base\n')
        self.git('add', '.')
        self.git('commit', '-qm', 'Base')
        self.base = self.git('rev-parse', 'HEAD')

    def tearDown(self):
        self.temp.cleanup()

    def git(self, *args, cwd=None):
        return subprocess.check_output(['git'] + list(args), cwd=str(cwd or self.repo)).decode().strip()

    def commit(self):
        self.git('add', '.')
        self.git('commit', '-qm', 'Candidate')
        return self.git('rev-parse', 'HEAD')

    def capture(self, head, terminated=True):
        arguments = [sys.executable, str(SCRIPT), 'snapshot', '--workspace', str(self.repo),
                     '--base', self.base, '--head', head, '--output', str(self.root / 'bundle')]
        if terminated:
            arguments.append('--worker-terminated')
        result = subprocess.run(arguments,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return result, json.loads(result.stdout.decode()) if result.stdout else None

    def test_committed_candidate_artifact_restores_exact_tree_in_clean_checkout(self):
        self.source.write_text('print("recovered")\n')
        head = self.commit()
        process, manifest = self.capture(head)
        self.assertEqual(process.returncode, 0, process.stderr.decode())
        self.assertEqual(manifest['status'], 'complete')
        self.assertEqual(manifest['head_sha'], head)
        self.assertEqual(manifest['base_sha'], self.base)
        self.assertEqual(manifest['changed_count'], 1)
        self.assertFalse(manifest['truncated'])
        entry = manifest['files'][0]
        self.assertEqual(entry['path'], 'docs/bootstrap/recovery-foundation/example.py')
        content = (self.root / 'bundle' / entry['artifact']).read_bytes()
        self.assertEqual(content, b'print("recovered")\n')
        self.assertEqual(entry['sha256'], hashlib.sha256(content).hexdigest())
        patch = self.root / 'bundle' / manifest['patch']['artifact']
        self.assertEqual(manifest['patch']['sha256'], hashlib.sha256(patch.read_bytes()).hexdigest())
        restored = self.root / 'restored'
        self.git('clone', '-q', str(self.repo), str(restored))
        self.git('checkout', '-q', '--detach', self.base, cwd=restored)
        self.git('apply', '--index', '--binary', str(patch), cwd=restored)
        self.assertEqual(self.git('write-tree', cwd=restored), self.git('rev-parse', head + '^{tree}'))

    def test_dirty_workspace_does_not_export_live_source(self):
        self.source.write_text('# still being changed\n')
        process, manifest = self.capture(self.base)
        self.assertNotEqual(process.returncode, 0)
        self.assertEqual(manifest['status'], 'unavailable')
        self.assertEqual(manifest['reason'], 'workspace-not-clean-at-head')
        self.assertFalse((self.root / 'bundle/candidate.patch').exists())

    def test_sensitive_file_blocks_complete_artifact_without_exporting_its_content(self):
        secret = self.source.parent / 'private.key'
        secret.write_text('FAKE-SECRET-MUST-NOT-BE-EXPORTED')
        process, manifest = self.capture(self.commit())
        self.assertNotEqual(process.returncode, 0)
        self.assertEqual(manifest['status'], 'incomplete')
        self.assertEqual(manifest['exclusions'][0]['reason'], 'sensitive-or-operational-path')
        self.assertNotIn('FAKE-SECRET-MUST-NOT-BE-EXPORTED', json.dumps(manifest))
        self.assertFalse((self.root / 'bundle/candidate.patch').exists())
        self.assertFalse((self.root / 'bundle/sources').exists())

    def test_source_size_limit_is_explicit_instead_of_silent_truncation(self):
        self.source.write_bytes(b'x' * 300000)
        process, manifest = self.capture(self.commit())
        self.assertNotEqual(process.returncode, 0)
        self.assertTrue(manifest['truncated'])
        self.assertEqual(manifest['exclusions'][0]['reason'], 'source-size-limit')
        self.assertFalse((self.root / 'bundle/candidate.patch').exists())

    def test_unconfirmed_termination_does_not_read_or_export_worker_files(self):
        process, manifest = self.capture(self.base, terminated=False)
        self.assertNotEqual(process.returncode, 0)
        self.assertEqual(manifest['reason'], 'termination-unconfirmed')
        self.assertFalse((self.root / 'bundle').exists())

    def test_symlink_never_exports_target_as_source(self):
        outside = self.root / 'outside.txt'
        outside.write_text('FAKE-PRIVATE-TARGET')
        self.source.unlink()
        self.source.symlink_to(outside)
        process, manifest = self.capture(self.commit())
        self.assertNotEqual(process.returncode, 0)
        self.assertEqual(manifest['exclusions'][0]['reason'], 'not-regular-source')
        self.assertNotIn('FAKE-PRIVATE-TARGET', json.dumps(manifest))
        self.assertFalse((self.root / 'bundle/candidate.patch').exists())


if __name__ == '__main__':
    unittest.main()
