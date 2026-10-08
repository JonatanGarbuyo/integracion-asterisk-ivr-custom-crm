"""Example extension. It knows JSON only; replace with any local executable."""
import json
import sys

request = json.load(sys.stdin)
json.dump({'contract_version': 1, 'action': 'continue', 'context_patch': {
    'greeting': request['handler_settings']['greeting'],
    'input_value': request['input']['value']}}, sys.stdout, ensure_ascii=False)
sys.stdout.write('\n')
