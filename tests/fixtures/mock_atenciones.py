#!/usr/bin/env python3
"""Atenciones contract mock: synthetic data, loopback only, Python 3.6+."""
import argparse
import json
import os
import re
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
from urllib.parse import parse_qs, urlsplit


def affiliate(**changes):
    value = dict(cuilValido=True, esTitular=False, activo=False,
                 prestadora=None, provincia=None, referencias=[], esProveedor=False)
    value.update(changes)
    return value


DIRECTORY = {
    '20000000001': affiliate(esTitular=True, activo=True, prestadora='Prestadora A'),
    '20000000028': affiliate(esTitular=True, activo=True, prestadora='Prestadora B',
                             referencias=['REFERENCIA_FICTICIA']),
    '20000000036': affiliate(esTitular=True, prestadora='Prestadora A'),
    '20000000044': affiliate(prestadora='Prestadora B'),
    '30000000007': affiliate(esProveedor=True),
}


def valid_cuil(value):
    if not re.fullmatch(r'[0-9]{11}', value):
        return False
    total = sum(int(digit) * weight for digit, weight in
                zip(value[:10], (5, 4, 3, 2, 7, 6, 5, 4, 3, 2)))
    remainder = 11 - total % 11
    return remainder != 10 and int(value[-1]) == (0 if remainder == 11 else remainder)


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


def make_handler(api_key, get_delay=0, post_delay=0, get_status=200, post_status=200):
    validations = {}
    lock = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass  # Never print the GET URL containing the CUIL.

        def reply(self, code, payload=None):
            body = b'' if payload is None else json.dumps(payload).encode('utf-8')
            self.send_response(code)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def authorized(self):
            if not api_key:
                self.reply(503)
                return False
            if self.headers.get('X-Api-Key') != api_key:
                self.reply(401)
                return False
            return True

        @staticmethod
        def call_id(value):
            return bool(value) and len(value) <= 40

        def do_GET(self):
            if not self.authorized():
                return
            parsed = urlsplit(self.path)
            if parsed.path != '/Atenciones/api/central/preatendedor':
                self.reply(404)
                return
            query = parse_qs(parsed.query, keep_blank_values=True)
            option = query.get('opcion', [''])[0]
            call = query.get('llamada', [''])[0]
            if option not in ('1', '2') or not self.call_id(call):
                self.reply(400, dict(mensaje='Parametros invalidos'))
                return
            cuil = re.sub(r'[\s-]', '', query.get('cuil', [''])[0])
            result = (DIRECTORY.get(cuil, affiliate()) if valid_cuil(cuil)
                      else affiliate(cuilValido=False))
            time.sleep(get_delay)
            if get_status != 200:
                self.reply(get_status)
                return
            with lock:
                validations[call] = result  # Ephemeral, no CUIL or durable logs.
            self.reply(200, result)

        def do_POST(self):
            if not self.authorized():
                return
            parsed = urlsplit(self.path)
            if parsed.path != '/Atenciones/api/central/llamada-atendida':
                self.reply(404)
                return
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if length < 0 or length > 1024:
                    raise ValueError()
                form = parse_qs(parsed.query, keep_blank_values=True)
                if length:
                    if self.headers.get('Content-Type', '').split(';')[0] != 'application/x-www-form-urlencoded':
                        raise ValueError()
                    form.update(parse_qs(self.rfile.read(length).decode(), keep_blank_values=True))
                call = form.get('llamada', [''])[0]
                extension = form.get('interno', [''])[0]
                if not self.call_id(call) or not re.fullmatch(r'[0-9]{1,10}', extension):
                    raise ValueError()
            except (ValueError, UnicodeError):
                self.reply(400, dict(mensaje='Parametros invalidos'))
                return
            time.sleep(post_delay)
            if post_status != 200:
                self.reply(post_status)
                return
            with lock:
                known = call in validations
            result = ('SIN_VALIDACION' if not known else
                      'OK' if extension in ('1001', '1002') else 'SIN_OPERADOR')
            self.reply(200, dict(resultado=result))

    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8899)
    parser.add_argument('--get-delay', type=float, default=0)
    parser.add_argument('--post-delay', type=float, default=0)
    parser.add_argument('--get-status', type=int, default=200)
    parser.add_argument('--post-status', type=int, default=200)
    args = parser.parse_args()
    handler = make_handler(os.environ.get('ATENCIONES_MOCK_API_KEY', 'testing-only-key'),
                           args.get_delay, args.post_delay, args.get_status, args.post_status)
    server = ThreadedHTTPServer(('127.0.0.1', args.port), handler)
    print('Mock Atenciones: loopback puerto %s; datos ficticios, sin logs HTTP.' % args.port)
    server.serve_forever()


if __name__ == '__main__':
    main()
