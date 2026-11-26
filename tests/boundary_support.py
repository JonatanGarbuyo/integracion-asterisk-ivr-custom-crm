"""Shared setup for public process boundaries, without inherited test methods."""
import json
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
ENTRY = ROOT / 'module' / 'backend' / 'entry.py'


class AdminBoundary:
    def setUp(self):
        artifacts = ROOT / 'artifacts'
        artifacts.mkdir(exist_ok=True)
        self.directory = tempfile.TemporaryDirectory(dir=str(artifacts))
        self.addCleanup(self.directory.cleanup)
        self.config = pathlib.Path(self.directory.name) / 'profiles.conf'

    def request(self, action, **data):
        command = [sys.executable, str(ENTRY), '--config', str(self.config)]
        if hasattr(self, 'extensions'):
            command.extend(['--extensions', str(self.extensions)])
        process = subprocess.run(command + ['admin'], input=json.dumps(dict(action=action, **data)),
                                 universal_newlines=True, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, timeout=5)
        self.assertEqual(process.returncode, 0, process.stderr)
        return json.loads(process.stdout)

    def profile(self, identifier='welcome'):
        return dict(identifier=identifier, extension='example', enabled=True,
                    next_destination='ext-local,201,1', fallback_destination='ext-local,202,1',
                    execution_budget_ms=800, input_source='none',
                    settings={'greeting': 'Buen día', 'api_token': 'private-token'})
