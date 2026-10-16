#!/usr/bin/env python3
"""Mock HTTP ligero de desarrollo para Afiliados CRM (provisional, solo laboratorio).

Contrato provisional, no definitivo: pedir URL/auth/samples reales al proveedor
antes de afirmar CRM real. No usar datos reales. Solo stdlib, Python 3.6+.

  python3 mock_crm_server.py --port 8899

Endpoints:
  GET  /afiliado?cuil=11DIGITOS -> 200 {"id": "AF-..", "obra_social": "OSPACA"}
                                   404 {"error": "not_found"} si no existe
  POST /atencion (JSON)           -> 200 {"ok": true}, guarda body en --outbox
  GET  /lento?cuil=..            -> demora --delay segundos (prueba timeout)
  POST /atencion-lenta           -> demora --delay segundos (prueba no bloqueante)
"""
import argparse
import json
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
from urllib.parse import urlparse, parse_qs


DIRECTORY = {
    "20304050607": {"id": "AF-1001", "obra_social": "ospaca"},
    "20123456789": {"id": "AF-1002", "obra_social": "otra_obra"},
}


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


def make_handler(directory, delay, outbox):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def _send_json(self, code, payload):
            body = json.dumps(payload).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            parsed = urlparse(self.path)
            query = parse_qs(parsed.query)
            cuil = (query.get("cuil") or [""])[0]
            if parsed.path == "/lento":
                time.sleep(delay)
            if len(cuil) != 11 or not cuil.isdigit():
                self._send_json(400, {"error": "invalid_input"})
                return
            record = directory.get(cuil)
            if record is None:
                self._send_json(404, {"error": "not_found"})
                return
            self._send_json(200, record)

        def do_POST(self):
            if self.path not in ("/atencion", "/atencion-lenta"):
                self._send_json(404, {"error": "not_found"})
                return
            length = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(min(length, 65536)) if length else b""
            if self.path == "/atencion-lenta":
                time.sleep(delay)
            if outbox is not None:
                try:
                    with open(outbox, "ab") as handle:
                        handle.write(body + b"\n")
                except OSError:
                    pass
            self._send_json(200, {"ok": True})

    return Handler


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8899)
    parser.add_argument("--delay", type=float, default=3.0)
    parser.add_argument("--outbox", default=None)
    args = parser.parse_args()
    handler = make_handler(DIRECTORY, args.delay, args.outbox)
    server = ThreadedHTTPServer(("127.0.0.1", args.port), handler)
    print("mock CRM en http://127.0.0.1:%d (provisional, laboratorio)" % args.port)
    server.serve_forever()


if __name__ == "__main__":
    main()
