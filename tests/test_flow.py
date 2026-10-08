import json
import tempfile
import time
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from tests.agi_harness import run_agi


class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


class CRMHandler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        query = parse_qs(urlsplit(self.path).query)
        self.server.requests.append(query)
        self.server.lookup_auth.append(self.headers.get('Authorization'))
        time.sleep(self.server.lookup_delay)
        body = self.server.lookup_by_cuil.get(query.get('cuil', [''])[0], self.server.lookup_body)
        self.send_response(self.server.lookup_status)
        self.end_headers()
        try:
            if self.server.trickle:
                for byte in body:
                    self.wfile.write(bytes([byte]))
                    self.wfile.flush()
                    time.sleep(self.server.trickle)
            else:
                self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_POST(self):
        self.server.notify_auth.append(self.headers.get('Authorization'))
        self.server.notifications.append(json.loads(self.rfile.read(int(self.headers['Content-Length']))))
        self.server.received.set()
        time.sleep(self.server.notify_delay)
        self.send_response(self.server.notify_status)
        self.end_headers()


class FlowTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), CRMHandler)
        self.server.requests, self.server.notifications = [], []
        self.server.lookup_auth, self.server.notify_auth = [], []
        self.server.lookup_by_cuil = {}
        self.server.received = threading.Event()
        self.server.lookup_delay = self.server.notify_delay = self.server.trickle = 0
        self.server.lookup_status, self.server.notify_status = 200, 204
        self.server.lookup_body = json.dumps({"affiliate_id": "af-demo-1", "obra_social": "OS_A"}).encode()
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        base = 'http://127.0.0.1:' + str(self.server.server_port)
        self.config = self.root / 'issabel_crm.conf'
        self.config.write_text('''[general]
pbx_id = pbx-lab
fallback_queue = 600
prompt = enter-cuil
invalid_prompt = pbx-invalid
attempts = 2
digit_timeout_ms = 1000
validate_checksum = no
lookup_timeout = 1
notify_timeout = 2
notify_max_workers = 4
runtime_dir = {runtime}
external_timeout = 30

[crm]
lookup_url = {base}/affiliates
notify_url = {base}/answered
allow_http = yes

[routes]
OS_A = queue:601
OS_B = external:08001234567

[agents]
PJSIP/1001 = crm-user-a,1001
Local/1002@from-queue/n = crm-user-b
'''.format(runtime=self.root / 'run', base=base))
        (self.root / 'run').mkdir()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.tmp.cleanup()

    def test_installed_style_import_also_locates_the_http_subprocess_module(self):
        variables, _, _, _ = run_agi('identify', self.config, digits=['20123456786'], export_pythonpath=False)
        self.assertEqual('found', variables['CRM_RESULT'])
        variables.update(MEMBERINTERFACE='PJSIP/1001', CRM_QUEUE='601')
        run_agi('answer', self.config, variables=variables, export_pythonpath=False)
        self.assertTrue(self.server.received.wait(2))

    def identified(self, member='PJSIP/1001', uniqueid='1700000000.1'):
        variables, _, _, _ = run_agi('identify', self.config, digits=['20123456786'], uniqueid=uniqueid)
        variables.update(MEMBERINTERFACE=member, MEMBERNAME='Operador', CRM_QUEUE='601')
        return variables

    def test_lookup_failures_clear_old_affiliate_and_continue_to_general_queue(self):
        scenarios = [
            (404, b'', 'not_found', ''), (500, b'{}', 'http_error', ''),
            (200, b'broken', 'invalid_response', ''),
            (200, b'{"affiliate_id":"a","obra_social":["OS_A","OS_B"]}', 'ambiguous_obra', 'a'),
            (200, b'{"affiliate_id":"a","obra_social":"UNKNOWN"}', 'unmapped_obra', 'a'),
            (200, b'{"affiliate_id":"a","obra_social":"${SHELL(evil)}"}', 'invalid_response', ''),
            (200, b'x' * 65537, 'response_too_large', ''),
        ]
        for status, body, expected, affiliate in scenarios:
            with self.subTest(expected=expected):
                self.server.lookup_status, self.server.lookup_body = status, body
                variables, _, _, errors = run_agi('identify', self.config,
                    variables={'CRM_AFFILIATE_ID': 'stale-affiliate'}, digits=['20123456786'])
                self.assertEqual(expected, variables['CRM_RESULT'])
                self.assertEqual(('queue', '600', affiliate),
                    (variables['CRM_DEST_TYPE'], variables['CRM_DEST'], variables['CRM_AFFILIATE_ID']))
                self.assertNotIn('20123456786', errors)
                run_agi('answer', self.config, variables=variables)
        self.assertEqual([], self.server.notifications)

    def test_total_lookup_budget_also_bounds_a_trickling_response(self):
        self.config.write_text(self.config.read_text().replace('lookup_timeout = 1', 'lookup_timeout = 0.25'))
        self.server.trickle = 0.05
        variables, _, elapsed, _ = run_agi('identify', self.config, digits=['20123456786'])
        self.assertEqual('timeout', variables['CRM_RESULT'])
        self.assertEqual('600', variables['CRM_DEST'])
        self.assertLess(elapsed, 0.8)

    def test_answer_returns_and_closes_agi_stream_before_slow_crm_responds(self):
        variables = self.identified()
        self.server.notify_delay = 1.5
        _, _, elapsed, _ = run_agi('answer', self.config, variables=variables)
        self.assertLess(elapsed, 0.8, 'EOF must not be held open by the detached emitter')
        self.assertTrue(self.server.received.wait(2))
        self.assertEqual(1, len(self.server.notifications))
        time.sleep(1.6)  # let the bounded emitter finish before fixture removal

    def test_notification_timeout_releases_slot_without_retry(self):
        import fcntl
        self.config.write_text(self.config.read_text().replace('notify_timeout = 2', 'notify_timeout = 0.2'))
        variables = self.identified()
        self.server.notify_delay = 1
        run_agi('answer', self.config, variables=variables)
        self.assertTrue(self.server.received.wait(2))
        time.sleep(0.4)
        with open(self.root / 'run' / 'slot-0', 'rb') as slot:
            fcntl.flock(slot, fcntl.LOCK_EX | fcntl.LOCK_NB)
        self.assertEqual(1, len(self.server.notifications))

    def test_exact_local_member_mapping_does_not_invent_a_physical_extension(self):
        variables = self.identified('Local/1002@from-queue/n')
        run_agi('answer', self.config, variables=variables)
        self.assertTrue(self.server.received.wait(2))
        self.assertEqual('crm-user-b', self.server.notifications[0]['crm_user_id'])
        self.assertNotIn('extension', self.server.notifications[0])

    def test_unknown_member_and_saturated_or_missing_runtime_do_not_block_answer(self):
        import fcntl
        unknown = self.identified('Agent/not-mapped')
        _, _, _, errors = run_agi('answer', self.config, variables=unknown)
        self.assertIn('notification_unmapped_member', errors)
        self.config.write_text(self.config.read_text().replace('notify_max_workers = 4', 'notify_max_workers = 1'))
        variables = self.identified()
        with open(self.root / 'run' / 'slot-0', 'wb') as slot:
            fcntl.flock(slot, fcntl.LOCK_EX | fcntl.LOCK_NB)
            _, _, elapsed, errors = run_agi('answer', self.config, variables=variables)
            self.assertLess(elapsed, 0.8)
            self.assertIn('notification_saturated', errors)
        (self.root / 'run' / 'slot-0').unlink()
        (self.root / 'run').rmdir()
        _, _, _, errors = run_agi('answer', self.config, variables=variables)
        self.assertIn('notification_launch_failed', errors)
        self.assertEqual([], self.server.notifications)

    def test_concurrent_calls_of_same_affiliate_do_not_cross_operator_identity(self):
        from concurrent.futures import ThreadPoolExecutor
        def call(index):
            member = 'PJSIP/1001' if index % 2 == 0 else 'Local/1002@from-queue/n'
            variables = self.identified(member, '1700000000.' + str(index))
            run_agi('answer', self.config, variables=variables)
            return variables['CRM_INTERACTION_ID'], 'crm-user-a' if index % 2 == 0 else 'crm-user-b'
        with ThreadPoolExecutor(max_workers=4) as pool:
            expected = dict(pool.map(call, range(4)))
        deadline = time.monotonic() + 3
        while len(self.server.notifications) < 4 and time.monotonic() < deadline:
            time.sleep(0.02)
        observed = {n['interaction_id']: n['crm_user_id'] for n in self.server.notifications}
        self.assertEqual(expected, observed)
        self.assertEqual(4, len({n['event_id'] for n in self.server.notifications}))

    def test_manual_map_changes_affect_new_calls_without_code_changes(self):
        self.config.write_text(self.config.read_text().replace('queue:601', 'queue:602').replace('crm-user-a', 'crm-user-new'))
        variables = self.identified()
        self.assertEqual('602', variables['CRM_DEST'])
        run_agi('answer', self.config, variables=variables)
        self.assertTrue(self.server.received.wait(2))
        self.assertEqual('crm-user-new', self.server.notifications[0]['crm_user_id'])

    def test_external_route_is_selected_only_from_local_approved_map(self):
        self.server.lookup_body = b'{"affiliate_id":"af-demo-2","obra_social":"OS_B"}'
        variables, _, _, _ = run_agi('identify', self.config, digits=['20123456786'])
        self.assertEqual(('external', '08001234567'), (variables['CRM_DEST_TYPE'], variables['CRM_DEST']))
        self.assertEqual([], self.server.notifications)

    def test_bad_config_preserves_preseeded_fallback_and_does_not_reuse_identity(self):
        self.config.write_text(self.config.read_text().replace('queue:601', 'external:${SHELL(evil)}'))
        variables, _, _, errors = run_agi('identify', self.config,
            variables={'CRM_AFFILIATE_ID': 'stale', 'CRM_DEST': '600', 'CRM_DEST_TYPE': 'queue'},
            digits=['20123456786'])
        self.assertEqual('config_error', variables['CRM_RESULT'])
        self.assertEqual('600', variables['CRM_DEST'])
        self.assertEqual('', variables['CRM_AFFILIATE_ID'])
        self.assertNotIn('evil', errors)

    def test_recognized_affiliate_in_general_queue_still_notifies_operator(self):
        self.server.lookup_body = b'{"affiliate_id":"af-recognized","obra_social":"UNMAPPED"}'
        variables = self.identified()
        self.assertEqual('600', variables['CRM_DEST'])
        variables['CRM_QUEUE'] = '600'
        run_agi('answer', self.config, variables=variables)
        self.assertTrue(self.server.received.wait(2))
        self.assertEqual('af-recognized', self.server.notifications[0]['affiliate_id'])

    def test_reassignment_while_waiting_omits_notice_to_a_different_crm_user(self):
        variables = self.identified()
        self.config.write_text(self.config.read_text().replace('crm-user-a', 'crm-user-reassigned'))
        _, _, _, errors = run_agi('answer', self.config, variables=variables)
        self.assertIn('notification_mapping_changed', errors)
        self.assertEqual([], self.server.notifications)

    def test_routing_diagnostic_includes_approved_destination_without_cuil(self):
        _, _, _, errors = run_agi('identify', self.config, digits=['20123456786'])
        diagnostic = json.loads(errors.strip())
        self.assertEqual('queue:601', diagnostic['destination'])
        self.assertNotIn('20123456786', errors)

    def test_bearer_tokens_are_sent_in_headers_and_never_in_agi_logs(self):
        secrets = self.root / 'credentials.conf'
        secrets.write_text('[auth]\nlookup_token = lookup-secret\nnotify_token = notify-secret\n')
        self.config.write_text(self.config.read_text().replace('[crm]', '[crm]\nsecrets_file = ' + str(secrets)))
        variables, _, _, errors = run_agi('identify', self.config, digits=['20123456786'])
        variables.update(MEMBERINTERFACE='PJSIP/1001', CRM_QUEUE='601')
        _, _, _, answer_errors = run_agi('answer', self.config, variables=variables)
        self.assertTrue(self.server.received.wait(2))
        self.assertEqual(['Bearer lookup-secret'], self.server.lookup_auth)
        self.assertEqual(['Bearer notify-secret'], self.server.notify_auth)
        self.assertNotIn('secret', errors + answer_errors)

    def test_connection_refused_and_notification_http_error_are_best_effort(self):
        variables = self.identified()
        self.server.notify_status = 503
        _, _, elapsed, _ = run_agi('answer', self.config, variables=variables)
        self.assertLess(elapsed, 0.8)
        self.assertTrue(self.server.received.wait(2))
        time.sleep(0.2)
        self.assertEqual(1, len(self.server.notifications))
        # Reuse the now-closed listener address for deterministic connection refusal.
        self.server.shutdown()
        self.server.server_close()
        variables, _, elapsed, _ = run_agi('identify', self.config, digits=['20123456786'])
        self.assertEqual('transport_error', variables['CRM_RESULT'])
        self.assertEqual('600', variables['CRM_DEST'])
        self.assertLess(elapsed, 0.8)

    def test_simultaneous_distinct_affiliates_keep_their_own_notice(self):
        from concurrent.futures import ThreadPoolExecutor
        self.server.lookup_by_cuil = {
            '20123456786': b'{"affiliate_id":"af-demo-1","obra_social":"OS_A"}',
            '27234567891': b'{"affiliate_id":"af-demo-2","obra_social":"OS_A"}'}
        def call(index):
            cuil = '20123456786' if index == 0 else '27234567891'
            variables, _, _, _ = run_agi('identify', self.config, digits=[cuil], uniqueid='1700000000.' + str(index))
            variables.update(MEMBERINTERFACE='PJSIP/1001', CRM_QUEUE='601')
            run_agi('answer', self.config, variables=variables)
            return variables['CRM_INTERACTION_ID'], 'af-demo-1' if index == 0 else 'af-demo-2'
        with ThreadPoolExecutor(max_workers=2) as pool:
            expected = dict(pool.map(call, range(2)))
        deadline = time.monotonic() + 3
        while len(self.server.notifications) < 2 and time.monotonic() < deadline:
            time.sleep(0.02)
        self.assertEqual(expected, {n['interaction_id']: n['affiliate_id'] for n in self.server.notifications})

    def test_configured_star_terminator_is_accepted_by_the_ivr(self):
        self.config.write_text(self.config.read_text().replace('attempts = 2', 'attempts = 2\nterminator = *'))
        variables, _, _, _ = run_agi('identify', self.config, digits=['20123456786*'])
        self.assertEqual('found', variables['CRM_RESULT'])

    def test_invalid_modulo_11_check_digit_does_not_lookup_an_affiliate(self):
        self.config.write_text(self.config.read_text().replace('validate_checksum = no', 'validate_checksum = yes'))
        variables, _, _, errors = run_agi('identify', self.config, digits=['20000000019', ''])
        self.assertEqual('invalid_cuil', variables['CRM_RESULT'])
        self.assertEqual('600', variables['CRM_DEST'])
        self.assertEqual([], self.server.requests)
        self.assertNotIn('20000000019', errors)

    def test_affiliate_is_routed_and_answer_notifies_the_correct_operator(self):
        variables, commands, _, _ = run_agi('identify', self.config, digits=['20123456786'])
        self.assertEqual(('queue', '601'), (variables['CRM_DEST_TYPE'], variables['CRM_DEST']))
        self.assertEqual([{'cuil': ['20123456786']}], self.server.requests)
        self.assertEqual([], self.server.notifications, 'lookup must not imply an answer')
        variables.update(MEMBERINTERFACE='PJSIP/1001', MEMBERNAME='Operador A', CRM_QUEUE='601')
        _, _, _, _ = run_agi('answer', self.config, variables=variables)
        self.assertTrue(self.server.received.wait(3), 'detached emitter must deliver the HTTP request')
        notice = self.server.notifications[0]
        self.assertEqual('af-demo-1', notice['affiliate_id'])
        self.assertEqual('crm-user-a', notice['crm_user_id'])
        self.assertEqual('PJSIP/1001', notice['member_interface'])
        self.assertEqual('1001', notice['extension'])
        self.assertEqual('601', notice['queue'])
        self.assertEqual(variables['CRM_INTERACTION_ID'], notice['interaction_id'])
        self.assertNotEqual(notice['interaction_id'], notice['event_id'])
        self.assertNotIn('20123456786', json.dumps(notice))
