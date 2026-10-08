"""One read-only, validated configuration snapshot per AGI invocation."""
import configparser
import io
import hashlib
import json
import math
import os
import re
from urllib.parse import urlsplit

DEFAULT_CONFIG = '/etc/asterisk/issabel_crm.conf'
IDENTIFIER = re.compile(r'^[A-Za-z0-9_.:@-]{1,128}$')
QUEUE = re.compile(r'^[0-9]{1,10}$')
EXTERNAL = re.compile(r'^0800[0-9]{6,12}$')


class ConfigError(ValueError):
    pass


def identifier(value):
    return isinstance(value, str) and bool(IDENTIFIER.fullmatch(value))


def read_config(path=None, text=None):
    path = path or os.environ.get('ISSABEL_CRM_CONFIG', DEFAULT_CONFIG)
    parser = configparser.ConfigParser(interpolation=None, inline_comment_prefixes=None)
    parser.optionxform = str
    try:
        with (io.StringIO(text) if text is not None else open(path, encoding='utf-8')) as source:
            parser.read_file(source)
        general, crm = parser['general'], parser['crm']
        config = {
            'pbx_id': general['pbx_id'],
            'fallback_queue': general['fallback_queue'],
            'prompt': general.get('prompt', 'custom/enter-cuil'),
            'invalid_prompt': general.get('invalid_prompt', 'pbx-invalid'),
            'attempts': general.getint('attempts', 2),
            'terminator': general.get('terminator', '#'),
            'digit_timeout_ms': general.getint('digit_timeout_ms', 5000),
            'validate_checksum': general.getboolean('validate_checksum', True),
            'lookup_timeout': general.getfloat('lookup_timeout', 2),
            'notify_timeout': general.getfloat('notify_timeout', 3),
            'notify_max_workers': general.getint('notify_max_workers', 16),
            'external_timeout': general.getint('external_timeout', 30),
            'runtime_dir': general.get('runtime_dir', '/run/issabel-crm'),
            'lookup_url': crm['lookup_url'],
            'notify_url': crm['notify_url'],
            'allow_http': crm.getboolean('allow_http', False),
            'routes': {}, 'agents': {}, 'lookup_token': '', 'notify_token': '',
        }
        if not identifier(config['pbx_id']) or not QUEUE.fullmatch(config['fallback_queue']):
            raise ConfigError('Invalid PBX identifier or fallback queue')
        for key, low, high in [('attempts', 1, 5), ('digit_timeout_ms', 100, 30000),
                               ('lookup_timeout', .05, 15), ('notify_timeout', .05, 15),
                               ('notify_max_workers', 1, 128), ('external_timeout', 1, 120)]:
            if not math.isfinite(config[key]) or not low <= config[key] <= high:
                raise ConfigError('Out-of-range setting: ' + key)
        for key in ('prompt', 'invalid_prompt'):
            if not re.fullmatch(r'[A-Za-z0-9_/-]*', config[key]) or '..' in config[key]:
                raise ConfigError('Invalid sound path')
        if config['terminator'] not in ('#', '*'):
            raise ConfigError('Terminator must be # or *')
        if not config['prompt']:
            raise ConfigError('Identification prompt is required')
        if not os.path.isabs(config['runtime_dir']):
            raise ConfigError('runtime_dir must be absolute')
        for key in ('lookup_url', 'notify_url'):
            url = urlsplit(config[key])
            _ = url.port  # force validation
            if (url.scheme not in (('https', 'http') if config['allow_http'] else ('https',))
                    or not url.hostname or url.username or url.password or url.fragment
                    or any(c.isspace() for c in config[key])):
                raise ConfigError('Invalid endpoint: ' + key)
        for obra, destination in parser['routes'].items():
            kind, separator, target = destination.partition(':')
            pattern = QUEUE if kind == 'queue' else EXTERNAL if kind == 'external' else None
            if not identifier(obra) or not separator or not pattern or not pattern.fullmatch(target):
                raise ConfigError('Invalid approved destination')
            config['routes'][obra] = (kind, target)
        for member, mapping in parser['agents'].items():
            parts = [part.strip() for part in mapping.split(',')]
            if (not re.fullmatch(r'[A-Za-z0-9_/@.:-]{1,200}', member) or len(parts) > 2
                    or not identifier(parts[0]) or (len(parts) == 2 and not QUEUE.fullmatch(parts[1]))):
                raise ConfigError('Invalid member mapping')
            config['agents'][member] = {'crm_user_id': parts[0]}
            if len(parts) == 2:
                config['agents'][member]['extension'] = parts[1]
        config['agent_map_revision'] = hashlib.sha256(
            json.dumps(config['agents'], sort_keys=True).encode('utf-8')).hexdigest()
        secrets_path = crm.get('secrets_file', '')
        if secrets_path:
            if not os.path.isabs(secrets_path):
                raise ConfigError('secrets_file must be absolute')
            secrets = configparser.ConfigParser(interpolation=None)
            with open(secrets_path, encoding='utf-8') as source:
                secrets.read_file(source)
            for name in ('lookup_token', 'notify_token'):
                token = secrets['auth'].get(name, '')
                if len(token) > 2048 or any(c in token for c in ('\r', '\n', '\x00')):
                    raise ConfigError('Invalid authorization token')
                config[name] = token
        return config
    except (KeyError, OSError, ValueError, configparser.Error) as error:
        # Never include a parser error: it may contain a credential or CUIL.
        if isinstance(error, ConfigError):
            raise
        raise ConfigError('Configuration is missing or invalid') from None
