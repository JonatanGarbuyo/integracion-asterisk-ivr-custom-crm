import json
from test_admin import Administration
from agi_harness import call


class CallExecution(Administration):
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
