import json
import sys
import syslog


def record(outcome, interaction_id='', stderr=True):
    message = json.dumps({'component': 'issabel-crm', 'outcome': outcome,
                          'interaction_id': interaction_id})
    syslog.syslog(syslog.LOG_INFO, message)
    if stderr:
        sys.stderr.write(message + '\n')
