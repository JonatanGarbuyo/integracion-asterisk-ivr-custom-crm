#!/usr/bin/python3
"""Fixed local entry point. JSON stdin/stdout for administration; AGI later."""
import argparse
import configparser
import json
import pathlib
import sys

from callflow_hooks.configuration import Configuration
from callflow_hooks.runtime import AGI, ChannelClosed, run


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', default='/etc/asterisk/callflow-hooks/profiles.conf')
    parser.add_argument('--extensions', default=str(pathlib.Path(__file__).resolve().parents[1] / 'extensions'))
    parser.add_argument('action', choices=['admin', 'agi'])
    parser.add_argument('profile', nargs='?')
    args = parser.parse_args()
    if args.action == 'agi':
        channel = None
        try:
            channel = AGI(sys.stdin, sys.stdout)
            run(Configuration(args.config, args.extensions), args.profile, channel)
        except ChannelClosed:
            pass
        except (ValueError, KeyError, TypeError, OSError, configparser.Error):
            if channel:
                try:
                    channel.set('CALLFLOW_HANDLER_STATUS', 'configuration_error')
                except ChannelClosed:
                    pass
        return
    try:
        configuration = Configuration(args.config, args.extensions)
        request = json.loads(sys.stdin.read(65537))
        if request['action'] == 'describe':
            response = configuration.describe()
        elif request['action'] == 'save':
            response = configuration.save(request['profile'], request['expected_version'])
        else:
            raise ValueError('Acción desconocida')
    except (ValueError, KeyError, TypeError, OSError, configparser.Error):
        # Never include exception details: external files/values may contain secrets.
        response = dict(ok=False, error='Configuración inválida o no disponible; revisar campos, versión y permisos')
    json.dump(response, sys.stdout, ensure_ascii=False)
    sys.stdout.write('\n')


if __name__ == '__main__':
    main()
