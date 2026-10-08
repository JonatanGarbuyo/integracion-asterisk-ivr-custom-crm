import datetime
import re
import uuid
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .config import ConfigError, identifier, read_config
from .diagnostic import record
from .notify import launch
from .transport import request


def valid_cuil(value, checksum):
    if not re.fullmatch(r'[0-9]{11}', value):
        return False
    if not checksum:
        return True
    weights = (5, 4, 3, 2, 7, 6, 5, 4, 3, 2)
    digit = (11 - sum(int(c) * w for c, w in zip(value[:10], weights)) % 11) % 11
    return digit < 10 and digit == int(value[-1])


def identify(agi):
    # Erase all previously associated affiliate data before attempting lookup.
    for name in ('CRM_CUIL', 'CRM_AFFILIATE_ID', 'CRM_OBRA', 'CRM_QUEUE'):
        agi.set('__' + name, '')
    interaction = str(uuid.uuid4())
    agi.set('__CRM_INTERACTION_ID', interaction)
    agi.set('__CRM_UNIQUEID', agi.environment.get('agi_uniqueid', ''))
    agi.set('__CRM_LINKEDID', agi.evaluate('${CHANNEL(linkedid)}') or agi.environment.get('agi_uniqueid', ''))
    try:
        config = read_config()
    except ConfigError:
        agi.set('CRM_RESULT', 'config_error')
        record('config_error', interaction)
        return  # dialplan has pre-seeded a validated fallback
    agi.set('CRM_DEST_TYPE', 'queue')
    agi.set('CRM_DEST', config['fallback_queue'])
    agi.set('__CRM_PBX_ID', config['pbx_id'])
    cuil = ''
    for _ in range(config['attempts']):
        cuil = agi.collect(config['prompt'], config['digit_timeout_ms'], config['terminator'])
        if valid_cuil(cuil, config['validate_checksum']):
            break
        agi.playback(config['invalid_prompt'])
    else:
        agi.set('CRM_RESULT', 'invalid_cuil')
        record('invalid_cuil', interaction)
        return
    agi.set('__CRM_CUIL', cuil)
    url = urlsplit(config['lookup_url'])
    query = [(k, v) for k, v in parse_qsl(url.query) if k != 'cuil'] + [('cuil', cuil)]
    lookup_url = urlunsplit((url.scheme, url.netloc, url.path, urlencode(query), ''))
    response = request({'method': 'GET', 'url': lookup_url, 'token': config['lookup_token']},
                       config['lookup_timeout'])
    outcome = response.get('error', '')
    if not outcome:
        status = response.get('status', 0)
        if status == 404:
            outcome = 'not_found'
        elif status != 200:
            outcome = 'http_error'
        else:
            body = response.get('body')
            if not isinstance(body, dict) or not identifier(body.get('affiliate_id')):
                outcome = 'invalid_response'
            elif isinstance(body.get('obra_social'), list):
                outcome = 'ambiguous_obra'
            elif not identifier(body.get('obra_social')):
                outcome = 'invalid_response'
            elif body['obra_social'] not in config['routes']:
                outcome = 'unmapped_obra'
            else:
                kind, destination = config['routes'][body['obra_social']]
                agi.set('__CRM_AFFILIATE_ID', body['affiliate_id'])
                agi.set('__CRM_OBRA', body['obra_social'])
                agi.set('CRM_DEST_TYPE', kind)
                agi.set('CRM_DEST', destination)
                outcome = 'found'
    agi.set('CRM_RESULT', outcome)
    record(outcome, interaction)


def answer(agi):
    # Snapshot member data before chaining an existing Queue AGI.
    values = {name: agi.get(name) for name in (
        'CRM_INTERACTION_ID', 'CRM_AFFILIATE_ID', 'CRM_PBX_ID', 'CRM_UNIQUEID',
        'CRM_LINKEDID', 'CRM_QUEUE', 'MEMBERINTERFACE', 'MEMBERNAME', 'CRM_PREVIOUS_QAGI')}
    previous = values['CRM_PREVIOUS_QAGI']
    if previous and 'issabel-crm-answer.agi' not in previous:
        agi.execute('AGI', previous)
    if not values['CRM_AFFILIATE_ID'] or not values['CRM_INTERACTION_ID']:
        record('notification_no_affiliate', values['CRM_INTERACTION_ID'])
        return
    try:
        config = read_config()
    except ConfigError:
        record('notification_config_error', values['CRM_INTERACTION_ID'])
        return
    member = values['MEMBERINTERFACE']
    agent = config['agents'].get(member)
    if not agent:
        record('notification_unmapped_member', values['CRM_INTERACTION_ID'])
        return
    payload = {
        'schema_version': 1, 'event_type': 'queue_member_answered',
        'interaction_id': values['CRM_INTERACTION_ID'], 'event_id': str(uuid.uuid4()),
        'affiliate_id': values['CRM_AFFILIATE_ID'], 'pbx_id': values['CRM_PBX_ID'],
        'uniqueid': values['CRM_UNIQUEID'], 'linkedid': values['CRM_LINKEDID'],
        'member_interface': member, 'member_name': values['MEMBERNAME'][:200],
        'queue': values['CRM_QUEUE'],
        'answered_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    payload.update(agent)
    record('notification_' + launch(config, payload), values['CRM_INTERACTION_ID'])
