"""Ephemeral HTTP CRM double with an operator inbox and fault injection."""
import argparse
from collections import deque
import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
import threading
import time
from urllib.parse import parse_qs, urlsplit

FIXTURES = {
    '20123456786': {'affiliate_id': 'af-demo-1', 'obra_social': 'OS_A'},
    '27234567891': {'affiliate_id': 'af-demo-2', 'obra_social': 'OS_B'},
    '20345678906': {'affiliate_id': 'af-demo-external', 'obra_social': 'OS_EXTERNAL'},
    '20456789014': {'affiliate_id': 'af-demo-ambiguous', 'obra_social': ['OS_A', 'OS_B']},
    '20567890121': {'affiliate_id': 'af-demo-unmapped', 'obra_social': 'UNMAPPED'},
}

DASHBOARD = '''<!doctype html><html lang="es"><meta charset="utf-8">
<title>CRM simulado — operador</title>
<style>body{font:16px system-ui;margin:2rem;max-width:1000px}input{font:inherit;padding:.5rem}
table{border-collapse:collapse;width:100%;margin-top:1rem}td,th{padding:.6rem;border-bottom:1px solid #ccc;text-align:left}</style>
<h1>CRM simulado</h1><p>Datos ficticios; avisos conservados sólo en memoria.</p>
<label>Usuario CRM <input id="user" value="crm-user-a"></label><p id="state"></p>
<table><thead><tr><th>Afiliado</th><th>Miembro</th><th>Cola</th><th>Interacción</th></tr></thead><tbody id="rows"></tbody></table>
<script>
async function refresh(){try{
const r=await fetch('/notifications?crm_user_id='+encodeURIComponent(document.getElementById('user').value));
if(!r.ok)throw Error('HTTP '+r.status);const notices=await r.json();
const rows=document.getElementById('rows');rows.replaceChildren();
for(const n of notices.slice().reverse()){const tr=document.createElement('tr');
for(const key of ['affiliate_id','member_interface','queue','interaction_id']){const td=document.createElement('td');td.textContent=n[key]||'';tr.appendChild(td)}rows.appendChild(tr)}
document.getElementById('state').textContent=notices.length+' avisos para este usuario';
}catch(e){document.getElementById('state').textContent=e.message}}
setInterval(refresh,1000);refresh();</script></html>'''


class Server(ThreadingMixIn, HTTPServer):
    daemon_threads = True

    def __init__(self, address, options):
        super().__init__(address, Handler)
        self.options = options
        self.notices = deque(maxlen=500)
        self.lock = threading.Lock()
        self.token = os.environ.get(options.token_env, '')
        self.fixtures = FIXTURES
        if options.fixtures:
            with open(options.fixtures, encoding='utf-8') as source:
                self.fixtures = json.load(source)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass  # request paths contain CUIL; never log them

    def response(self, status, body=None):
        raw = b'' if body is None else json.dumps(body).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(raw)))
        self.end_headers()
        try:
            if self.server.options.trickle_interval:
                for byte in raw:
                    self.wfile.write(bytes([byte]))
                    self.wfile.flush()
                    time.sleep(self.server.options.trickle_interval)
            else:
                self.wfile.write(raw)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def authorized(self):
        if self.server.token and self.headers.get('Authorization') != 'Bearer ' + self.server.token:
            self.response(401, {'error': 'unauthorized'})
            return False
        return True

    def do_GET(self):
        url = urlsplit(self.path)
        if url.path == '/':
            raw = DASHBOARD.encode()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
            return
        if not self.authorized():
            return
        query = parse_qs(url.query)
        if url.path == '/affiliates':
            time.sleep(self.server.options.lookup_delay)
            if self.server.options.lookup_status != 200:
                self.response(self.server.options.lookup_status, {'error': 'injected'})
                return
            affiliate = self.server.fixtures.get(query.get('cuil', [''])[0])
            self.response(200 if affiliate else 404, affiliate or {'error': 'not_found'})
        elif url.path == '/notifications':
            user = query.get('crm_user_id', [''])[0]
            with self.server.lock:
                notices = [n for n in self.server.notices if not user or n['crm_user_id'] == user]
            self.response(200, notices)
        else:
            self.response(404, {'error': 'unknown_endpoint'})

    def do_POST(self):
        if not self.authorized():
            return
        if urlsplit(self.path).path != '/answered':
            self.response(404)
            return
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if not 0 < size <= 8192:
                raise ValueError()
            payload = json.loads(self.rfile.read(size).decode())
            required = ('interaction_id', 'event_id', 'affiliate_id', 'crm_user_id',
                        'member_interface', 'queue', 'answered_at', 'pbx_id', 'uniqueid', 'linkedid')
            if not isinstance(payload, dict) or not all(isinstance(payload.get(k), str) and payload[k] for k in required):
                raise ValueError()
            if payload.get('schema_version') != 1 or payload.get('event_type') != 'queue_member_answered':
                raise ValueError()
        except (ValueError, UnicodeError):
            self.response(400, {'error': 'invalid_payload'})
            return
        time.sleep(self.server.options.notify_delay)
        if self.server.options.notify_status == 204:
            with self.server.lock:
                if not any(n['event_id'] == payload['event_id'] for n in self.server.notices):
                    self.server.notices.append(payload)
        self.response(self.server.options.notify_status)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8080)
    parser.add_argument('--fixtures')
    parser.add_argument('--token-env', default='MOCK_CRM_TOKEN')
    parser.add_argument('--lookup-delay', type=float, default=0)
    parser.add_argument('--notify-delay', type=float, default=0)
    parser.add_argument('--lookup-status', type=int, default=200)
    parser.add_argument('--notify-status', type=int, default=204)
    parser.add_argument('--trickle-interval', type=float, default=0)
    options = parser.parse_args()
    server = Server((options.host, options.port), options)
    print(json.dumps({'url': 'http://' + options.host + ':' + str(server.server_port)}), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
