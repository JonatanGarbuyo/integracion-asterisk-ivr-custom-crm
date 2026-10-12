"""CLI with external GitHub HTTP/OpenCode doubles and real Git; no internal mocks."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[2] / 'tools/agent_review.py'
REPO = 'JonatanGarbuyo/integracion-asterisk-ivr-custom-crm'
MODELS = {'spec': 'opencode/muse-spark-1.3-contributor-free',
          'standards': 'opencode/mimo-v2.6-flash-free'}


class BootstrapReviews(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.repo = self.root / 'candidate'
        self.repo.mkdir()
        self.git('init', '-q')
        self.git('config', 'user.name', 'Fixture')
        self.git('config', 'user.email', 'fixture@example.invalid')
        (self.repo / 'docs').mkdir()
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
                '---\nmodel: ' + model + '\npermission:\n  edit: deny\n---\nRead-only ' + axis + ' review.\n')
        self.bin = self.root / 'bin'
        self.bin.mkdir()
        shim = self.root / 'shim'
        shim.mkdir()
        api_data = {'state': 'open', 'draft': True, 'user': {'login': 'JonatanGarbuyo'},
                    'body': '<!-- callflow-operator-bootstrap:41 -->',
                    'head': {'sha': self.head, 'ref': 'bootstrap/agent-evidence-41-pr',
                             'repo': {'full_name': REPO}},
                    'base': {'sha': self.base, 'ref': 'main', 'repo': {'full_name': REPO}}}
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
    elif path == 'git/ref/heads/main': value = {'object': {'sha': pr['head']['sha']}}
    elif path.endswith('/comments') or path.endswith('/blocked_by'): value = []
    elif path.startswith('issues/'): value = {'number': int(path.split('/')[1]), 'state':'open', 'labels':[{'name':'ready-for-agent'}], 'body':'Approved operator bootstrap only'}
    else: raise AssertionError(path)
    return io.BytesIO(json.dumps(value).encode())
urllib.request.urlopen = request
'''
        (shim / 'sitecustomize.py').write_text(shim_code.replace('PR_DATA', repr(api_data)).replace(
            'COMMENTS_PATH', repr(str(self.root / 'comments.json'))))
        self.env = dict(os.environ, PATH=str(self.bin) + os.pathsep + os.environ['PATH'],
                        PYTHONPATH=str(shim), PYTHONDONTWRITEBYTECODE='1', GH_TOKEN='github-test-token',
                        OPENCODE_ZEN_API_KEY='zen-test-placeholder')

    def tearDown(self):
        self.temp.cleanup()

    def git(self, *args):
        return subprocess.check_output(['git'] + list(args), cwd=str(self.repo)).decode().strip()

    def provider(self, status='PASS', wrong_head=False, mutate=False):
        code = r'''import json,os,pathlib,re,sys
if '--version' in sys.argv:
    print('1.18.30'); sys.exit(0)
assert 'GH_TOKEN' not in os.environ and 'GITHUB_TOKEN' not in os.environ and 'PYTHONPATH' not in os.environ
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
        path.write_text('#!' + sys.executable + '\n' + code.replace('WRONG_HEAD', repr(wrong_head)).replace(
            'MUTATE', repr(mutate)).replace('STATUS', repr(status)))
        path.chmod(0o755)

    def run_review(self, axis='spec'):
        output = self.root / ('evidence-' + axis)
        process = subprocess.run([sys.executable, str(SCRIPT), '--pr', '91', '--axis', axis,
                                  '--head', self.head, '--base', self.base, '--workspace', str(self.repo),
                                  '--profiles', str(self.profiles), '--evidence', str(output)],
                                 env=self.env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return process, json.loads(process.stdout.decode()), output

    def test_independent_profiles_publish_exact_head_without_transcript_or_model_github_token(self):
        self.provider()
        for axis in ('spec', 'standards'):
            process, result, output = self.run_review(axis)
            self.assertEqual(process.returncode, 0, process.stderr.decode())
            self.assertEqual(result['status'], 'PASS')
            report = json.loads((output / result['report']).read_text())
            self.assertEqual(report['head'], self.head)
            self.assertEqual(report['axis'], axis)
            self.assertEqual(report['model'], MODELS[axis])
            self.assertNotIn('intermediate-text', report['report'])
        comments = json.loads((self.root / 'comments.json').read_text())
        self.assertEqual(len(comments), 2)
        for comment in comments:
            self.assertIn('head=' + self.head, comment['body'])
            self.assertNotIn('intermediate-text', comment['body'])
        self.assertEqual(self.git('status', '--porcelain'), '')

    def test_fail_is_preserved_and_published_but_never_pass(self):
        self.provider('FAIL')
        process, result, output = self.run_review()
        self.assertNotEqual(process.returncode, 0)
        self.assertEqual(result['status'], 'FAIL')
        self.assertTrue(result['published'])
        self.assertEqual(json.loads((output / result['report']).read_text())['result'], 'FAIL')

    def test_wrong_head_report_cannot_publish_or_approve(self):
        self.provider(wrong_head=True)
        process, result, output = self.run_review()
        self.assertNotEqual(process.returncode, 0)
        self.assertEqual(result['reason'], 'review-marker-invalid')
        self.assertFalse((self.root / 'comments.json').exists())

    def test_reviewer_mutation_cannot_publish_or_approve(self):
        self.provider(mutate=True)
        process, result, output = self.run_review()
        self.assertNotEqual(process.returncode, 0)
        self.assertEqual(result['reason'], 'review-mutated-candidate')
        self.assertFalse((self.root / 'comments.json').exists())

    def test_real_controller_gate_failure_keeps_validated_candidate_before_checks(self):
        # Real application Git/worktree and real failing gate; only GitHub/OpenCode are doubles.
        (self.repo / 'module/backend').mkdir(parents=True)
        (self.repo / 'module/backend/entry.py').write_text('# laboratory placeholder\n')
        (self.repo / 'tests').mkdir()
        (self.repo / 'tests/test_fixture.py').write_text('# laboratory placeholder\n')
        self.git('add', '.')
        self.git('commit', '-qm', 'Application fixture')
        start = self.git('rev-parse', 'HEAD')
        shim = self.root / 'shim/sitecustomize.py'
        shim.write_text(shim.read_text().replace(repr(self.head), repr(start)))
        provider = self.bin / 'opencode'
        provider.write_text('#!' + sys.executable + '\n' + r'''import json,os,pathlib,sys
if '--version' in sys.argv:
    print('1.18.30'); sys.exit(0)
assert 'GH_TOKEN' not in os.environ
pathlib.Path('docs/change.md').write_text('complete candidate before failed gate\n')
print(json.dumps({'type':'text','part':{'text':'Approved change complete'}}))
''')
        provider.chmod(0o755)
        controls = self.root / 'controls'
        (controls / 'tools').mkdir(parents=True)
        for name in ('agent_flow.py', 'agent_evidence.py', 'agent_gates.py'):
            (controls / 'tools' / name).write_bytes((SCRIPT.parent / name).read_bytes())
        subprocess.check_call(['git', 'init', '-q', str(controls)])
        subprocess.check_call(['git', 'config', 'user.name', 'Fixture'], cwd=str(controls))
        subprocess.check_call(['git', 'config', 'user.email', 'fixture@example.invalid'], cwd=str(controls))
        subprocess.check_call(['git', 'add', '.'], cwd=str(controls))
        subprocess.check_call(['git', 'commit', '-qm', 'Trusted controls'], cwd=str(controls))
        subprocess.check_call(['git', 'remote', 'add', 'origin', str(self.repo)], cwd=str(controls))
        evidence = self.root / 'controller-evidence'
        process = subprocess.run([sys.executable, str(controls / 'tools/agent_flow.py'), '--mode', 'ticket',
                                  '--number', '41', '--base', 'main', '--workspace', str(self.root / 'worktree'),
                                  '--evidence', str(evidence)], env=self.env, cwd=str(controls),
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertNotEqual(process.returncode, 0)
        result = json.loads((evidence / 'result.json').read_text())
        self.assertEqual(result['stage'], 'checks', process.stdout.decode())
        self.assertEqual(result['reason'], 'command-failed')
        self.assertEqual(result['candidate']['status'], 'complete')
        manifest = json.loads((evidence / result['candidate']['manifest']).read_text())
        self.assertEqual(manifest['base_sha'], start)
        self.assertEqual(manifest['head_sha'], result['sha'])
        folder = evidence / Path(result['candidate']['manifest']).parent
        content = (folder / manifest['files'][0]['artifact']).read_bytes()
        self.assertEqual(content, b'complete candidate before failed gate\n')


if __name__ == '__main__':
    unittest.main()
