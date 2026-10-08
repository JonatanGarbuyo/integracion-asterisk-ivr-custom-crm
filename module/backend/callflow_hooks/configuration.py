"""Single .conf source shared by the native form, CLI and call runtime."""
import configparser
import fcntl
import hashlib
import io
import json
import os
import pathlib
import re
import sys
import tempfile

IDENTIFIER = re.compile(r'^[a-z][a-z0-9_-]{0,39}$')
DESTINATION = re.compile(r'^[A-Za-z0-9_-]{1,80},[A-Za-z0-9_*#-]{1,80},[1-9][0-9]{0,5}$')
VARIABLE = re.compile(r'^[A-Za-z][A-Za-z0-9_]{0,79}$')
CORE_FIELDS = {
    'enabled': {'type': 'boolean', 'label': 'Habilitado', 'default': True},
    'next_destination': {'type': 'string', 'label': 'Destino siguiente (contexto,extensión,prioridad)', 'required': True, 'max_length': 170},
    'fallback_destination': {'type': 'string', 'label': 'Destino de contingencia', 'required': True, 'max_length': 170},
    'execution_budget_ms': {'type': 'integer', 'label': 'Límite del handler (ms)', 'default': 1000, 'minimum': 50, 'maximum': 5000},
    'input_source': {'type': 'choice', 'label': 'Fuente de entrada', 'default': 'none', 'options': ['none', 'dtmf', 'callerid', 'channel']},
    'input_variable': {'type': 'string', 'label': 'Variable de entrada del canal', 'default': '', 'max_length': 80},
    'input_prompt': {'type': 'string', 'label': 'Audio para solicitar dígitos', 'default': '', 'max_length': 100},
    'input_max_digits': {'type': 'integer', 'label': 'Máximo de dígitos', 'default': 20, 'minimum': 1, 'maximum': 40},
    'input_timeout_ms': {'type': 'integer', 'label': 'Tiempo para ingresar dígitos (ms)', 'default': 5000, 'minimum': 100, 'maximum': 15000}
}


class ConfigurationError(ValueError):
    pass


def validate_fields(fields, values):
    if not isinstance(values, dict) or set(values) - set(fields):
        raise ConfigurationError('Campos desconocidos')
    result = {}
    for name, field in fields.items():
        value = values.get(name, field.get('default'))
        kind = field['type']
        if kind in ('string', 'secret', 'choice'):
            if not isinstance(value, str) or len(value) > field.get('max_length', 2000):
                raise ConfigurationError('Valor inválido: ' + name)
            if field.get('required') and not value:
                raise ConfigurationError('Campo requerido: ' + name)
            if 'pattern' in field and not re.fullmatch(field['pattern'], value):
                raise ConfigurationError('Formato inválido: ' + name)
            if kind == 'choice' and value not in field['options']:
                raise ConfigurationError('Opción inválida: ' + name)
        elif kind == 'integer':
            if type(value) is not int or not field.get('minimum', -2147483648) <= value <= field.get('maximum', 2147483647):
                raise ConfigurationError('Número inválido: ' + name)
        elif kind == 'boolean':
            if type(value) is not bool:
                raise ConfigurationError('Booleano inválido: ' + name)
        else:
            raise ConfigurationError('Tipo de campo no soportado')
        result[name] = value
    return result


