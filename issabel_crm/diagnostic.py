import json
import sys
import syslog


def record(outcome, interaction_id='', stderr=True, destination=''):
    fields = {'component': 'callflow-hooks', 'outcome': outcome, 'interaction_id': interaction_id}
    if destination:
        fields['destination'] = destination
    message = json.dumps(fields)
    syslog.syslog(syslog.LOG_INFO, message)
    if stderr:
        sys.stderr.write(message + '\n')
