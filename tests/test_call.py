import json
import pathlib
import os
import signal
import unittest
from boundary_support import AdminBoundary
from agi_harness import call


class CallExecution(AdminBoundary, unittest.TestCase):
    def test_callerid_runs_json_handler_enriches_context_and_selects_next_destination(self):
        profile = self.profile()
        profile['input_source'] = 'callerid'
        saved = self.request('save', profile=profile,
                             expected_version=self.request('describe')['configuration_version'])
        variables, commands, _ = call(self.config)
        self.assertEqual(variables['CALLFLOW_PROFILE_IDENTIFIER'], 'welcome')
        self.assertEqual(variables['CALLFLOW_CONFIGURATION_VERSION'], saved['configuration_version'])
        self.assertEqual(variables['CALLFLOW_NEXT_DESTINATION'], 'ext-local,201,1')
        self.assertEqual(variables['CALLFLOW_HANDLER_STATUS'], 'completed')
        context = json.loads(variables['CALLFLOW_CONTEXT_JSON'])
        self.assertEqual(context, {'greeting': 'Buen día', 'input_value': '555123'})
        self.assertNotIn('private-token', '\n'.join(commands))

    def test_none_dtmf_and_channel_inputs_use_same_handler_without_business_rules(self):
        for source, expected in [('none', ''), ('dtmf', '00123'), ('channel', 'customer-key')]:
            profile = self.profile()
            profile.update(input_source=source, input_variable='ACCOUNT_KEY')
            self.request('save', profile=profile,
                         expected_version=self.request('describe')['configuration_version'])
            variables, _, _ = call(self.config, digits='00123', variables={'ACCOUNT_KEY': 'customer-key'})
            self.assertEqual(json.loads(variables['CALLFLOW_CONTEXT_JSON'])['input_value'], expected)

    def test_handler_budget_and_unapproved_destination_use_explicit_fallback(self):
        self.extensions = pathlib.Path(self.directory.name) / 'extensions'
        module = self.extensions / 'custom'
        module.mkdir(parents=True)
        (module / 'manifest.json').write_text(json.dumps(dict(
            identifier='custom', title='Custom', contract_version=1,
            command=['@python', 'handler.py'], fields={})))
        profile = self.profile()
        profile.update(extension='custom', settings={}, execution_budget_ms=100)
        self.request('save', profile=profile,
                     expected_version=self.request('describe')['configuration_version'])
        for script in ['import time; time.sleep(10)',
                       'print(\'{"contract_version":1,"action":"route","destination":"ext-local,999,1"}\')',
                       'print(\'{"contract_version":99,"action":"continue"}\')']:
            (module / 'handler.py').write_text(script)
            variables, _, elapsed = call(self.config, extensions=self.extensions)
            self.assertLess(elapsed, 1.5)
            self.assertEqual(variables['CALLFLOW_HANDLER_STATUS'], 'fallback')
            self.assertEqual(variables['CALLFLOW_NEXT_DESTINATION'], 'ext-local,202,1')

    def test_hangup_terminates_handler_group_instead_of_orphaning_it(self):
        self.extensions = pathlib.Path(self.directory.name) / 'extensions'
        module = self.extensions / 'slow'
        module.mkdir(parents=True)
        pidfile = pathlib.Path(self.directory.name) / 'handler.pid'
        (module / 'manifest.json').write_text(json.dumps(dict(
            identifier='slow', title='Slow', contract_version=1,
            command=['@python', 'handler.py'], fields={})))
        (module / 'handler.py').write_text('import os,pathlib,time\npathlib.Path({!r}).write_text(str(os.getpid()))\ntime.sleep(30)\n'.format(str(pidfile)))
        profile = self.profile()
        profile.update(extension='slow', settings={}, execution_budget_ms=5000)
        self.request('save', profile=profile,
                     expected_version=self.request('describe')['configuration_version'])
        try:
            _, _, elapsed = call(self.config, extensions=self.extensions, hangup_after=0.3)
            self.assertLess(elapsed, 1.5)
            self.assertTrue(pidfile.exists(), 'Handler must have started before hangup')
            pid = int(pidfile.read_text())
            with self.assertRaises(ProcessLookupError):
                os.kill(pid, 0)
        finally:
            if pidfile.exists():
                try:
                    os.killpg(int(pidfile.read_text()), signal.SIGKILL)
                except ProcessLookupError:
                    pass