class Configuration:
    def __init__(self, path, extensions):
        self.path = pathlib.Path(path)
        self.extensions = pathlib.Path(extensions)
        self.catalog = {}
        for filename in sorted(self.extensions.glob('*/manifest.json')):
            module = json.loads(filename.read_text(encoding='utf-8'))
            identifier = module['identifier']
            if not IDENTIFIER.fullmatch(identifier) or identifier in self.catalog or module['contract_version'] != 1:
                raise ConfigurationError('Extensión inválida')
            command = module['command']
            if not isinstance(command, list) or not command or not all(isinstance(x, str) and x for x in command):
                raise ConfigurationError('Comando de extensión inválido')
            module['_directory'] = str(filename.parent.resolve())
            module['_command'] = [sys.executable if command[0] == '@python' else command[0]] + command[1:]
            if not os.path.isabs(module['_command'][0]):
                raise ConfigurationError('El ejecutable debe tener ruta absoluta')
            for field_name in module['fields']:
                if not VARIABLE.fullmatch(field_name):
                    raise ConfigurationError('Nombre de campo inválido')
                field = module['fields'][field_name]
                if field['type'] == 'secret' and field.get('default', ''):
                    raise ConfigurationError('Las credenciales no admiten valores por defecto')
            self.catalog[identifier] = module

    def normalize(self, profile):
        if not isinstance(profile, dict) or set(profile) - (set(CORE_FIELDS) | {'identifier', 'extension', 'settings'}):
            raise ConfigurationError('Perfil inválido')
        identifier = profile.get('identifier', '')
        if not isinstance(identifier, str) or not IDENTIFIER.fullmatch(identifier):
            raise ConfigurationError('Identificador de perfil inválido')
        extension = profile.get('extension')
        if extension not in self.catalog:
            raise ConfigurationError('Extensión desconocida')
        normalized = validate_fields(CORE_FIELDS, {k: v for k, v in profile.items() if k in CORE_FIELDS})
        for key in ('next_destination', 'fallback_destination'):
            if not DESTINATION.fullmatch(normalized[key]) or normalized[key].startswith('callflow-profile-'):
                raise ConfigurationError('Destino inválido: ' + key)
        if normalized['input_source'] == 'channel' and not VARIABLE.fullmatch(normalized['input_variable']):
            raise ConfigurationError('Variable de entrada inválida')
        prompt = normalized['input_prompt']
        if prompt and (not re.fullmatch(r'[A-Za-z0-9_/-]+', prompt) or '..' in prompt or prompt.startswith('/')):
            raise ConfigurationError('Audio inválido')
        normalized.update(identifier=identifier, extension=extension,
                          settings=validate_fields(self.catalog[extension]['fields'], profile.get('settings', {})))
        return normalized

    def read(self):
        data = self.path.read_bytes() if self.path.exists() else b''
        if len(data) > 262144:
            raise ConfigurationError('Configuración demasiado grande')
        version = hashlib.sha256(data).hexdigest()
        parser = configparser.ConfigParser(interpolation=None)
        parser.read_string(data.decode('utf-8'))
        profiles = {}
        if parser.defaults():
            raise ConfigurationError('No se admite sección DEFAULT')
        for section in parser.sections():
            if not section.startswith('profile:'):
                raise ConfigurationError('Sección desconocida')
            identifier = section[len('profile:'):]
            raw = dict(parser[section])
            for key in ('execution_budget_ms', 'input_max_digits', 'input_timeout_ms'):
                if key in raw:
                    raw[key] = int(raw[key])
            if 'enabled' in raw:
                if raw['enabled'].lower() not in ('true', 'false'):
                    raise ConfigurationError('Habilitado debe ser true o false')
                raw['enabled'] = raw['enabled'].lower() == 'true'
            raw['settings'] = json.loads(raw.get('settings', '{}'))
            raw['identifier'] = identifier
            profiles[identifier] = self.normalize(raw)
        return version, profiles

    def describe(self):
        version, profiles = self.read()
        public = []
        for identifier, profile in sorted(profiles.items()):
            profile = dict(profile, settings=dict(profile['settings']))
            fields = self.catalog[profile['extension']]['fields']
            profile['configured_secrets'] = [k for k, field in fields.items() if field['type'] == 'secret' and profile['settings'][k]]
            for key, field in fields.items():
                if field['type'] == 'secret':
                    profile['settings'][key] = ''
            profile['custom_destination'] = 'callflow-profile-{},s,1'.format(identifier)
            public.append(profile)
        extensions = [{k: module[k] for k in ('identifier', 'title', 'fields')} for module in self.catalog.values()]
        return dict(ok=True, configuration_version=version, profiles=public, extensions=extensions, core_fields=CORE_FIELDS)

    def save(self, profile, expected_version):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(str(self.path) + '.lock', 'a') as lock:
            os.chmod(lock.name, 0o600)
            fcntl.flock(lock, fcntl.LOCK_EX)
            version, profiles = self.read()
            if version != expected_version:
                raise ConfigurationError('La configuración cambió; recargar el formulario')
            profile = dict(profile)
            old = profiles.get(profile.get('identifier'))
            if old and old['extension'] == profile.get('extension'):
                settings = dict(profile.get('settings', {}))
                for name, field in self.catalog[old['extension']]['fields'].items():
                    if field['type'] == 'secret' and not settings.get(name):
                        settings[name] = old['settings'][name]
                profile['settings'] = settings
            normalized = self.normalize(profile)
            profiles[normalized['identifier']] = normalized
            parser = configparser.ConfigParser(interpolation=None)
            for identifier, item in sorted(profiles.items()):
                parser['profile:' + identifier] = {
                    k: json.dumps(v, ensure_ascii=False) if k == 'settings' else str(v).lower() if type(v) is bool else str(v)
                    for k, v in item.items() if k != 'identifier'}
            output = io.StringIO()
            parser.write(output)
            if len(output.getvalue().encode('utf-8')) > 262144:
                raise ConfigurationError('Configuración demasiado grande')
            fd, temporary = tempfile.mkstemp(prefix='.profiles-', dir=str(self.path.parent))
            try:
                with os.fdopen(fd, 'w', encoding='utf-8') as stream:
                    stream.write(output.getvalue())
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temporary, str(self.path))
            finally:
                if os.path.exists(temporary):
                    os.unlink(temporary)
        return self.describe()
