"""Offline orchestration tests: real git boundaries, fake model/GitHub edges."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('agent_flow', Path(__file__).resolve().parents[2] / 'tools/agent_flow.py')
flow = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(flow)


class API:
    token = 'github-secret-do-not-forward'

    def __init__(self, sha='a' * 40):
        self.base = sha
        self.permission = 'write'
        self.issue = {'number': 42, 'title': 'Approved lab behavior', 'state': 'open',
                      'labels': [{'name': 'ready-for-agent'}], 'body': 'Only the requested application change'}
        self.dependencies = []
        self.writes = []
        self.pr = {'number': 77, 'state': 'open', 'draft': True, 'body': '<!-- callflow-agent-issue:42 -->',
                   'base': {'ref': 'main', 'repo': {'full_name': flow.REPOSITORY}},
                   'head': {'ref': 'feat/callflow-agent-issue-42', 'sha': sha, 'repo': {'full_name': flow.REPOSITORY}},
                   'html_url': 'https://github.com/' + flow.REPOSITORY + '/pull/77'}

    def request(self, path, method='GET', data=None):
        if method != 'GET':
            self.writes.append((path, data))
            return {'html_url': 'https://github.com/' + flow.REPOSITORY + '/pull/88'}
        if path.endswith('/permission'):
            return {'permission': self.permission}
        if path.startswith('pulls/'):
            return self.pr
        if path == 'issues/2':
            return {'number': 2, 'body': 'Parent specification'}
        return self.issue

    def pages(self, path):
        if path.endswith('/blocked_by'):
            return self.dependencies
        return []

    def sha(self, branch):
        return self.base


def event(mode='ticket'):
    value = {'repository': {'full_name': flow.REPOSITORY, 'default_branch': 'main'}, 'action': 'created',
             'comment': {'body': '/agent-ticket', 'author_association': 'OWNER', 'user': {'login': 'JonatanGarbuyo'}},
             'issue': {'number': 42}}
    if mode == 'fix':
        value['comment']['body'] = '/agent-fix-cycle'
        value['issue']['pull_request'] = {'url': 'not-trusted-for-routing'}
    return value


class Guard(unittest.TestCase):
    def test_exact_command_authority_and_trusted_ref(self):
        api = API()
        self.assertEqual(flow.guard(event(), 'issue_comment', 'refs/heads/main', api)['mode'], 'ticket')
        with self.assertRaisesRegex(flow.Stop, 'untrusted-control-ref'):
            flow.guard(event(), 'issue_comment', 'refs/heads/evil', api)
        api.permission = 'read'
        with self.assertRaisesRegex(flow.Stop, 'actor-not-authorized'):
            flow.guard(event(), 'issue_comment', 'refs/heads/main', api)

    def test_ordinary_comment_and_wrong_command_surface(self):
        ordinary = event()
        ordinary['comment']['body'] = 'Please see /agent-ticket later'
        self.assertEqual(flow.guard(ordinary, 'issue_comment', 'refs/heads/main', API()), {'run': 'false'})
        wrong = event()
        wrong['issue']['pull_request'] = {}
        with self.assertRaisesRegex(flow.Stop, 'command-surface-invalid'):
            flow.guard(wrong, 'issue_comment', 'refs/heads/main', API())

    def test_dispatch_inputs_and_optional_readonly_actor(self):
        dispatch = {'repository': {'full_name': flow.REPOSITORY, 'default_branch': 'main'},
                    'inputs': {'operation': 'probe', 'base': 'main'}, 'sender': {'login': 'JonatanGarbuyo'}}
        self.assertEqual(flow.guard(dispatch, 'workflow_dispatch', 'refs/heads/main', API())['number'], '0')
        dispatch['inputs']['operation'] = 'ticket'
        dispatch['inputs']['number'] = 'not-a-number'
        with self.assertRaisesRegex(flow.Stop, 'number-invalid'):
            flow.guard(dispatch, 'workflow_dispatch', 'refs/heads/main', API())

    def test_ready_label_never_overrides_dependency_or_other_state(self):
        api = API()
        api.dependencies = [{'state': 'open'}]
        with self.assertRaisesRegex(flow.Stop, 'ticket-blocked'):
            flow.authorized_issue(api, 42)
        api.dependencies = []
        api.issue['labels'].append({'name': 'optional'})
        with self.assertRaisesRegex(flow.Stop, 'ticket-not-approved'):
            flow.authorized_issue(api, 42)
        api.issue['labels'] = [{'name': 'ready-for-agent'}]
        api.issue['state'] = 'closed'
        with self.assertRaisesRegex(flow.Stop, 'ticket-not-approved'):
            flow.authorized_issue(api, 42)

    def test_fix_requires_own_draft_deterministic_branch_and_marker(self):
        api = API()
        self.assertEqual(flow.approved_pr(api, 77)[1]['number'], 42)
        for mutation in ('draft', 'foreign', 'branch', 'marker'):
            api = API()
            if mutation == 'draft': api.pr['draft'] = False
            if mutation == 'foreign': api.pr['head']['repo']['full_name'] = 'someone/else'
            if mutation == 'branch': api.pr['head']['ref'] = 'feat/callflow-generic-profile'
            if mutation == 'marker': api.pr['body'] = 'Closes #42'
            with self.assertRaises(flow.Stop):
                flow.approved_pr(api, 77)

    def test_dependency_pagination_reads_every_page(self):
        api = object.__new__(flow.GitHub)
        items = [{'state': 'closed'}] * 100
        with patch.object(api, 'request', side_effect=[items, [{'state': 'open'}]]) as request:
            result = api.pages('issues/42/dependencies/blocked_by')
        self.assertEqual(result[-1]['state'], 'open')
        self.assertIn('page=2', request.call_args.args[0])


class ModelPolicy(unittest.TestCase):
    def test_free_main_small_models_and_token_allowlist(self):
        source = {'PATH': '/bin', 'GH_TOKEN': 'secret', 'GITHUB_TOKEN': 'secret', 'OPENCODE_ZEN_API_KEY': 'key',
                  'OPENAI_API_KEY': 'paid', 'OPENCODE_CONFIG_CONTENT': 'unsafe', 'ACTIONS_RUNTIME_TOKEN': 'secret'}
        self.assertEqual(flow.clean_environment(source), {'PATH': '/bin'})
        for model in flow.MODELS.values():
            config = flow.config(model, True)
            self.assertEqual(config['model'], config['small_model'])
            self.assertEqual(config['enabled_providers'], ['opencode'])
            self.assertEqual(config['share'], 'disabled')
            self.assertEqual(config['permission']['bash']['*'], 'deny')
            self.assertEqual(config['permission']['task'], 'deny')
            self.assertEqual(config['permission']['edit']['tools/agent_*'], 'deny')
        with self.assertRaisesRegex(flow.Stop, 'model-not-free'):
            flow.config('openai/paid-model', True)

    def test_error_and_missing_output_fail_closed_without_publishing_transcript(self):
        text = json.dumps({'type': 'text', 'part': {'text': 'marker'}})
        self.assertEqual(flow.parse_model_output(text), 'marker')
        with self.assertRaisesRegex(flow.Stop, 'model-error'):
            flow.parse_model_output(text + '\n' + json.dumps({'type': 'error', 'error': 'secret value'}))
        with self.assertRaisesRegex(flow.Stop, 'model-no-text'):
            flow.parse_model_output('not json\n' + json.dumps({'type': 'step_finish'}))

    def test_timeout_terminates_process_group(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(flow.Stop, 'timeout'):
                flow.command(['python3', '-c', 'import time; time.sleep(20)'], temp,
                             flow.clean_environment(), timeout=0.05)


class GitBoundary(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=str(Path(__file__).resolve().parents[3]))
        self.root = Path(self.temp.name)
        self.repo = self.root / 'candidate'
        self.repo.mkdir()
        subprocess.check_call(['git', 'init', '-q', '-b', 'main', str(self.repo)])
        flow.git(self.repo, 'config', 'user.name', 'Fixture')
        flow.git(self.repo, 'config', 'user.email', 'fixture@example.invalid')
        for path, value in {'module/backend/entry.py': '# lab\n', 'tests/test_application.py': '# fixture\n',
                            '.gitignore': '__pycache__/\nignored/\n'}.items():
            file = self.repo / path
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text(value)
        flow.git(self.repo, 'add', '--all')
        flow.git(self.repo, 'commit', '-qm', 'Fixture base')
        self.sha = flow.git(self.repo, 'rev-parse', 'HEAD')
        self.api = API(self.sha)
        self.remote = self.root / 'remote.git'
        subprocess.check_call(['git', 'init', '--bare', '-q', str(self.remote)])
        flow.git(self.repo, 'remote', 'add', 'origin', str(self.remote))
        flow.git(self.repo, 'push', '-q', 'origin', 'main')
        self.args = argparse.Namespace(mode='ticket', number=42, base='main', workspace=str(self.repo))

    def tearDown(self):
        self.temp.cleanup()

    def implement(self, workspace, axis, prompt, writable=False):
        if axis == 'implement':
            with (workspace / 'module/backend/entry.py').open('a') as out:
                out.write('# approved behavior\n')
            return 'Implementation complete'
        return 'CFH_REVIEW:' + axis + ':' + flow.git(workspace, 'rev-parse', 'HEAD') + ':PASS'

    def execute(self, worker=None, gates=None):
        with patch.object(flow, 'prepare_workspace'), patch.object(flow, 'worker', side_effect=worker or self.implement), \
             patch.object(flow, 'run_gates', side_effect=gates):
            return flow.execute(self.args, self.api)

    def branch_exists(self):
        result = subprocess.run(['git', '--git-dir', str(self.remote), 'show-ref', '--verify',
                                 'refs/heads/feat/callflow-agent-issue-42'], capture_output=True)
        return result.returncode == 0

    def test_publish_only_checks_and_both_reviews_same_committed_sha(self):
        seen = []
        def worker(workspace, axis, prompt, writable=False):
            if axis != 'implement': seen.append((axis, flow.git(workspace, 'rev-parse', 'HEAD')))
            return self.implement(workspace, axis, prompt, writable)
        result = self.execute(worker)
        self.assertEqual(result['status'], 'draft-published')
        self.assertEqual(seen, [('spec', result['sha']), ('standards', result['sha'])])
        self.assertTrue(self.branch_exists())
        self.assertTrue(self.api.writes[-1][1]['draft'])
        self.assertEqual(flow.snapshot(self.repo), (result['sha'], ''))

    def test_failed_checks_model_or_review_never_push(self):
        with self.assertRaisesRegex(flow.Stop, 'gate-failed'):
            self.execute(gates=lambda *args: (_ for _ in ()).throw(flow.Stop('gate-failed')))
        self.assertFalse(self.branch_exists())
        self.assertFalse(self.api.writes)

    def test_worker_head_change_and_protected_paths_fail_before_gates(self):
        for name in ('AGENTS.md', '.github/workflows/evil.yml', 'tools/agent_flow.py', 'tests/automation/evil.py', '.env'):
            file = self.repo / name
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text('forbidden')
            with self.assertRaisesRegex(flow.Stop, 'protected-path-change'):
                flow.inspect_changes(self.repo, self.sha)
            file.unlink()
        with (self.repo / 'module/backend/entry.py').open('a') as out: out.write('# changed\n')
        flow.git(self.repo, 'add', '--all')
        flow.git(self.repo, 'commit', '-qm', 'Worker illegally commits')
        with self.assertRaisesRegex(flow.Stop, 'worker-changed-head'):
            flow.inspect_changes(self.repo, self.sha)

    def test_readonly_reviewer_cannot_modify_even_ignored_files(self):
        def worker(workspace, axis, prompt, writable=False):
            output = self.implement(workspace, axis, prompt, writable)
            if axis == 'spec':
                (workspace / 'ignored').mkdir()
                (workspace / 'ignored' / 'secret').write_text('mutated')
            return output
        with self.assertRaisesRegex(flow.Stop, 'review-mutated-candidate'):
            self.execute(worker)
        self.assertFalse(self.branch_exists())

    def test_base_change_during_review_stops_push(self):
        def worker(workspace, axis, prompt, writable=False):
            output = self.implement(workspace, axis, prompt, writable)
            if axis == 'standards': self.api.base = 'b' * 40
            return output
        with self.assertRaisesRegex(flow.Stop, 'base-changed'):
            self.execute(worker)
        self.assertFalse(self.branch_exists())

    def test_bounded_review_failure_and_decision_never_publish(self):
        calls = []
        def worker(workspace, axis, prompt, writable=False):
            calls.append(axis)
            if axis == 'implement': return self.implement(workspace, axis, prompt, writable)
            return 'CFH_REVIEW:' + axis + ':' + flow.git(workspace, 'rev-parse', 'HEAD') + ':FAIL'
        with self.assertRaisesRegex(flow.Stop, 'review-failed'):
            self.execute(worker)
        self.assertEqual(calls.count('implement'), 2)
        self.assertFalse(self.branch_exists())

    def test_reject_project_config_and_symlink(self):
        (self.repo / 'opencode.json').write_text('{"plugin":["unsafe"]}')
        with self.assertRaisesRegex(flow.Stop, 'project-agent-configuration-present'):
            flow.reject_project_configuration(self.repo)
        (self.repo / 'opencode.json').unlink()
        (self.repo / 'module/link').symlink_to('/tmp')
        with self.assertRaisesRegex(flow.Stop, 'symlink-change'):
            flow.inspect_changes(self.repo, self.sha)

    def test_worker_env_includes_only_zen_key_and_isolated_config(self):
        calls = []
        def command(argv, cwd, env, timeout):
            calls.append((argv, env))
            if '--version' in argv: return flow.VERSION
            return json.dumps({'type': 'text', 'part': {'text': 'done'}})
        with patch.dict(os.environ, {'GH_TOKEN': 'github-token', 'OPENCODE_ZEN_API_KEY': 'zen-key',
                                     'ANTHROPIC_API_KEY': 'paid-token'}), patch.object(flow, 'command', side_effect=command):
            self.assertEqual(flow.worker(self.repo, 'implement', 'lab prompt', True), 'done')
        env = calls[-1][1]
        self.assertNotIn('GH_TOKEN', env)
        self.assertNotIn('ANTHROPIC_API_KEY', env)
        self.assertEqual(env['OPENCODE_ZEN_API_KEY'], 'zen-key')
        self.assertEqual(json.loads(env['OPENCODE_CONFIG_CONTENT'])['small_model'], flow.MODELS['implement'])
        self.assertEqual(env['OPENCODE_DISABLE_DEFAULT_PLUGINS'], 'true')
        self.assertFalse(Path(env['XDG_DATA_HOME']).exists())


if __name__ == '__main__':
    unittest.main()
