import signal
import sys

from .agi import AGI, Hangup
from .diagnostic import record
from .flow import notify_crm_of_queue_member_answer, route_affiliate_call


def on_hangup(signum, frame):
    raise Hangup()


def main():
    signal.signal(signal.SIGHUP, on_hangup)
    try:
        agi = AGI()
        {'identify': route_affiliate_call, 'answer': notify_crm_of_queue_member_answer}[sys.argv[1]](agi)
    except Hangup:
        record('caller_hangup')
    except Exception:
        # A technical failure never writes traceback, credentials or CRM data to AGI.
        record('agi_error')


if __name__ == '__main__':
    main()
