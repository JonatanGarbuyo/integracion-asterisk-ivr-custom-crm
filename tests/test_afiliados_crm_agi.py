"""Public AGI-process and HTTP tests; no internal PHP functions are mocked."""
import json
import os
from pathlib import Path
import selectors
import ssl
import importlib.util
import shlex
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit


ROOT = Path(__file__).resolve().parents[1] / 'tools' / 'afiliados-crm-agi'
PHP = os.environ.get('AFILIADOS_TEST_PHP') or shutil.which('php')


def record(**changes):
    data = dict(cuilValido=True, esTitular=True, activo=True,
                prestadora='Prestadora de prueba', provincia='Provincia ficticia',
                referencias=[], esProveedor=False)
    data.update(changes)
    return data


class TestHTTPServer(ThreadingHTTPServer):
    def handle_error(self, request, client_address):
        # Aborted TLS handshakes/timeouts are deliberate test inputs.
        if not isinstance(sys.exc_info()[1], (BrokenPipeError, ConnectionResetError, ssl.SSLError)):
            super().handle_error(request, client_address)


class AtencionesAgi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not PHP:
            raise RuntimeError('PHP CLI with curl/json is required; tests cannot be skipped')
        subprocess.run([PHP, '-r', 'exit(extension_loaded("curl") && '
                        'extension_loaded("json") ? 0 : 1);'], check=True)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.spool = self.directory / 'jobs'
        self.spool.mkdir(mode=0o700)
        self.state = dict(payload=record(), get_status=200, post_status=200,
                          post_result='OK', get_delay=0, post_delay=0,
                          requests=[], post_started=threading.Event(),
                          post_finished=threading.Event())
        state = self.state

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_args):
                pass

            def respond(self, status, payload):
                body = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
                self.send_response(status)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                try:
                    self.wfile.write(body)
                except (BrokenPipeError, ConnectionResetError):
                    pass

            def do_GET(self):
                state['requests'].append(dict(method='GET', path=self.path,
                                              headers=dict(self.headers)))
                time.sleep(state['get_delay'])
                self.respond(state['get_status'], state['payload'])

            def do_POST(self):
                body = self.rfile.read(int(self.headers.get('Content-Length', '0')))
                state['requests'].append(dict(method='POST', path=self.path,
                                              headers=dict(self.headers), body=body))
                state['post_started'].set()
                if state.get('post_release') is not None:
                    state['post_release'].wait(5)
                time.sleep(state['post_delay'])
                self.respond(state['post_status'], dict(resultado=state['post_result']))
                state['post_finished'].set()

        self.server = TestHTTPServer(('127.0.0.1', 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.thread.join, 2)
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.conf = self.directory / 'atenciones.conf'
        self.conf.write_text('[atenciones]\nbase_url = http://127.0.0.1:%s/Atenciones\n'
                             'api_key = test-secret\nallow_http_loopback = 1\n'
                             '[runtime]\nspool_dir = "%s"\n' %
                             (self.server.server_port, self.spool))
        self.conf.chmod(0o600)

    def agi(self, name, variables=None, option='1', uniqueid='caller.123', timeout=8, php_args=()):
        variables = dict(variables or {})
        env = dict(os.environ, AFILIADOS_CRM_CONF=str(self.conf))
        process = subprocess.Popen([PHP] + list(php_args) + [str(ROOT / name), option], stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   text=True, env=env)
        self.addCleanup(lambda: process.kill() if process.poll() is None else None)
        initial = 'agi_channel: SIP/inbound-abc\nagi_uniqueid: %s\nagi_arg_1: %s\n\n' % (
            uniqueid, option)
        process.stdin.write(initial)
        process.stdin.flush()
        commands = []
        selector = selectors.DefaultSelector()
        selector.register(process.stdout, selectors.EVENT_READ)
        deadline = time.monotonic() + timeout
        while True:
            remaining = deadline - time.monotonic()
            self.assertGreater(remaining, 0, 'AGI did not return within the test deadline')
            self.assertTrue(selector.select(remaining), 'AGI stalled')
            line = process.stdout.readline()
            if not line:
                break
            commands.append(line.rstrip())
            tokens = shlex.split(line)
            if tokens[:2] == ['GET', 'VARIABLE']:
                value = variables.get(tokens[2])
                response = '200 result=0\n' if value is None else '200 result=1 (%s)\n' % value
            elif tokens[:2] == ['SET', 'VARIABLE']:
                self.assertEqual(len(tokens), 4)
                variables[tokens[2].lstrip('_')] = tokens[3]
                response = '200 result=1\n'
            else:
                self.fail('AGI attempted a non-data command: %s' % line)
            process.stdin.write(response)
            process.stdin.flush()
        selector.close()
        process.wait(timeout=max(0.1, deadline - time.monotonic()))
        stderr = process.stderr.read()
        process.stdin.close()
        process.stdout.close()
        process.stderr.close()
        self.assertEqual(process.returncode, 0, stderr)
        return variables, commands, stderr

    def lookup(self, option='1', cuil='20-00000000-1', variables=None, uniqueid='caller.123'):
        values = dict(dtmfinput=cuil)
        values.update(variables or {})
        return self.agi('crm_get_afiliado.agi.php', values, option, uniqueid)

    def test_lookup_resolves_a_value_and_uses_the_real_api_contract(self):
        values, commands, stderr = self.lookup()
        self.assertEqual(values['CRM_ROUTE_KEY'], 'END_CALL')
        self.assertEqual(values['CRM_PRESTADORA'], 'Prestadora de prueba')
        request = self.state['requests'][0]
        parsed = urlsplit(request['path'])
        self.assertEqual(parsed.path, '/Atenciones/api/central/preatendedor')
        self.assertEqual(parse_qs(parsed.query), dict(opcion=['1'], cuil=['20000000001'],
                                                     llamada=['caller.123']))
        self.assertEqual(request['headers']['X-Api-Key'], 'test-secret')
        self.assertNotIn('Authorization', request['headers'])
        self.assertEqual(values['dtmfinput'], '')
        self.assertNotIn('test-secret', '\n'.join(commands) + stderr)

    def test_attention_returns_the_literal_prestadora_in_the_single_route_variable(self):
        self.state['payload'] = record(prestadora='Osde')
        values, _, _ = self.lookup(option='2')
        self.assertEqual(values['CRM_ROUTE_KEY'], 'Osde')

    def test_attention_without_prestadora_falls_back_to_general_call_center(self):
        for name in (None, ''):
            with self.subTest(prestadora=name):
                self.state['payload'] = record(prestadora=name)
                values, _, _ = self.lookup(option='2')
                self.assertEqual(values['CRM_ROUTE_KEY'], 'CALL_CENTER')

    def test_reference_object_is_not_a_valid_json_list(self):
        self.state['payload'] = record(referencias={})
        values, _, _ = self.lookup()
        self.assertEqual(values['CRM_ROUTE_KEY'], 'CALL_CENTER')
        self.assertEqual(values['CRM_PRESTADORA'], '')

    def test_attended_notification_uses_original_id_and_only_the_extension(self):
        values, _, _ = self.lookup(option='2')
        values.update(MEMBERINTERFACE='Local/1001@from-queue/n', MEMBERNAME='Display label')
        self.agi('crm_set_atencion.agi.php', values, uniqueid='agent.999')
        self.assertTrue(self.state['post_finished'].wait(4), 'notification was not sent')
        request = next(r for r in self.state['requests'] if r['method'] == 'POST')
        self.assertEqual(request['path'], '/Atenciones/api/central/llamada-atendida')
        self.assertEqual(request['headers']['X-Api-Key'], 'test-secret')
        self.assertEqual(request['headers']['Content-Type'], 'application/x-www-form-urlencoded')
        self.assertNotIn('Authorization', request['headers'])
        self.assertEqual(parse_qs(request['body'].decode()),
                         dict(llamada=['caller.123'], interno=['1001']))
        self.assertEqual(list(self.spool.iterdir()), [])

    def test_menu_rules_return_decision_keys_without_routing_the_channel(self):
        cases = [
            ('1', record(cuilValido=False, esProveedor=True), 'INVALID_CUIL'),
            ('1', record(esProveedor=True, esTitular=False, activo=False), 'END_CALL'),
            ('1', record(), 'END_CALL'),
            ('1', record(activo=False), 'Prestadora de prueba'),
            ('1', record(esTitular=False, activo=False, referencias=['FICTIONAL_REF']), 'Prestadora de prueba'),
            ('1', record(esTitular=False, activo=False, prestadora=None, provincia=None), 'CALL_CENTER'),
            ('2', record(cuilValido=False, esTitular=False), 'INVALID_CUIL'),
            ('2', record(esTitular=False), 'END_CALL'),
            ('2', record(activo=False, referencias=['FICTIONAL_REF']), 'END_CALL'),
            ('2', record(referencias=['FICTIONAL_REF']), 'PORTAL'),
            ('2', record(esProveedor=True, referencias=['FICTIONAL_REF']), 'PORTAL'),
            ('2', record(esProveedor=True), 'Prestadora de prueba'),
            ('2', record(), 'Prestadora de prueba'),
        ]
        for option, payload, expected in cases:
            with self.subTest(option=option, payload=payload):
                self.state['payload'] = payload
                values, _, _ = self.lookup(option=option)
                self.assertEqual(values['CRM_ROUTE_KEY'], expected)

    def test_prestadora_keeps_unicode_case_and_escaping_without_overriding_rejection(self):
        name = 'Prestadora Ñandú "Prueba" \\ Sucursal'
        self.state['payload'] = record(prestadora=name)
        values, _, _ = self.lookup(option='2')
        self.assertEqual(values['CRM_ROUTE_KEY'], name)
        self.assertEqual(values['CRM_PRESTADORA'], name)
        values, _, _ = self.lookup(option='1')
        self.assertEqual(values['CRM_ROUTE_KEY'], 'END_CALL')

    def test_optional_and_invalid_cuil_are_sent_to_the_api_for_validation(self):
        self.state['payload'] = record(cuilValido=False, esTitular=False, activo=False,
                                       prestadora=None, provincia=None)
        for cuil in ('', '12', ' 20-00000000-1 '):
            with self.subTest(cuil=cuil):
                values, _, _ = self.lookup(cuil=cuil)
                self.assertEqual(values['CRM_ROUTE_KEY'], 'INVALID_CUIL')
                query = parse_qs(urlsplit(self.state['requests'][-1]['path']).query,
                                 keep_blank_values=True)
                self.assertEqual(query['cuil'], [cuil.replace(' ', '').replace('-', '')])

    def test_technical_errors_use_call_center_and_keep_the_answer_hook(self):
        for status in (201, 302, 400, 401, 403, 404, 500, 503):
            with self.subTest(status=status):
                self.state['get_status'] = status
                values, _, stderr = self.lookup()
                self.assertEqual(values['CRM_ROUTE_KEY'], 'CALL_CENTER')
                self.assertEqual(values['CRM_PRESTADORA'], '')
                self.assertEqual(values['CRM_CALL_ID'], 'caller.123')
                self.assertEqual(values['QAGI'], 'crm_set_atencion.agi.php')
                self.assertNotIn('20000000001', stderr)

    def test_bad_json_types_and_oversized_responses_are_technical_errors(self):
        missing = record()
        del missing['cuilValido']
        cases = [b'not JSON', b'[]', missing, record(cuilValido='false'),
                 record(activo=1), record(referencias=None), record(referencias=[1]),
                 record(prestadora=['wrong type']), record(prestadora='bad\nvalue'),
                 b' ' * 17000]
        for payload in cases:
            with self.subTest(payload_type=type(payload).__name__):
                self.state['payload'] = payload
                values, _, _ = self.lookup()
                self.assertEqual(values['CRM_ROUTE_KEY'], 'CALL_CENTER')
                self.assertEqual(values['CRM_PRESTADORA'], '')

    def test_lookup_times_out_at_three_seconds(self):
        self.state['get_delay'] = 4.2
        started = time.monotonic()
        values, _, _ = self.lookup()
        elapsed = time.monotonic() - started
        self.assertEqual(values['CRM_ROUTE_KEY'], 'CALL_CENTER')
        self.assertGreater(elapsed, 2.7)
        self.assertLess(elapsed, 3.8)

    def test_original_id_survives_a_cuil_retry_on_a_different_channel(self):
        first, _, _ = self.lookup(uniqueid='ingress.42')
        first['dtmfinput'] = '27-00000000-2'
        second, _, _ = self.lookup(variables=first, uniqueid='local.99')
        self.assertEqual(second['CRM_CALL_ID'], 'ingress.42')
        query = parse_qs(urlsplit(self.state['requests'][-1]['path']).query)
        self.assertEqual(query['llamada'], ['ingress.42'])
        self.assertEqual(query['cuil'], ['27000000002'])

    def test_maximum_original_id_is_preserved_and_overlong_id_is_not_truncated(self):
        values, _, _ = self.lookup(uniqueid='a' * 40)
        self.assertEqual(values['CRM_CALL_ID'], 'a' * 40)
        count = len(self.state['requests'])
        values, _, _ = self.lookup(uniqueid='b' * 41)
        self.assertEqual(values['CRM_ROUTE_KEY'], 'CALL_CENTER')
        self.assertEqual(len(self.state['requests']), count)
        self.assertNotIn('CRM_CALL_ID', values)

    def test_foreign_queue_hooks_are_preserved(self):
        for name in ('QAGI', 'VQ_AGI'):
            with self.subTest(name=name):
                values, _, _ = self.lookup(variables={name: 'foreign_crm_set_atencion.agi.php'})
                self.assertEqual(values[name], 'foreign_crm_set_atencion.agi.php')
                self.assertEqual(values['CRM_QAGI_CONFLICT'], '1')

    def test_option_three_does_not_call_the_api(self):
        values, _, _ = self.lookup(option='3')
        self.assertEqual(values['CRM_ROUTE_KEY'], 'OPTION_3')
        self.assertEqual(self.state['requests'], [])
        self.assertNotIn('QAGI', values)

    def test_menu_option_can_be_read_from_the_inherited_ivr_variable(self):
        values, _, _ = self.lookup(option='', variables=dict(IVR_DIGIT_PRESSED='2'))
        self.assertEqual(values['CRM_ROUTE_KEY'], 'Prestadora de prueba')
        self.assertEqual(len(self.state['requests']), 1)
        query = parse_qs(urlsplit(self.state['requests'][0]['path']).query)
        self.assertEqual(query['opcion'], ['2'])

    def test_configuration_array_is_a_safe_error_instead_of_a_php_fatal(self):
        self.conf.write_text('[atenciones]\nbase_url[]=invalid\napi_key=test-secret\n')
        values, _, stderr = self.lookup()
        self.assertEqual(values['CRM_ROUTE_KEY'], 'CALL_CENTER')
        self.assertNotIn('Fatal', stderr)
        self.assertEqual(self.state['requests'], [])

    def test_medical_fields_and_cuil_are_not_exported_to_channel_or_jobs(self):
        self.state['payload'] = record(referencias=['PRIVATE_TEST_REFERENCE'])
        values, commands, stderr = self.lookup(option='2')
        self.assertEqual(values['CRM_ROUTE_KEY'], 'PORTAL')
        output = '\n'.join(commands) + stderr + json.dumps(values)
        for sensitive in ('PRIVATE_TEST_REFERENCE', 'test-secret', '20000000001'):
            self.assertNotIn(sensitive, output)
        self.assertEqual(values['CRM_CUIL'], '')
        self.assertEqual(list(self.spool.iterdir()), [])

    def test_a_blocked_post_does_not_hold_the_queue_agi(self):
        release = threading.Event()
        self.state['post_release'] = release
        try:
            self.agi('crm_set_atencion.agi.php', dict(CRM_CALL_ID='caller.42',
                     MEMBERINTERFACE='Local/1001@from-queue/n'), timeout=1)
            self.assertTrue(self.state['post_started'].wait(2))
            self.assertFalse(self.state['post_finished'].is_set())
        finally:
            release.set()
        self.assertTrue(self.state['post_finished'].wait(3))

    def test_the_three_post_results_and_http_failure_do_not_affect_the_agi(self):
        for result, status in [('OK', 200), ('SIN_VALIDACION', 200), ('SIN_OPERADOR', 200),
                               ('ignored', 401), ('ignored', 500)]:
            with self.subTest(result=result, status=status):
                self.state['post_result'], self.state['post_status'] = result, status
                self.state['post_finished'].clear()
                self.agi('crm_set_atencion.agi.php', dict(CRM_CALL_ID='original.1',
                         MEMBERINTERFACE='Local/1001@from-queue/n'))
                self.assertTrue(self.state['post_finished'].wait(3))

    def test_missing_identity_never_uses_the_current_channel_id_or_display_name(self):
        cases = [dict(MEMBERINTERFACE='Local/1001@from-queue/n'),
                 dict(CRM_CALL_ID='original.1', MEMBERNAME='1001'),
                 dict(CRM_CALL_ID='original.1', MEMBERINTERFACE='Local/1001@other/n'),
                 dict(CRM_CALL_ID='original.1', MEMBERINTERFACE='Agent/9000'),
                 dict(CRM_CALL_ID='original.1', MEMBERINTERFACE='SIP/person-name'),
                 dict(CRM_CALL_ID='original.1', MEMBERINTERFACE='SIP/12345678901')]
        for values in cases:
            with self.subTest(values=values):
                self.agi('crm_set_atencion.agi.php', values, uniqueid='agent.must.not.be.used')
        self.assertEqual(self.state['requests'], [])

    def test_numeric_members_preserve_leading_zero_and_form_encoding(self):
        for interface, extension in [('Local/01001@from-queue/n', '01001'),
                                      ('SIP/1234', '1234'), ('PJSIP/5678', '5678')]:
            with self.subTest(interface=interface):
                self.state['post_finished'].clear()
                self.agi('crm_set_atencion.agi.php', dict(CRM_CALL_ID='original&x=1',
                         MEMBERINTERFACE=interface))
                self.assertTrue(self.state['post_finished'].wait(3))
                self.assertEqual(parse_qs(self.state['requests'][-1]['body'].decode()),
                                 dict(llamada=['original&x=1'], interno=[extension]))

    def test_dispatch_failure_removes_the_job_and_returns_normally(self):
        _, _, stderr = self.agi('crm_set_atencion.agi.php',
                                dict(CRM_CALL_ID='caller.42', MEMBERINTERFACE='SIP/1001'),
                                php_args=['-d', 'disable_functions=exec'])
        self.assertIn('notification_dispatch_failed', stderr)
        self.assertEqual(list(self.spool.iterdir()), [])
        self.assertEqual(self.state['requests'], [])

    def test_https_requires_a_trusted_certificate_and_matching_hostname(self):
        cert, key = self.directory / 'cert.pem', self.directory / 'key.pem'
        subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes',
                        '-keyout', str(key), '-out', str(cert), '-days', '1',
                        '-subj', '/CN=localhost', '-addext', 'subjectAltName=DNS:localhost'],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        server = TestHTTPServer(('127.0.0.1', 0), self.server.RequestHandlerClass)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(cert, key)
        server.socket = context.wrap_socket(server.socket, server_side=True)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(thread.join, 2)
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        conf = self.conf.read_text().replace('http://127.0.0.1:%s' % self.server.server_port,
                                             'https://localhost:%s' % server.server_port)
        self.conf.write_text(conf)
        values, _, _ = self.lookup()
        self.assertEqual(values['CRM_ROUTE_KEY'], 'CALL_CENTER')
        self.assertEqual(self.state['requests'], [])
        trusted = conf.replace('[runtime]', 'ca_file = "%s"\n[runtime]' % cert)
        self.conf.write_text(trusted.replace('https://localhost:', 'https://127.0.0.1:'))
        values, _, _ = self.lookup()
        self.assertEqual(values['CRM_ROUTE_KEY'], 'CALL_CENTER')
        self.assertEqual(self.state['requests'], [])
        self.conf.write_text(trusted)
        values, _, _ = self.lookup()
        self.assertEqual(values['CRM_ROUTE_KEY'], 'END_CALL')
        self.assertEqual(len(self.state['requests']), 1)

    def test_worker_rejects_external_or_malformed_jobs_without_http(self):
        env = dict(os.environ, AFILIADOS_CRM_CONF=str(self.conf))
        outside = self.directory / 'atencion-outside.job'
        malformed = self.spool / 'atencion-malformed.job'
        linked = self.spool / 'atencion-linked.job'
        outside.write_text(json.dumps(dict(llamada='original.1', interno='1001')))
        outside.chmod(0o600)
        linked.symlink_to(outside)
        malformed.write_text(json.dumps(dict(llamada='original.1', interno='1001', cuil='forbidden')))
        malformed.chmod(0o600)
        for job in (outside, linked, malformed):
            result = subprocess.run([PHP, str(ROOT / 'afiliados-crm/crm_worker.php'), str(job)],
                                    env=env, capture_output=True, text=True, timeout=2)
            self.assertEqual(result.returncode, 0)
            self.assertNotIn('forbidden', result.stderr)
        self.assertTrue(outside.exists())
        self.assertFalse(malformed.exists())
        self.assertEqual(self.state['requests'], [])

    def test_documented_mock_fixtures_work_with_the_actual_agi(self):
        spec = importlib.util.spec_from_file_location('atenciones_mock', ROOT / 'mock_crm_server.py')
        mock = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mock)
        self.server.RequestHandlerClass = mock.make_handler('test-secret')
        cases = [('20000000001', '1', 'END_CALL', 'Prestadora A'),
                 ('20000000001', '2', 'Prestadora A', 'Prestadora A'),
                 ('20000000028', '2', 'PORTAL', 'Prestadora B'),
                 ('20000000036', '1', 'Prestadora A', 'Prestadora A'),
                 ('20000000036', '2', 'END_CALL', 'Prestadora A'),
                 ('20000000044', '2', 'END_CALL', 'Prestadora B'),
                 ('30000000007', '1', 'END_CALL', ''),
                 ('20000000052', '1', 'CALL_CENTER', ''),
                 ('123', '1', 'INVALID_CUIL', '')]
        for cuil, option, decision, prestadora in cases:
            with self.subTest(cuil=cuil, option=option):
                values, _, _ = self.lookup(option=option, cuil=cuil)
                self.assertEqual(values['CRM_ROUTE_KEY'], decision)
                self.assertEqual(values['CRM_PRESTADORA'], prestadora)


if __name__ == '__main__':
    unittest.main()
