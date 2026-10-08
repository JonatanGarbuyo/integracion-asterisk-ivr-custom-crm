import json
import subprocess
import sys
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from tests.agi_harness import ROOT


class MockCRMTest(unittest.TestCase):
    def test_mock_supports_lookup_notification_and_operator_inbox(self):
        process = subprocess.Popen([sys.executable, '-m', 'lab.mock_crm', '--port', '0'],
            cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        try:
            startup = process.stdout.readline()
            self.assertTrue(startup.startswith('{'), process.stderr.read() if process.poll() is not None else startup)
            base = json.loads(startup)['url']
            with urlopen(base + '/affiliates?cuil=20123456786', timeout=2) as response:
                self.assertEqual({'affiliate_id': 'af-demo-1', 'obra_social': 'OS_A'}, json.load(response))
            payload = {'event_id': 'event-1', 'interaction_id': 'call-1', 'affiliate_id': 'af-demo-1',
                'crm_user_id': 'crm-user-a', 'member_interface': 'PJSIP/1001', 'queue': '601',
                'answered_at': '2026-10-08T00:00:00+00:00', 'event_type': 'queue_member_answered',
                'schema_version': 1, 'pbx_id': 'pbx-lab', 'uniqueid': '1.1', 'linkedid': '1.1'}
            with urlopen(Request(base + '/answered', data=json.dumps(payload).encode(),
                                 headers={'Content-Type': 'application/json'}), timeout=2) as response:
                self.assertEqual(204, response.status)
            with urlopen(base + '/notifications?crm_user_id=crm-user-a', timeout=2) as response:
                self.assertEqual([payload], json.load(response))
            with urlopen(base + '/notifications?crm_user_id=crm-user-b', timeout=2) as response:
                self.assertEqual([], json.load(response))
            with self.assertRaises(HTTPError) as missing:
                urlopen(base + '/affiliates?cuil=20999999999', timeout=2)
            self.assertEqual(404, missing.exception.code)
        finally:
            process.terminate()
            process.communicate(timeout=3)
