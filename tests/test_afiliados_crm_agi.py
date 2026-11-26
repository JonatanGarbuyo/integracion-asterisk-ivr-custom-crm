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


def record(destino='CALL_CENTER', **extras):
    data = dict(destino=destino)
    data.update(extras)
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

    def agi(self, name, variables=None, option='1', uniqueid='caller.123', timeout=8, php_args=(), script_dir=None,
            interaction=None, audio_errors=None):
        variables = dict(variables or {})
        attempts = iter(interaction if interaction is not None else [('20000000001', '1')])
        pending_digits = []
        confirmations = iter(())
        audio_errors = audio_errors or {}
        initial_get_count = sum(r['method'] == 'GET' for r in self.state['requests'])
        env = dict(os.environ, AFILIADOS_CRM_CONF=str(self.conf))
        process = subprocess.Popen([PHP] + list(php_args) + [str((script_dir or ROOT) / name), option], stdin=subprocess.PIPE,
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
            elif tokens[:2] == ['GET', 'OPTION']:
                if tokens[2].endswith('ingrese-cuil'):
                    cuil, confirmation = next(attempts, ('', None))
                    confirmations = iter(confirmation if isinstance(confirmation, (list, tuple)) else [confirmation])
                    pending_digits = list(cuil) + (['#'] if isinstance(cuil, str) and 0 < len(cuil) < 11 else [])
                    digit = pending_digits.pop(0) if pending_digits else None
                else:
                    self.assertEqual(sum(r['method'] == 'GET' for r in self.state['requests']), initial_get_count,
                                     'The API was called before confirming the CUIL')
                    digit = next(confirmations, None)
                response = '200 result=%s endpos=8000\n' % (ord(digit) if digit else 0)
                response = audio_errors.get(tokens[2], response)
            elif tokens[:3] == ['WAIT', 'FOR', 'DIGIT']:
                digit = pending_digits.pop(0) if pending_digits else None
                response = '200 result=%s\n' % (ord(digit) if digit else 0)
            elif tokens[:2] == ['STREAM', 'FILE']:
                response = audio_errors.get(tokens[2], '200 result=0 endpos=8000\n')
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

    def lookup(self, option='1', cuil='20000000001', variables=None, uniqueid='caller.123', **kwargs):
        kwargs.setdefault('interaction', [(cuil, '1')])
        return self.agi('crm_get_afiliado.agi.php', variables, option, uniqueid, **kwargs)

    def test_cuil_is_read_back_with_custom_digits_and_only_then_confirmed(self):
        values, commands, _ = self.lookup(cuil='01234567890')
        self.assertEqual(values['CRM_ROUTE_KEY'], 'CALL_CENTER')
        audio = [c for c in commands if c.startswith(('GET OPTION', 'STREAM FILE'))]
        self.assertEqual(audio, [
            'GET OPTION "custom/atenciones/ingrese-cuil" "0123456789*#" 5000',
            'STREAM FILE "custom/atenciones/usted-ingreso" ""',
            *['STREAM FILE "custom/atenciones/digito-%s" ""' % d for d in '01234567890'],
            'GET OPTION "custom/atenciones/confirme-cuil" "0123456789*#" 5000'])
        query = parse_qs(urlsplit(self.state['requests'][0]['path']).query)
        self.assertEqual(query['cuil'], ['01234567890'])
        self.assertNotIn('01234567890', json.dumps(values))

    def test_server_can_return_only_destino_without_affiliate_fields(self):
        self.state['payload'] = {'destino': 'PORTAL'}
        values, _, _ = self.lookup(option='2')
        self.assertEqual(values['CRM_ROUTE_KEY'], 'PORTAL')

    def test_invalid_confirmation_keeps_cuil_and_repeats_only_the_question(self):
        values, commands, _ = self.lookup(interaction=[('20000000001', ['3', '1'])])
        self.assertEqual(values['CRM_ROUTE_KEY'], 'CALL_CENTER')
        self.assertEqual(sum(c.startswith('GET OPTION "custom/atenciones/ingrese-cuil"') for c in commands), 1)
        self.assertEqual(sum(c.startswith('STREAM FILE "custom/atenciones/usted-ingreso"') for c in commands), 1)
        self.assertEqual(sum(c.startswith('GET OPTION "custom/atenciones/confirme-cuil"') for c in commands), 2)
        self.assertEqual(len(self.state['requests']), 1)
        query = parse_qs(urlsplit(self.state['requests'][0]['path']).query)
        self.assertEqual(query['cuil'], ['20000000001'])

    def test_reenter_queries_only_the_last_confirmed_cuil(self):
        values, commands, _ = self.lookup(interaction=[('20000000001', '2'), ('27000000002', '1')])
        self.assertEqual(len(self.state['requests']), 1)
        query = parse_qs(urlsplit(self.state['requests'][0]['path']).query)
        self.assertEqual(query, dict(opcion=['1'], cuil=['27000000002'], llamada=['caller.123']))
        self.assertEqual(values['CRM_CALL_ID'], 'caller.123')
        self.assertEqual(sum(c.startswith('GET OPTION "custom/atenciones/ingrese-cuil"') for c in commands), 2)

    def test_partial_input_timeout_is_not_sent_and_third_attempt_can_succeed(self):
        values, commands, _ = self.lookup(interaction=[(['1', '2', None], '1'),
                                                      ('20000000001', '2'), ('27000000002', '1')])
        self.assertEqual(values['CRM_ROUTE_KEY'], 'CALL_CENTER')
        self.assertEqual(len(self.state['requests']), 1)
        query = parse_qs(urlsplit(self.state['requests'][0]['path']).query)
        self.assertEqual(query['cuil'], ['27000000002'])
        self.assertEqual(sum(c.startswith('GET OPTION "custom/atenciones/ingrese-cuil"') for c in commands), 3)

    def test_audio_names_can_be_changed_in_local_config(self):
        self.conf.write_text(self.conf.read_text() + '\n[identification]\n'
                             'request_audio=custom/piloto/ingrese-cuil\n'
                             'entered_audio=custom/piloto/ingresado\n'
                             'confirm_audio=custom/piloto/confirmacion\n'
                             'digit_audio_prefix=custom/piloto/numero-\n')
        values, commands, _ = self.lookup(cuil='12')
        self.assertEqual(values['CRM_ROUTE_KEY'], 'CALL_CENTER')
        self.assertIn('GET OPTION "custom/piloto/ingrese-cuil" "0123456789*#" 5000', commands)
        self.assertIn('STREAM FILE "custom/piloto/ingresado" ""', commands)
        self.assertIn('STREAM FILE "custom/piloto/numero-1" ""', commands)
        self.assertIn('STREAM FILE "custom/piloto/numero-2" ""', commands)
        self.assertIn('GET OPTION "custom/piloto/confirmacion" "0123456789*#" 5000', commands)

    def test_three_failed_input_or_reentry_attempts_never_query(self):
        for attempts in ([('', None)] * 3, [('20000000001', '2')] * 3, [('12*', '1')] * 3):
            with self.subTest(attempts=attempts):
                values, commands, _ = self.lookup(interaction=attempts)
                self.assertEqual(values['CRM_ROUTE_KEY'], 'INPUT_FAILED')
                self.assertEqual(sum(c.startswith('GET OPTION "custom/atenciones/ingrese-cuil"') for c in commands), 3)
                self.assertEqual(self.state['requests'], [])

    def test_exhausted_confirmation_budget_returns_input_failed_without_reentering(self):
        for replies in ([None, None, None], ['3', '9', '#'], ['*', '0', '3']):
            with self.subTest(replies=replies):
                values, commands, _ = self.lookup(interaction=[('20000000001', replies)])
                self.assertEqual(values['CRM_ROUTE_KEY'], 'INPUT_FAILED')
                self.assertEqual(sum(c.startswith('GET OPTION "custom/atenciones/ingrese-cuil"') for c in commands), 1)
                self.assertEqual(sum(c.startswith('GET OPTION "custom/atenciones/confirme-cuil"') for c in commands), 3)
                self.assertEqual(self.state['requests'], [])

    def test_confirmation_budget_resets_on_explicit_reentry(self):
        values, commands, _ = self.lookup(interaction=[('20000000001', ['3', '9', '2']),
                                                      ('27000000002', [None, '3', '1'])])
        self.assertEqual(values['CRM_ROUTE_KEY'], 'CALL_CENTER')
        self.assertEqual(sum(c.startswith('GET OPTION "custom/atenciones/ingrese-cuil"') for c in commands), 2)
        self.assertEqual(sum(c.startswith('GET OPTION "custom/atenciones/confirme-cuil"') for c in commands), 6)
        self.assertEqual(len(self.state['requests']), 1)
        query = parse_qs(urlsplit(self.state['requests'][0]['path']).query)
        self.assertEqual(query['cuil'], ['27000000002'])

    def test_confirmation_limit_is_configurable_independently_of_input_limit(self):
        self.conf.write_text(self.conf.read_text() + '\n[identification]\nmax_attempts=1\nmax_confirmation_attempts=2\n')
        values, commands, _ = self.lookup(interaction=[('20000000001', ['3', '1'])])
        self.assertEqual(values['CRM_ROUTE_KEY'], 'CALL_CENTER')
        self.assertEqual(sum(c.startswith('GET OPTION "custom/atenciones/ingrese-cuil"') for c in commands), 1)
        self.assertEqual(sum(c.startswith('GET OPTION "custom/atenciones/confirme-cuil"') for c in commands), 2)
        count = len(self.state['requests'])
        values, commands, _ = self.lookup(interaction=[('20000000001', ['3', '9', '1'])])
        self.assertEqual(values['CRM_ROUTE_KEY'], 'INPUT_FAILED')
        self.assertEqual(sum(c.startswith('GET OPTION "custom/atenciones/confirme-cuil"') for c in commands), 2)
        self.assertEqual(len(self.state['requests']), count)

    def test_configured_attempts_and_integer_seconds_are_used(self):
        self.conf.write_text(self.conf.read_text() + '\n[identification]\nmax_attempts=2\n'
                             'input_timeout=7\nconfirmation_timeout=4\n')
        values, commands, _ = self.lookup(interaction=[('12', '2'), ('20000000001', None)])
        self.assertEqual(values['CRM_ROUTE_KEY'], 'INPUT_FAILED')
        self.assertEqual(sum(c.startswith('GET OPTION "custom/atenciones/ingrese-cuil"') for c in commands), 2)
        self.assertIn('GET OPTION "custom/atenciones/ingrese-cuil" "0123456789*#" 7000', commands)
        self.assertIn('WAIT FOR DIGIT 7000', commands)
        self.assertIn('GET OPTION "custom/atenciones/confirme-cuil" "0123456789*#" 4000', commands)
        self.assertEqual(self.state['requests'], [])

    def test_bad_input_settings_are_technical_errors_without_playback(self):
        original = self.conf.read_text()
        for setting in ('max_attempts=0', 'max_attempts[]=3', 'max_confirmation_attempts=0',
                        'max_confirmation_attempts[]=3', 'max_confirmation_attempts=1.5', 'input_timeout=1.5',
                        'confirmation_timeout=-1', 'request_audio=../secret', 'confirm_audio=prompt.wav'):
            with self.subTest(setting=setting):
                self.conf.write_text(original + '\n[identification]\n' + setting + '\n')
                values, commands, _ = self.lookup()
                self.assertEqual(values['CRM_ROUTE_KEY'], 'ERROR')
                self.assertFalse(any(c.startswith(('GET OPTION', 'STREAM FILE')) for c in commands))
                self.assertEqual(self.state['requests'], [])

    def test_audio_channel_or_protocol_failure_stops_without_query(self):
        for audio in ('ingrese-cuil', 'usted-ingreso', 'digito-2', 'confirme-cuil'):
            for reply in ('200 result=-1 endpos=0\n', '510 Invalid command\n'):
                with self.subTest(audio=audio, reply=reply):
                    values, commands, stderr = self.lookup(audio_errors={'custom/atenciones/' + audio: reply})
                    self.assertEqual(values['CRM_ROUTE_KEY'], 'ERROR')
                    self.assertEqual(self.state['requests'], [])
                    self.assertNotIn('20000000001', stderr)

    def test_two_agi_files_and_the_local_config_are_sufficient(self):
        installed = self.directory / 'agi-bin'
        installed.mkdir()
        for name in ('crm_get_afiliado.agi.php', 'crm_set_atencion.agi.php'):
            shutil.copy2(ROOT / name, installed / name)
        values, _, _ = self.agi('crm_get_afiliado.agi.php', dict(dtmfinput='20000000001'),
                                option='2', script_dir=installed)
        self.assertEqual(values['CRM_ROUTE_KEY'], 'CALL_CENTER')
        values['MEMBERINTERFACE'] = 'Local/1001@from-queue/n'
        self.agi('crm_set_atencion.agi.php', values, script_dir=installed, timeout=1)
        self.assertTrue(self.state['post_finished'].wait(3))
        post = next(r for r in self.state['requests'] if r['method'] == 'POST')
        self.assertEqual(parse_qs(post['body'].decode()),
                         dict(llamada=['caller.123'], interno=['1001']))
        self.assertEqual(list(self.spool.iterdir()), [])

    def test_lookup_resolves_a_value_and_uses_the_real_api_contract(self):
        values, commands, stderr = self.lookup()
        self.assertEqual(values['CRM_ROUTE_KEY'], 'CALL_CENTER')
        self.assertEqual(values['CRM_PRESTADORA'], '')
        request = self.state['requests'][0]
        parsed = urlsplit(request['path'])
        self.assertEqual(parsed.path, '/Atenciones/api/central/preatendedor')
        self.assertEqual(parse_qs(parsed.query), dict(opcion=['1'], cuil=['20000000001'],
                                                     llamada=['caller.123']))
        self.assertEqual(request['headers']['X-Api-Key'], 'test-secret')
        self.assertNotIn('Authorization', request['headers'])
        self.assertNotIn('dtmfinput', values)
        self.assertNotIn('test-secret', '\n'.join(commands) + stderr)

    def test_future_destinations_are_passed_through_unchanged(self):
        for destination in ('ATENCION_ESPECIAL', 'atencion_norte-2027', 'COLA_Ñ'):
            with self.subTest(destination=destination):
                self.state['payload'] = record(destination)
                values, _, _ = self.lookup(option='2')
                self.assertEqual(values['CRM_ROUTE_KEY'], destination)

    def test_empty_destination_returns_error(self):
        for destination in (None, '', '   '):
            with self.subTest(destination=destination):
                self.state['payload'] = record(destination)
                values, _, _ = self.lookup(option='2')
                self.assertEqual(values['CRM_ROUTE_KEY'], 'ERROR')

    def test_non_string_destination_is_invalid(self):
        for destination in ([], {}, True, 12):
            with self.subTest(destination=destination):
                self.state['payload'] = record(destination)
                values, _, _ = self.lookup()
                self.assertEqual(values['CRM_ROUTE_KEY'], 'ERROR')

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

    def test_server_decisions_are_used_for_either_menu_option_without_local_rules(self):
        for option in ('1', '2'):
            for destination in ('CALL_CENTER', 'PORTAL', 'END_CALL', 'INVALID_CUIL'):
                with self.subTest(option=option, destination=destination):
                    self.state['payload'] = record(destination)
                    values, _, _ = self.lookup(option=option)
                    self.assertEqual(values['CRM_ROUTE_KEY'], destination)

    def test_destination_text_is_preserved_and_safely_escaped(self):
        destination = 'Atención "Especial" \\ Norte'
        self.state['payload'] = record(destination)
        values, _, _ = self.lookup(option='2')
        self.assertEqual(values['CRM_ROUTE_KEY'], destination)

    def test_confirmed_short_cuil_is_sent_to_the_api_for_validation(self):
        self.state['payload'] = record('INVALID_CUIL')
        for cuil in ('12', '20000000001'):
            with self.subTest(cuil=cuil):
                values, _, _ = self.lookup(cuil=cuil)
                self.assertEqual(values['CRM_ROUTE_KEY'], 'INVALID_CUIL')
                query = parse_qs(urlsplit(self.state['requests'][-1]['path']).query,
                                 keep_blank_values=True)
                self.assertEqual(query['cuil'], [cuil.replace(' ', '').replace('-', '')])

    def test_technical_errors_return_error_and_keep_the_answer_hook(self):
        for status in (201, 302, 400, 401, 403, 404, 500, 503):
            with self.subTest(status=status):
                self.state['get_status'] = status
                values, _, stderr = self.lookup()
                self.assertEqual(values['CRM_ROUTE_KEY'], 'ERROR')
                self.assertEqual(values['CRM_PRESTADORA'], '')
                self.assertEqual(values['CRM_CALL_ID'], 'caller.123')
                self.assertEqual(values['QAGI'], 'crm_set_atencion.agi.php')
                self.assertNotIn('20000000001', stderr)

    def test_bad_json_types_and_oversized_responses_are_technical_errors(self):
        cases = [b'not JSON', b'[]', {}, {'cuilValido': True, 'prestadora': 'IGNORED'},
                 record('bad\nvalue'), record('x' * 513), b' ' * 17000]
        for payload in cases:
            with self.subTest(payload_type=type(payload).__name__):
                self.state['payload'] = payload
                values, _, _ = self.lookup()
                self.assertEqual(values['CRM_ROUTE_KEY'], 'ERROR')
                self.assertEqual(values['CRM_PRESTADORA'], '')

    def test_lookup_times_out_at_three_seconds(self):
        self.state['payload'] = record('PORTAL')
        self.state['get_delay'] = 4.2
        started = time.monotonic()
        values, _, _ = self.lookup()
        elapsed = time.monotonic() - started
        self.assertEqual(values['CRM_ROUTE_KEY'], 'ERROR')
        self.assertGreater(elapsed, 2.7)
        self.assertLess(elapsed, 3.8)

    def test_original_id_survives_a_cuil_retry_on_a_different_channel(self):
        first, _, _ = self.lookup(uniqueid='ingress.42')
        second, _, _ = self.lookup(cuil='27000000002', variables=first, uniqueid='local.99')
        self.assertEqual(second['CRM_CALL_ID'], 'ingress.42')
        query = parse_qs(urlsplit(self.state['requests'][-1]['path']).query)
        self.assertEqual(query['llamada'], ['ingress.42'])
        self.assertEqual(query['cuil'], ['27000000002'])

    def test_maximum_original_id_is_preserved_and_overlong_id_is_not_truncated(self):
        values, _, _ = self.lookup(uniqueid='a' * 40)
        self.assertEqual(values['CRM_CALL_ID'], 'a' * 40)
        count = len(self.state['requests'])
        values, _, _ = self.lookup(uniqueid='b' * 41)
        self.assertEqual(values['CRM_ROUTE_KEY'], 'ERROR')
        self.assertEqual(len(self.state['requests']), count)
        self.assertNotIn('CRM_CALL_ID', values)

    def test_foreign_queue_hooks_are_preserved(self):
        for name in ('QAGI', 'VQ_AGI'):
            with self.subTest(name=name):
                values, _, _ = self.lookup(variables={name: 'foreign_crm_set_atencion.agi.php'})
                self.assertEqual(values[name], 'foreign_crm_set_atencion.agi.php')
                self.assertEqual(values['CRM_QAGI_CONFLICT'], '1')

    def test_any_menu_digit_is_forwarded_for_the_server_to_decide(self):
        for option in ('0', '3', '9'):
            with self.subTest(option=option):
                values, _, _ = self.lookup(option=option)
                self.assertEqual(values['CRM_ROUTE_KEY'], 'CALL_CENTER')
                query = parse_qs(urlsplit(self.state['requests'][-1]['path']).query)
                self.assertEqual(query['opcion'], [option])
        self.assertEqual(len(self.state['requests']), 3)

    def test_menu_option_can_be_read_from_the_inherited_ivr_variable(self):
        values, _, _ = self.lookup(option='', variables=dict(IVR_DIGIT_PRESSED='2'))
        self.assertEqual(values['CRM_ROUTE_KEY'], 'CALL_CENTER')
        self.assertEqual(len(self.state['requests']), 1)
        query = parse_qs(urlsplit(self.state['requests'][0]['path']).query)
        self.assertEqual(query['opcion'], ['2'])

    def test_configuration_array_is_a_safe_error_instead_of_a_php_fatal(self):
        self.conf.write_text('[atenciones]\nbase_url[]=invalid\napi_key=test-secret\n')
        values, _, stderr = self.lookup()
        self.assertEqual(values['CRM_ROUTE_KEY'], 'ERROR')
        self.assertNotIn('Fatal', stderr)
        self.assertEqual(self.state['requests'], [])

    def test_extra_affiliate_fields_are_not_used_or_exported(self):
        self.state['payload'] = record('PORTAL', referencias=['PRIVATE_TEST_REFERENCE'],
                                       prestadora='PRIVATE_TEST_PROVIDER', esTitular=False,
                                       activo=False, esProveedor=True)
        values, commands, stderr = self.lookup(option='2')
        self.assertEqual(values['CRM_ROUTE_KEY'], 'PORTAL')
        output = '\n'.join(commands) + stderr + json.dumps(values)
        for sensitive in ('PRIVATE_TEST_REFERENCE', 'PRIVATE_TEST_PROVIDER', 'test-secret', '20000000001'):
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
        self.state['payload'] = record('PORTAL')
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
        self.assertEqual(values['CRM_ROUTE_KEY'], 'ERROR')
        self.assertEqual(self.state['requests'], [])
        trusted = conf.replace('[runtime]', 'ca_file = "%s"\n[runtime]' % cert)
        self.conf.write_text(trusted.replace('https://localhost:', 'https://127.0.0.1:'))
        values, _, _ = self.lookup()
        self.assertEqual(values['CRM_ROUTE_KEY'], 'ERROR')
        self.assertEqual(self.state['requests'], [])
        self.conf.write_text(trusted)
        values, _, _ = self.lookup()
        self.assertEqual(values['CRM_ROUTE_KEY'], 'PORTAL')
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
            result = subprocess.run([PHP, str(ROOT / 'crm_set_atencion.agi.php'), '--send', str(job)],
                                    env=env, capture_output=True, text=True, timeout=2)
            self.assertEqual(result.returncode, 0)
            self.assertNotIn('forbidden', result.stderr)
        self.assertTrue(outside.exists())
        self.assertFalse(malformed.exists())
        self.assertEqual(self.state['requests'], [])

    def test_documented_mock_fixtures_work_with_the_actual_agi(self):
        spec = importlib.util.spec_from_file_location('atenciones_mock', Path(__file__).parent / 'fixtures/mock_atenciones.py')
        mock = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mock)
        self.server.RequestHandlerClass = mock.make_handler('test-secret')
        cases = [('20000000001', '1', 'END_CALL'),
                 ('20000000001', '2', 'CALL_CENTER'),
                 ('20000000028', '2', 'PORTAL'),
                 ('20000000036', '1', 'CALL_CENTER'),
                 ('20000000036', '2', 'END_CALL'),
                 ('20000000044', '2', 'END_CALL'),
                 ('30000000007', '1', 'END_CALL'),
                 ('20000000052', '1', 'CALL_CENTER'),
                 ('20000000060', '2', 'ATENCION_ESPECIAL'),
                 ('123', '1', 'INVALID_CUIL')]
        for cuil, option, destination in cases:
            with self.subTest(cuil=cuil, option=option):
                values, _, _ = self.lookup(option=option, cuil=cuil)
                self.assertEqual(values['CRM_ROUTE_KEY'], destination)


if __name__ == '__main__':
    unittest.main()
