"""Gate contract: mandatory application inputs and actual compatibility commands."""
import importlib.util
import pathlib
import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('agent_gates', ROOT / 'tools/agent_gates.py')
GATES = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GATES)


class GateContract(unittest.TestCase):
    def test_documentation_only_base_cannot_report_green(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(RuntimeError):
                GATES.commands(pathlib.Path(directory))

    def test_application_gate_requires_suite_rpm_and_compatibility(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = pathlib.Path(directory)
            for name in ('module/backend/entry.py', 'module/module.xml', 'tests/test_call.py', 'tests/test_admin.py', 'tools/build-rpm.py', 'module/page.php'):
                path = workspace / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('')
            checks = GATES.commands(workspace)
            self.assertTrue(any(GATES.SUITE_CODE in command for command in checks))
            self.assertIn(['php', '-l', 'module/page.php'], checks)
            self.assertTrue(any(command[-1] == 'tools/build-rpm.py' for command in checks))
            docker = [command for command in checks if command[0] == 'docker']
            for image in ('python:3.6', 'python:3.9', 'python:3.12', 'php:8.2-cli'):
                self.assertTrue(any(image in command for command in docker), image)
            php = [command for command in docker if 'php:8.2-cli' in command][0]
            self.assertIn('nobody', php[-1])
            self.assertIn('*web.py', php[-1])
            self.assertIn('test_pbx_state.py', php[-1])
            self.assertTrue(all(str(workspace)+':/project:ro' in command for command in docker))
            self.assertTrue(all('/project/artifacts:rw,mode=1777' in command for command in docker))

    def test_nonroot_runner_uses_noninteractive_sudo_for_lifecycle_suite(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = pathlib.Path(directory)
            for name in ('module/backend/entry.py', 'module/module.xml', 'tests/test_call.py', 'tests/test_admin.py', 'tools/build-rpm.py'):
                path = workspace / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('')
            with patch.object(GATES.os, 'geteuid', return_value=1001):
                command = GATES.commands(workspace)[0]
            self.assertEqual(command[:4], ['sudo', '-n', '--', sys.executable])
            self.assertIn(GATES.SUITE_CODE, command)

    def test_empty_full_and_targeted_suites_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = pathlib.Path(directory)
            (workspace/'tests').mkdir()
            (workspace/'tests/test_empty.py').write_text('')
            for pattern in ('test*.py', '*web.py', 'test_pbx_state.py'):
                result = subprocess.run(GATES.suite_command(sys.executable, pattern), cwd=str(workspace),
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                self.assertEqual(result.returncode, 5, result.stdout+result.stderr)
                self.assertIn('Discovered 0 tests', result.stdout)

    def test_real_gate_process_does_not_forward_credentials_to_checks(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = pathlib.Path(directory)
            for name in ('module/backend/entry.py', 'module/module.xml', 'tests/test_call.py', 'tests/test_admin.py', 'tools/build-rpm.py', 'bin/php', 'bin/docker'):
                path = workspace / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('')
            check = ('import os\n'
                     'assert not any(name in os.environ for name in ("GH_TOKEN", "GITHUB_TOKEN", "OPENCODE_ZEN_API_KEY"))\n')
            (workspace/'tests/test_call.py').write_text(check+'import unittest\nclass Fixture(unittest.TestCase):\n    def test_runs(self):\n        self.assertTrue(True)\n')
            (workspace/'tools/build-rpm.py').write_text(check)
            for tool in ('php', 'docker'):
                path = workspace/'bin'/tool
                path.write_text('#!'+sys.executable+'\n'+check)
                path.chmod(0o755)
            environment = dict(os.environ, PATH=str(workspace/'bin')+os.pathsep+os.environ['PATH'],
                               GH_TOKEN='fake-github', GITHUB_TOKEN='fake-github', OPENCODE_ZEN_API_KEY='fake-zen')
            result = subprocess.run([sys.executable, str(ROOT/'tools/agent_gates.py'), str(workspace)],
                                    env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
            self.assertNotIn('fake-', result.stdout+result.stderr)
            self.assertFalse((workspace/'tests/__pycache__').exists())


if __name__ == '__main__':
    unittest.main()
