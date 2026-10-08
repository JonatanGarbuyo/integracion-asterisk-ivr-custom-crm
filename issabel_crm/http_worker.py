"""HTTP subprocess. Its supervisor enforces the total wall-clock budget."""
import json
import sys
import urllib.error
import urllib.request

MAX_RESPONSE = 65536


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def main():
    work = json.load(sys.stdin)
    headers = {'Accept': 'application/json'}
    if work.get('token'):
        headers['Authorization'] = 'Bearer ' + work['token']
    data = None
    if work['method'] == 'POST':
        data = json.dumps(work['payload']).encode('utf-8')
        headers['Content-Type'] = 'application/json'
        headers['Idempotency-Key'] = work['payload']['event_id']
    request = urllib.request.Request(work['url'], data=data, headers=headers, method=work['method'])
    try:
        # Ignore proxy environment variables on a PBX; use the configured endpoint directly.
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
        with opener.open(request, timeout=work['timeout']) as response:
            if work['method'] == 'POST':
                result = {'status': response.status}
            else:
                body = response.read(MAX_RESPONSE + 1)
                result = ({'error': 'response_too_large'} if len(body) > MAX_RESPONSE else
                          {'status': response.status, 'body': json.loads(body.decode('utf-8'))})
    except urllib.error.HTTPError as error:
        result = {'status': error.code}
    except (ValueError, UnicodeError):
        result = {'error': 'invalid_response'}
    except (OSError, urllib.error.URLError):
        result = {'error': 'transport_error'}
    sys.stdout.write(json.dumps(result))


if __name__ == '__main__':
    main()
