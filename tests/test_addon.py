import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class AddonTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.custom = self.root / 'etc/asterisk/extensions_custom.conf'
        self.custom.parent.mkdir(parents=True)
        self.custom.write_text('[existing-custom]\nexten => s,1,NoOp(existing)\n')

    def tearDown(self):
        self.tmp.cleanup()

    def command(self, *args):
        return subprocess.run([sys.executable, str(ROOT / 'tools/addon.py')] + list(args),
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)

    def test_install_and_uninstall_preserve_existing_dialplan_and_operational_config(self):
        installed = self.command('install', '--root', str(self.root))
        self.assertEqual(0, installed.returncode, installed.stderr)
        self.assertIn('NoOp(existing)', self.custom.read_text())
        self.assertEqual(1, self.custom.read_text().count('#include issabel_crm_extensions.conf'))
        program = self.root / 'var/lib/asterisk/agi-bin/issabel-crm-identify.agi'
        self.assertTrue(program.stat().st_mode & 0o100)
        config = self.root / 'etc/asterisk/issabel_crm.conf'
        original = config.read_text().replace('fallback_queue = 600', 'fallback_queue = 699')
        config.write_text(original)
        self.assertEqual(0, self.command('install', '--root', str(self.root)).returncode)
        self.assertEqual(original, config.read_text())
        self.assertEqual(1, self.custom.read_text().count('#include issabel_crm_extensions.conf'))
        self.assertIn('CRM_DEST=699', (self.root / 'etc/asterisk/issabel_crm_extensions.conf').read_text())
        self.assertEqual(0, self.command('uninstall', '--root', str(self.root)).returncode)
        self.assertEqual('[existing-custom]\nexten => s,1,NoOp(existing)\n', self.custom.read_text())
        self.assertTrue(config.exists())
        self.assertFalse(program.exists())

    def test_staged_entrypoint_runs_without_importing_the_checkout(self):
        from tests.agi_harness import run_agi
        self.assertEqual(0, self.command('install', '--root', str(self.root)).returncode)
        config = self.root / 'etc/asterisk/issabel_crm.conf'
        variables, _, _, _ = run_agi('identify', config, digits=['', ''],
            export_pythonpath=False, entrypoint=self.root / 'var/lib/asterisk/agi-bin/issabel-crm-identify.agi')
        self.assertEqual('invalid_cuil', variables['CRM_RESULT'])

    def test_invalid_candidate_is_rejected_without_replacing_live_config(self):
        self.assertEqual(0, self.command('install', '--root', str(self.root)).returncode)
        config = self.root / 'etc/asterisk/issabel_crm.conf'
        original = config.read_bytes()
        candidate = self.root / 'candidate.conf'
        candidate.write_text(config.read_text().replace('queue:601', 'queue:601,evil,1'))
        result = self.command('apply', '--root', str(self.root), '--config', str(candidate))
        self.assertNotEqual(0, result.returncode)
        self.assertEqual(original, config.read_bytes())

    def test_dialplan_preserves_issabel_queue_and_outbound_routing(self):
        self.assertEqual(0, self.command('install', '--root', str(self.root)).returncode)
        text = (self.root / 'etc/asterisk/issabel_crm_extensions.conf').read_text()
        self.assertIn('Goto(ext-queues,${CRM_DEST},1)', text)
        self.assertIn('Set(VQ_AGI=issabel-crm-answer.agi)', text)
        self.assertIn('CRM_PREVIOUS_QAGI', text)
        self.assertIn('Dial(Local/${CRM_DEST}@from-internal/n,30,g)', text)
        self.assertNotIn('Queue(', text, 'must retain generated queue features')
