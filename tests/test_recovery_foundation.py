"""Public CLI tests for ticket #41 recovery foundation (staging handoff).

Approved seams only: staging CLIs executed as processes, real temporary Git
repos for candidate/restore worktrees, GitHub API and the OpenCode executable
as the only external doubles for publication/reviews. No patching or mocking
of internal collaborators. Fixtures configure local Git identity, valid
remotes/ref HEADs and bundles outside the source repo; every scenario starts
clean. Python 3.6 compatible.
"""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STAGING = ROOT / 'docs' / 'bootstrap' / 'recovery-foundation'
PRESERVE = STAGING / 'preserve.py'
RESTORE = STAGING / 'restore.py'
CHECKSUM = STAGING / 'checksum.py'
REVIEW = STAGING / 'review.py'

REPO = 'JonatanGarbuyo/integracion-asterisk-ivr-custom-crm'
PR_MARKER = '<!-- callflow-recovery-handoff:41 -->'
MODELS = {'spec': 'opencode/muse-spark-1.3-contributor-free',
          'standards': 'opencode/mimo-v2.6-flash-free'}
VERSION = '1.18.30'


class GitFixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.repo = self.root / 'source'
        self.repo.mkdir()
        self.git('init', '-q', cwd=self.repo)
        self.git('config', 'user.name', 'Fixture', cwd=self.repo)
        self.git('config', 'user.email', 'fixture@example.invalid',
                 cwd=self.repo)
        self.candidate = self.repo / 'tests' / 'recovery_fixture.py'
        self.candidate.parent.mkdir(parents=True, exist_ok=True)
        self.candidate.write_text('# base\n')
        self.git('add', '.', cwd=self.repo)
        self.git('commit', '-qm', 'Base', cwd=self.repo)
        self.base = self.git('rev-parse', 'HEAD', cwd=self.repo)
        self.bundle = self.root / 'bundle'
        self.result_file = self.root / 'result.json'

    def tearDown(self):
        self.temp.cleanup()

    def git(self, *args, **kwargs):
        cwd = kwargs.get('cwd', self.repo)
        return subprocess.check_output(
            ['git'] + list(args),
            cwd=str(cwd)).decode().strip()

    def commit(self, message='Candidate'):
        self.git('add', '.')
        self.git('commit', '-qm', message)
        return self.git('rev-parse', 'HEAD')

    def write_result(self, reason):
        self.result_file.write_text(json.dumps(
            {'status': 'failure', 'reason': reason}) + '\n')
        return str(self.result_file)

    def preserve(self, head, terminated=True, reason='review-failed'):
        arguments = [sys.executable, str(PRESERVE), 'preserve',
                     '--workspace', str(self.repo),
                     '--base', self.base, '--head', head,
                     '--result', self.write_result(reason),
                     '--output', str(self.bundle),
                     '--ticket', '41', '--run', 'test-run']
        if terminated:
            arguments.append('--worker-terminated')
        process = subprocess.run(arguments, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, timeout=180)
        manifest = json.loads(process.stdout.decode()) if process.stdout \
            else None
        return process, manifest

    def restore(self, bundle, worktree):
        process = subprocess.run(
            [sys.executable, str(RESTORE), 'restore',
             '--bundle', str(bundle), '--worktree', str(worktree)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=180)
        return process, json.loads(process.stdout.decode())

    def clean_worktree_at(self, ref):
        target = self.root / 'restored'
        subprocess.check_call(['git', 'clone', '-q', str(self.repo),
                               str(target)])
        subprocess.check_call(['git', 'config', 'user.name', 'Fixture'],
                              cwd=str(target))
        subprocess.check_call(['git', 'config', 'user.email',
                               'fixture@example.invalid'], cwd=str(target))
        subprocess.check_call(['git', 'checkout', '-q', '--detach', ref],
                              cwd=str(target))
        return target


class PreserveCli(GitFixture):
    def test_complete_candidate_preserves_result_and_package(self):
        self.candidate.write_text('print("recovered")\n')
        head = self.commit()
        process, manifest = self.preserve(head)
        self.assertEqual(process.returncode, 0, process.stderr.decode())
        self.assertEqual(manifest['status'], 'complete')
        self.assertEqual(manifest['base_sha'], self.base)
        self.assertEqual(manifest['head_sha'], head)
        self.assertTrue(manifest['termination_confirmed'])
        self.assertEqual(manifest['termination_outcome'], 'check-failed')
        self.assertEqual(manifest['ticket'], 41)
        self.assertEqual(manifest['limits']['files'], 200)
        self.assertEqual(manifest['changed_count'], 1)
        self.assertFalse(manifest['truncated'])
        self.assertEqual(manifest['exclusions'], [])
        entry = manifest['files'][0]
        self.assertEqual(entry['path'], 'tests/recovery_fixture.py')
        self.assertIn(entry['mode'], ('100644', '100755'))
        content = (self.bundle / entry['artifact']).read_bytes()
        self.assertEqual(content, b'print("recovered")\n')
        self.assertEqual(entry['bytes'], len(content))
        self.assertEqual(entry['sha256'],
                         hashlib.sha256(content).hexdigest())
        for key in ('patch', 'uncommitted_patch', 'result'):
            info = manifest[key]
            payload = (self.bundle / info['artifact']).read_bytes()
            self.assertEqual(info['bytes'], len(payload))
            self.assertEqual(info['sha256'],
                             hashlib.sha256(payload).hexdigest())
        self.assertEqual((self.bundle / 'result.json').read_bytes(),
                         self.result_file.read_bytes())

    def test_timeout_is_never_conflated_with_check_failed(self):
        self.candidate.write_text('# timeout candidate\n')
        head = self.commit()
        process, manifest = self.preserve(head, reason='timeout')
        self.assertEqual(process.returncode, 0, process.stderr.decode())
        self.assertEqual(manifest['status'], 'complete')
        self.assertEqual(manifest['termination_outcome'], 'timeout')

    def test_unconfirmed_termination_records_unavailable(self):
        self.candidate.write_text('# still being changed\n')
        process, manifest = self.preserve(self.base, terminated=False)
        self.assertNotEqual(process.returncode, 0)
        self.assertEqual(manifest['status'], 'unavailable')
        self.assertEqual(manifest['reason'], 'termination-unconfirmed')
        self.assertFalse(self.bundle.exists())

    def test_uncommitted_changes_captured_after_confirmed_termination(self):
        self.candidate.write_text('# committed\n')
        head = self.commit()
        self.candidate.write_text('# uncommitted edit\n')
        extra = self.repo / 'tests' / 'recovery_extra.py'
        extra.write_text('# untracked\n')
        process, manifest = self.preserve(head)
        self.assertEqual(process.returncode, 0, process.stderr.decode())
        self.assertEqual(manifest['status'], 'complete')
        self.assertEqual(manifest['uncommitted']['changed_count'], 2)
        artifacts = [item['artifact'] for item in manifest['files']]
        self.assertTrue(any(name.startswith('uncommitted_sources/')
                            for name in artifacts))
        self.assertTrue((self.bundle / 'uncommitted.patch').exists())

    def test_sensitive_file_blocks_complete_bundle_without_export(self):
        secret = self.repo / 'tests' / 'fixture.key'
        secret.write_text('FAKE-SECRET-MUST-NOT-BE-EXPORTED')
        head = self.commit()
        process, manifest = self.preserve(head)
        self.assertNotEqual(process.returncode, 0)
        self.assertEqual(manifest['status'], 'incomplete')
        self.assertEqual(manifest['exclusions'][0]['reason'],
                         'sensitive-or-operational-path')
        self.assertNotIn('FAKE-SECRET-MUST-NOT-BE-EXPORTED',
                         json.dumps(manifest))
        self.assertFalse((self.bundle / 'candidate.patch').exists())
        self.assertFalse((self.bundle / 'sources').exists())

    def test_symlink_never_exports_target_as_source(self):
        outside = self.root / 'outside.txt'
        outside.write_text('FAKE-PRIVATE-TARGET')
        self.candidate.unlink()
        self.candidate.symlink_to(outside)
        head = self.commit()
        process, manifest = self.preserve(head)
        self.assertNotEqual(process.returncode, 0)
        self.assertEqual(manifest['status'], 'incomplete')
        self.assertEqual(manifest['exclusions'][0]['reason'],
                         'not-regular-source')
        self.assertNotIn('FAKE-PRIVATE-TARGET', json.dumps(manifest))
        self.assertFalse((self.bundle / 'candidate.patch').exists())

    def test_source_size_limit_is_explicit_instead_of_silent_truncation(self):
        self.candidate.write_bytes(b'x' * 300000)
        head = self.commit()
        process, manifest = self.preserve(head)
        self.assertNotEqual(process.returncode, 0)
        self.assertTrue(manifest['truncated'])
        self.assertEqual(manifest['exclusions'][0]['reason'],
                         'source-size-limit')
        self.assertFalse((self.bundle / 'candidate.patch').exists())


class RestoreCli(GitFixture):
    def complete_bundle(self, uncommitted=False):
        self.candidate.write_text('print("recovered")\n')
        head = self.commit()
        if uncommitted:
            self.candidate.write_text('print("recovered-dirty")\n')
        process, manifest = self.preserve(head)
        self.assertEqual(process.returncode, 0, process.stderr.decode())
        return manifest, head

    def test_restore_verifies_and_restores_in_clean_worktree_at_base(self):
        manifest, head = self.complete_bundle()
        worktree = self.clean_worktree_at(self.base)
        process, result = self.restore(self.bundle, worktree)
        self.assertEqual(process.returncode, 0, result)
        self.assertEqual(result['status'], 'restored')
        self.assertEqual(result['head'], head)
        content = (worktree / 'tests/recovery_fixture.py').read_bytes()
        self.assertEqual(content, b'print("recovered")\n')
        tree = subprocess.check_output(
            ['git', 'write-tree'], cwd=str(worktree)).decode().strip()
        self.assertEqual(tree, manifest['tree_sha'])

    def test_restore_applies_uncommitted_changes_without_staging_them(self):
        manifest, head = self.complete_bundle(uncommitted=True)
        worktree = self.clean_worktree_at(self.base)
        process, result = self.restore(self.bundle, worktree)
        self.assertEqual(process.returncode, 0, result)
        self.assertEqual(result['status'], 'restored')
        content = (worktree / 'tests/recovery_fixture.py').read_bytes()
        self.assertEqual(content, b'print("recovered-dirty")\n')
        tree = subprocess.check_output(
            ['git', 'write-tree'], cwd=str(worktree)).decode().strip()
        self.assertEqual(tree, manifest['tree_sha'])

    def test_restore_refuses_tampered_bundle(self):
        manifest, head = self.complete_bundle()
        entry = manifest['files'][0]
        target = self.bundle / entry['artifact']
        payload = bytearray(target.read_bytes())
        payload[0] = (payload[0] + 1) % 256
        target.write_bytes(bytes(payload))
        worktree = self.clean_worktree_at(self.base)
        process, result = self.restore(self.bundle, worktree)
        self.assertNotEqual(process.returncode, 0)
        self.assertEqual(result['reason'], 'tampered-bundle')
        self.assertEqual((worktree / 'tests/recovery_fixture.py').read_text(),
                         '# base\n')

    def test_restore_refuses_incomplete_bundle(self):
        secret = self.repo / 'tests' / 'fixture.key'
        secret.write_text('FAKE-SECRET-MUST-NOT-BE-EXPORTED')
        head = self.commit()
        process, manifest = self.preserve(head)
        self.assertEqual(manifest['status'], 'incomplete')
        worktree = self.clean_worktree_at(self.base)
        process, result = self.restore(self.bundle, worktree)
        self.assertNotEqual(process.returncode, 0)
        self.assertEqual(result['reason'], 'incomplete-bundle')

    def test_restore_refuses_symlink_inside_bundle(self):
        manifest, head = self.complete_bundle()
        entry = manifest['files'][0]
        target = self.bundle / entry['artifact']
        outside = self.root / 'outside.txt'
        outside.write_text('FAKE-PRIVATE-TARGET')
        target.unlink()
        target.symlink_to(outside)
        worktree = self.clean_worktree_at(self.base)
        process, result = self.restore(self.bundle, worktree)
        self.assertNotEqual(process.returncode, 0)
        self.assertEqual(result['reason'], 'symlink-refused')

    def test_restore_refuses_secret_and_outside_paths(self):
        manifest, head = self.complete_bundle()
        stored = json.loads((self.bundle / 'manifest.json').read_text())
        digest = hashlib.sha256(b'shh').hexdigest()
        stored['files'].append(
            {'path': 'secrets/token', 'artifact': 'sources/secrets/token',
             'mode': '100644', 'bytes': 3, 'sha256': digest})
        stored['files'].append(
            {'path': '../evil', 'artifact': 'sources/evil',
             'mode': '100644', 'bytes': 3, 'sha256': digest})
        (self.bundle / 'sources/secrets/token').parent.mkdir(parents=True,
                                                             exist_ok=True)
        (self.bundle / 'sources/secrets/token').write_bytes(b'shh')
        (self.bundle / 'sources/evil').write_bytes(b'shh')
        (self.bundle / 'manifest.json').write_text(json.dumps(stored))
        worktree = self.clean_worktree_at(self.base)
        process, result = self.restore(self.bundle, worktree)
        self.assertNotEqual(process.returncode, 0)
        self.assertEqual(result['reason'], 'unsafe-or-sensitive-path')

    def test_restore_never_uses_transcript_or_result_as_source(self):
        transcript = self.root / 'transcript-only'
        transcript.mkdir()
        (transcript / 'result.json').write_text(json.dumps(
            {'status': 'failure', 'reason': 'review-failed'}) + '\n')
        (transcript / 'transcript.log').write_text(
            'alleged candidate bytes\n')
        worktree = self.clean_worktree_at(self.base)
        process, result = self.restore(transcript, worktree)
        self.assertNotEqual(process.returncode, 0)
        self.assertEqual(result['reason'], 'incomplete-bundle')
        self.assertEqual((worktree / 'tests/recovery_fixture.py').read_text(),
                         '# base\n')

    def test_restore_refuses_dirty_or_wrong_base_worktree(self):
        manifest, head = self.complete_bundle()
        dirty = self.clean_worktree_at(self.base)
        (dirty / 'tests/recovery_fixture.py').write_text('# dirty\n')
        process, result = self.restore(self.bundle, dirty)
        self.assertNotEqual(process.returncode, 0)
        self.assertEqual(result['reason'], 'worktree-not-clean')
        wrong = self.clean_worktree_at(head)
        process, result = self.restore(self.bundle, wrong)
        self.assertNotEqual(process.returncode, 0)
        self.assertEqual(result['reason'], 'base-mismatch')


class ChecksumHandoff(unittest.TestCase):
    def test_handoff_is_generated_and_verified_by_tool(self):
        temp = tempfile.TemporaryDirectory()
        try:
            root = Path(temp.name)
            handoff = root / 'handoff.json'
            process = subprocess.run(
                [sys.executable, str(CHECKSUM), '--root', str(STAGING),
                 '--output', str(handoff)],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                timeout=180)
            self.assertEqual(process.returncode, 0,
                             process.stderr.decode())
            document = json.loads(handoff.read_text())
            self.assertEqual(document['ticket'], 41)
            for entry in document['files']:
                payload = (STAGING / entry['path']).read_bytes()
                self.assertEqual(entry['sha256'],
                                 hashlib.sha256(payload).hexdigest())
                self.assertEqual(entry['bytes'], len(payload))
            verify = subprocess.run(
                [sys.executable, str(CHECKSUM), '--root', str(STAGING),
                 '--verify', str(handoff)],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                timeout=180)
            self.assertEqual(verify.returncode, 0,
                             verify.stderr.decode())
            self.assertEqual(json.loads(verify.stdout.decode())['status'],
                             'verified')
        finally:
            temp.cleanup()

    def test_verify_detects_difference_without_invented_hashes(self):
        temp = tempfile.TemporaryDirectory()
        try:
            root = Path(temp.name)
            handoff = root / 'handoff.json'
            subprocess.check_call(
                [sys.executable, str(CHECKSUM), '--root', str(STAGING),
                 '--output', str(handoff)])
            empty = root / 'empty'
            empty.mkdir()
            process = subprocess.run(
                [sys.executable, str(CHECKSUM), '--root', str(empty),
                 '--verify', str(handoff)],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                timeout=180)
            self.assertNotEqual(process.returncode, 0)
            self.assertEqual(json.loads(process.stdout.decode())['status'],
                             'failed')
        finally:
            temp.cleanup()


class ReviewCli(GitFixture):
    def setUp(self):
        super(ReviewCli, self).setUp()
        (self.repo / 'docs/change.md').write_text('base\n')
        self.git('add', '.')
        self.git('commit', '-qm', 'Base')
        self.base = self.git('rev-parse', 'HEAD')
        (self.repo / 'docs/change.md').write_text('candidate\n')
        self.git('commit', '-qam', 'Candidate')
        self.head = self.git('rev-parse', 'HEAD')
        self.profiles = self.root / 'profiles'
        self.profiles.mkdir()
        for axis, model in MODELS.items():
            (self.profiles / ('reviewer-' + axis + '.md')).write_text(
                '---\nmodel: ' + model + '\npermission:\n  edit: deny\n'
                '---\nRead-only ' + axis + ' review.\n')
        self.bin = self.root / 'bin'
        self.bin.mkdir()
        shim = self.root / 'shim'
        shim.mkdir()
        api_data = {'state': 'open', 'draft': True,
                    'body': 'handoff\n' + PR_MARKER + '\n',
                    'head': {'sha': self.head,
                             'ref': 'bootstrap/recovery-foundation-41-test',
                             'repo': {'full_name': REPO}},
                    'base': {'sha': self.base, 'ref': 'main',
                             'repo': {'full_name': REPO}}}
        shim_code = '''import io,json,pathlib,urllib.request
pr = PR_DATA
comments = pathlib.Path(COMMENTS_PATH)
def request(req, timeout=30):
    path = req.full_url.split('/repos/')[1].split('/',2)[2].split('?')[0]
    if req.get_method() == 'POST':
        entries = json.loads(comments.read_text()) if comments.exists() else []
        entries.append(json.loads(req.data.decode()))
        comments.write_text(json.dumps(entries))
        value = {'id': 1}
    elif path == 'pulls/91': value = pr
    else: raise AssertionError(path)
    return io.BytesIO(json.dumps(value).encode())
urllib.request.urlopen = request
'''
        (shim / 'sitecustomize.py').write_text(
            shim_code.replace('PR_DATA', repr(api_data)).replace(
                'COMMENTS_PATH', repr(str(self.root / 'comments.json'))))
        self.env = dict(os.environ,
                        PATH=str(self.bin) + os.pathsep + os.environ['PATH'],
                        PYTHONPATH=str(shim), PYTHONDONTWRITEBYTECODE='1',
                        GH_TOKEN='github-test-token',
                        OPENCODE_ZEN_API_KEY='zen-test-placeholder')

    def provider(self, status='PASS', wrong_head=False, mutate=False,
                 silent=False):
        code = r'''import json,os,pathlib,re,sys
if '--version' in sys.argv:
    print('VERSION'); sys.exit(0)
assert 'GH_TOKEN' not in os.environ and 'GITHUB_TOKEN' not in os.environ and 'PYTHONPATH' not in os.environ
if SILENT:
    print(json.dumps({'type':'ping'})); sys.exit(0)
prompt = sys.argv[-1]
head = re.search(r'Reviewed HEAD: ([0-9a-f]{40})', prompt).group(1)
axis = re.search(r'Review axis: (spec|standards)', prompt).group(1)
model = sys.argv[sys.argv.index('--model') + 1]
if WRONG_HEAD: head = 'b' * 40
if MUTATE: pathlib.Path('docs/change.md').write_text('forbidden reviewer mutation')
marker = '<!-- review-result: axis=%s model=%s head=%s result=%s -->' % (axis,model,head,STATUS)
print(json.dumps({'type':'text','part':{'text':'intermediate-text-not-a-report'}}))
print(json.dumps({'type':'text','part':{'text':'Independent final findings\n'+marker}}))
'''
        path = self.bin / 'opencode'
        path.write_text('#!' + sys.executable + '\n' + code.replace(
            'VERSION', VERSION).replace('WRONG_HEAD',
                                        repr(wrong_head)).replace(
                                            'MUTATE', repr(mutate)).replace(
                                                'STATUS', repr(status)).replace(
                                                    'SILENT', repr(silent)))
        path.chmod(0o755)

    def run_review(self, axis='spec', output=None):
        output = output or self.root / ('evidence-' + axis)
        process = subprocess.run(
            [sys.executable, str(REVIEW), '--pr', '91', '--axis', axis,
             '--head', self.head, '--base', self.base,
             '--workspace', str(self.repo),
             '--profiles', str(self.profiles), '--evidence', str(output)],
            env=self.env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=180)
        return process, json.loads(process.stdout.decode()), output

    def comments(self):
        path = self.root / 'comments.json'
        return json.loads(path.read_text()) if path.exists() else []

    def test_spec_and_standards_publish_exact_head_reports_separately(self):
        self.provider()
        for axis in ('spec', 'standards'):
            process, result, output = self.run_review(axis)
            self.assertEqual(process.returncode, 0,
                             process.stderr.decode())
            self.assertEqual(result['status'], 'PASS')
            self.assertEqual(result['model'], MODELS[axis])
            report = json.loads((output / result['report']).read_text())
            self.assertEqual(report['head'], self.head)
            self.assertEqual(report['axis'], axis)
            self.assertEqual(report['model'], MODELS[axis])
            self.assertNotIn('intermediate-text', report['report'])
        posted = self.comments()
        self.assertEqual(len(posted), 2)
        for comment in posted:
            self.assertIn(self.head, comment['body'])
            self.assertNotIn('intermediate-text', comment['body'])
        self.assertEqual((self.repo / 'docs/change.md').read_text(),
                         'candidate\n')
        self.assertEqual(self.git('status', '--porcelain'), '')

    def test_fail_is_preserved_and_published_but_never_passes(self):
        self.provider('FAIL')
        process, result, output = self.run_review()
        self.assertNotEqual(process.returncode, 0)
        self.assertEqual(result['status'], 'FAIL')
        self.assertTrue(result['published'])
        stored = json.loads((output / result['report']).read_text())
        self.assertEqual(stored['result'], 'FAIL')
        self.assertEqual(len(self.comments()), 1)

    def test_needs_decision_never_approves(self):
        self.provider('NEEDS-DECISION')
        process, result, output = self.run_review()
        self.assertNotEqual(process.returncode, 0)
        self.assertEqual(result['status'], 'NEEDS-DECISION')
        self.assertTrue(result['published'])

    def test_missing_report_never_approves(self):
        self.provider(silent=True)
        process, result, output = self.run_review()
        self.assertNotEqual(process.returncode, 0)
        self.assertEqual(result['reason'], 'model-no-text')
        self.assertEqual(self.comments(), [])

    def test_foreign_sha_report_cannot_publish_or_approve(self):
        self.provider(wrong_head=True)
        process, result, output = self.run_review()
        self.assertNotEqual(process.returncode, 0)
        self.assertEqual(result['reason'], 'review-marker-invalid')
        self.assertEqual(self.comments(), [])

    def test_reviewer_mutation_cannot_publish_or_approve(self):
        self.provider(mutate=True)
        process, result, output = self.run_review()
        self.assertNotEqual(process.returncode, 0)
        self.assertEqual(result['reason'], 'review-mutated-candidate')
        self.assertEqual(self.comments(), [])

    def test_evidence_inside_candidate_is_rejected(self):
        self.provider()
        output = self.repo / 'invalid-evidence'
        process, result, _ = self.run_review(output=output)
        self.assertNotEqual(process.returncode, 0)
        self.assertEqual(result['reason'], 'review-input-invalid')
        self.assertEqual(self.git('status', '--porcelain'), '')
        self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
