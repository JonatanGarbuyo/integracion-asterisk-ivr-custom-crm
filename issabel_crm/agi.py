"""Minimal AGI wire client. stdout is exclusively the Asterisk protocol."""
import re
import sys


class Hangup(Exception):
    pass


def quoted(value):
    value = str(value)
    if any(c in value for c in ('\n', '\r', '\x00')):
        raise ValueError('Invalid AGI argument')
    return '"' + value.replace('\\', '\\\\').replace('"', '\\"') + '"'


class AGI:
    def __init__(self):
        self.environment = {}
        for line in sys.stdin:
            if not line.strip():
                break
            key, separator, value = line.partition(':')
            if separator:
                self.environment[key] = value.strip()

    def command(self, text):
        sys.stdout.write(text + '\n')
        sys.stdout.flush()
        line = sys.stdin.readline()
        if not line or line.startswith('HANGUP'):
            raise Hangup()
        match = re.fullmatch(r'200 result=([^\s]*)(?:\s+\((.*)\))?(?:\s+endpos=-?\d+)?\s*', line.rstrip())
        if not match:
            raise ValueError('Unexpected AGI response')
        if match.group(1) == '-1':
            raise Hangup()
        return match.group(1), match.group(2) or ''

    def get(self, name):
        result, value = self.command('GET VARIABLE ' + quoted(name))
        return value if result == '1' else ''

    def evaluate(self, expression):
        result, value = self.command('GET FULL VARIABLE ' + quoted(expression))
        return value if result == '1' else ''

    def set(self, name, value):
        self.command('SET VARIABLE ' + quoted(name) + ' ' + quoted(value))

    def collect(self, prompt, timeout_ms, terminator):
        escape = '0123456789*#'
        result, _ = self.command('GET OPTION ' + quoted(prompt) + ' ' + quoted(escape) + ' ' + str(timeout_ms))
        digits = ''
        for _ in range(13):
            if not result or result == '0':
                return ''  # an incomplete identifier is not accepted on timeout
            character = chr(int(result))
            if character == terminator:
                return digits
            if character not in '0123456789' or len(digits) >= 11:
                return ''
            digits += character
            result, _ = self.command('WAIT FOR DIGIT ' + str(timeout_ms))
        return ''

    def playback(self, prompt):
        if prompt:
            self.command('STREAM FILE ' + quoted(prompt) + ' ""')

    def execute(self, application, argument):
        return self.command('EXEC ' + quoted(application) + ' ' + quoted(argument))
