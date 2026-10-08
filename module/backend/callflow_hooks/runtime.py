"""AGI boundary and bounded JSON process execution. No business rules."""
import json
import os
import re
import signal
import subprocess
import tempfile


class ChannelClosed(Exception):
    pass


class AGI:
    def __init__(self, incoming, outgoing):
        self.incoming, self.outgoing = incoming, outgoing
        self.environment = {}
        for _ in range(100):
            line = incoming.readline(4097)
            if not line:
                raise ChannelClosed()
            if line == '\n':
                break
            key, value = line.rstrip('\n').split(':', 1)
            self.environment[key] = value.strip()
        else:
            raise ChannelClosed()

    def command(self, value):
        self.outgoing.write(value + '\n')
        self.outgoing.flush()
        response = self.incoming.readline(32769)
        match = re.match(r'200 result=(-?\d+)(?: \((.*)\))?', response.rstrip('\n'))
        if not match or match.group(1) == '-1':
            raise ChannelClosed()
        return match.group(1), match.group(2) or ''

    def set(self, name, value):
        text = str(value).replace('\\', '\\\\').replace('"', '\\"')
        if '\n' in text or '\r' in text:
            raise ValueError('Invalid channel value')
        self.command('SET VARIABLE {} "{}"'.format(name, text))

    def input(self, profile):
        source = profile['input_source']
        if source == 'callerid':
            value = self.environment.get('agi_callerid', '')
        elif source == 'channel':
            _, value = self.command('GET VARIABLE ' + profile['input_variable'])
        elif source == 'dtmf':
            self.command('ANSWER')
            value, extra = self.command('GET DATA "{}" {} {}'.format(
                profile['input_prompt'], profile['input_timeout_ms'], profile['input_max_digits']))
            if extra == 'timeout' and value == '0':
                value = ''
        else:
            value = ''
        return dict(source=source, value=value[:2048])


def execute(extension, request, budget_ms):
    """Handlers may be in any language. No shell, no AGI, no inherited stdin."""
    with tempfile.TemporaryFile() as output:
        process = subprocess.Popen(extension['_command'], cwd=extension['_directory'],
                                   stdin=subprocess.PIPE, stdout=output, stderr=subprocess.DEVNULL,
                                   start_new_session=True, close_fds=True)
        try:
            process.communicate(json.dumps(request, ensure_ascii=False, allow_nan=False).encode('utf-8'),
                                timeout=budget_ms / 1000.0)
            if process.returncode:
                raise ValueError('Handler failed')
            output.seek(0)
            result = output.read(16385)
            if len(result) > 16384:
                raise ValueError('Handler output exceeded limit')
            response = json.loads(result.decode('utf-8'), parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
            if not isinstance(response, dict) or set(response) - {'contract_version', 'action', 'context_patch', 'destination'}:
                raise ValueError('Invalid handler response')
            if type(response.get('contract_version')) is not int or response['contract_version'] != 1:
                raise ValueError('Unsupported contract')
            if response.get('action') not in ('continue', 'route') or not isinstance(response.get('context_patch', {}), dict):
                raise ValueError('Invalid handler action or context')
            if response['action'] == 'continue' and 'destination' in response:
                raise ValueError('Continue cannot override destination')
            return response
        finally:
            # Also release grandchildren that survived the handler's main process.
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait()


def run(configuration, identifier, channel):
    version, profiles = configuration.read()
    profile = profiles[identifier]
    channel.set('__CALLFLOW_PROFILE_IDENTIFIER', identifier)
    channel.set('__CALLFLOW_CONFIGURATION_VERSION', version)
    channel.set('CALLFLOW_NEXT_DESTINATION', profile['fallback_destination'])
    channel.set('__CALLFLOW_CONTEXT_JSON', '{}')
    if not profile['enabled']:
        channel.set('CALLFLOW_HANDLER_STATUS', 'disabled')
        return
    request = dict(contract_version=1, event='ivr_entry', profile_identifier=identifier,
                   configuration_version=version,
                   call=dict(unique_id=channel.environment.get('agi_uniqueid', ''),
                             channel_name=channel.environment.get('agi_channel', '')),
                   input=channel.input(profile), context={}, handler_settings=profile['settings'])
    try:
        response = execute(configuration.catalog[profile['extension']], request, profile['execution_budget_ms'])
        destination = profile['next_destination']
        if response['action'] == 'route':
            destination = response.get('destination')
            if destination not in (profile['next_destination'], profile['fallback_destination']):
                raise ValueError('Unapproved destination')
        context = json.dumps(response.get('context_patch', {}), ensure_ascii=False, allow_nan=False, separators=(',', ':'))
        channel.set('__CALLFLOW_CONTEXT_JSON', context)
        channel.set('CALLFLOW_NEXT_DESTINATION', destination)
        channel.set('CALLFLOW_HANDLER_STATUS', 'completed')
    except (OSError, ValueError, TypeError, subprocess.TimeoutExpired):
        channel.set('CALLFLOW_HANDLER_STATUS', 'fallback')

