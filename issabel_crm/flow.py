import datetime
import re
import uuid
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .config import ConfigError, identifier, read_config
from .diagnostic import record
from .notify import launch
from .transport import request


def is_valid_affiliate_cuil(value, checksum):
    if not re.fullmatch(r'[0-9]{11}', value):
        return False
    if not checksum:
        return True
    weights = (5, 4, 3, 2, 7, 6, 5, 4, 3, 2)
    digit = (11 - sum(int(c) * w for c, w in zip(value[:10], weights)) % 11) % 11
    return digit < 10 and digit == int(value[-1])


def route_affiliate_call(agi):
    # Erase all previously associated affiliate data before attempting lookup.
    for name in ('CALLFLOW_AFFILIATE_CUIL', 'CALLFLOW_CRM_AFFILIATE_ID', 'CALLFLOW_CRM_OBRA_SOCIAL_CODE', 'CALLFLOW_QUEUE_NAME'):
        agi.set('__' + name, '')
    call_interaction_id = str(uuid.uuid4())
    agi.set('__CALLFLOW_CALL_INTERACTION_ID', call_interaction_id)
    agi.set('__CALLFLOW_ASTERISK_CHANNEL_UNIQUEID', agi.environment.get('agi_uniqueid', ''))
    agi.set('__CALLFLOW_ASTERISK_LINKEDID', agi.evaluate('${CHANNEL(linkedid)}') or agi.environment.get('agi_uniqueid', ''))
    try:
        config = read_config()
    except ConfigError:
        agi.set('CALLFLOW_ROUTING_STATUS', 'config_error')
        record('config_error', call_interaction_id)
        return  # dialplan has pre-seeded a validated fallback
    agi.set('CALLFLOW_ROUTING_DESTINATION_TYPE', 'queue')
    agi.set('CALLFLOW_ROUTING_DESTINATION_NUMBER', config['fallback_queue'])
    agi.set('__CALLFLOW_PBX_INSTANCE_ID', config['pbx_id'])
    agi.set('__CALLFLOW_QUEUE_MEMBER_CRM_MAP_HASH', config['queue_member_crm_map_hash'])
    cuil = ''
    for _ in range(config['attempts']):
        cuil = agi.collect(config['prompt'], config['digit_timeout_ms'], config['terminator'])
        if is_valid_affiliate_cuil(cuil, config['validate_checksum']):
            break
        agi.playback(config['invalid_prompt'])
    else:
        agi.set('CALLFLOW_ROUTING_STATUS', 'invalid_cuil')
        record('invalid_cuil', call_interaction_id, destination='queue:' + config['fallback_queue'])
        return
    agi.set('__CALLFLOW_AFFILIATE_CUIL', cuil)
    configured_lookup_url = urlsplit(config['lookup_url'])
    lookup_query_parameters = [(key, value) for key, value in parse_qsl(configured_lookup_url.query) if key != 'cuil'] + [('cuil', cuil)]
    lookup_url = urlunsplit((configured_lookup_url.scheme, configured_lookup_url.netloc, configured_lookup_url.path, urlencode(lookup_query_parameters), ''))
    affiliate_lookup_response = request({'method': 'GET', 'url': lookup_url, 'token': config['lookup_token']},
                       config['lookup_timeout'])
    destination_type, destination_number = 'queue', config['fallback_queue']
    routing_status = affiliate_lookup_response.get('error', '')
    if not routing_status:
        lookup_http_status = affiliate_lookup_response.get('status', 0)
        if lookup_http_status == 404:
            routing_status = 'not_found'
        elif lookup_http_status != 200:
            routing_status = 'http_error'
        else:
            affiliate_record = affiliate_lookup_response.get('body')
            if not isinstance(affiliate_record, dict) or not identifier(affiliate_record.get('affiliate_id')):
                routing_status = 'invalid_response'
            elif isinstance(affiliate_record.get('obra_social'), list):
                if affiliate_record['obra_social'] and all(identifier(obra) for obra in affiliate_record['obra_social']):
                    agi.set('__CALLFLOW_CRM_AFFILIATE_ID', affiliate_record['affiliate_id'])
                    routing_status = 'ambiguous_obra'
                else:
                    routing_status = 'invalid_response'
            elif not identifier(affiliate_record.get('obra_social')):
                routing_status = 'invalid_response'
            elif affiliate_record['obra_social'] not in config['routes']:
                agi.set('__CALLFLOW_CRM_AFFILIATE_ID', affiliate_record['affiliate_id'])
                routing_status = 'unmapped_obra'
            else:
                destination_type, destination_number = config['routes'][affiliate_record['obra_social']]
                agi.set('__CALLFLOW_CRM_AFFILIATE_ID', affiliate_record['affiliate_id'])
                agi.set('__CALLFLOW_CRM_OBRA_SOCIAL_CODE', affiliate_record['obra_social'])
                agi.set('CALLFLOW_ROUTING_DESTINATION_TYPE', destination_type)
                agi.set('CALLFLOW_ROUTING_DESTINATION_NUMBER', destination_number)
                routing_status = 'found'
    agi.set('CALLFLOW_ROUTING_STATUS', routing_status)
    record(routing_status, call_interaction_id, destination=destination_type + ':' + destination_number)


def notify_crm_of_queue_member_answer(agi):
    # Snapshot member data before chaining an existing Queue AGI.
    call_channel_variables = {name: agi.get(name) for name in (
        'CALLFLOW_CALL_INTERACTION_ID', 'CALLFLOW_CRM_AFFILIATE_ID', 'CALLFLOW_PBX_INSTANCE_ID', 'CALLFLOW_ASTERISK_CHANNEL_UNIQUEID',
        'CALLFLOW_ASTERISK_LINKEDID', 'CALLFLOW_QUEUE_NAME', 'CALLFLOW_QUEUE_MEMBER_CRM_MAP_HASH', 'MEMBERINTERFACE', 'MEMBERNAME', 'CALLFLOW_QUEUE_PREVIOUS_ANSWER_AGI')}
    previous_queue_answer_agi = call_channel_variables['CALLFLOW_QUEUE_PREVIOUS_ANSWER_AGI']
    if previous_queue_answer_agi and 'issabel-crm-answer.agi' not in previous_queue_answer_agi:
        agi.execute('AGI', previous_queue_answer_agi)
    if not call_channel_variables['CALLFLOW_CRM_AFFILIATE_ID'] or not call_channel_variables['CALLFLOW_CALL_INTERACTION_ID']:
        record('notification_no_affiliate', call_channel_variables['CALLFLOW_CALL_INTERACTION_ID'])
        return
    try:
        config = read_config()
    except ConfigError:
        record('notification_config_error', call_channel_variables['CALLFLOW_CALL_INTERACTION_ID'])
        return
    if call_channel_variables['CALLFLOW_QUEUE_MEMBER_CRM_MAP_HASH'] != config['queue_member_crm_map_hash']:
        record('notification_mapping_changed', call_channel_variables['CALLFLOW_CALL_INTERACTION_ID'])
        return
    queue_member_interface = call_channel_variables['MEMBERINTERFACE']
    crm_operator_mapping = config['agents'].get(queue_member_interface)
    if not crm_operator_mapping:
        record('notification_unmapped_member', call_channel_variables['CALLFLOW_CALL_INTERACTION_ID'])
        return
    payload = {
        'schema_version': 1, 'event_type': 'queue_member_answered',
        'interaction_id': call_channel_variables['CALLFLOW_CALL_INTERACTION_ID'], 'event_id': str(uuid.uuid4()),
        'affiliate_id': call_channel_variables['CALLFLOW_CRM_AFFILIATE_ID'], 'pbx_id': call_channel_variables['CALLFLOW_PBX_INSTANCE_ID'],
        'uniqueid': call_channel_variables['CALLFLOW_ASTERISK_CHANNEL_UNIQUEID'], 'linkedid': call_channel_variables['CALLFLOW_ASTERISK_LINKEDID'],
        'member_interface': queue_member_interface, 'member_name': call_channel_variables['MEMBERNAME'][:200],
        'queue': call_channel_variables['CALLFLOW_QUEUE_NAME'],
        'answered_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    payload.update(crm_operator_mapping)
    record('notification_' + launch(config, payload), call_channel_variables['CALLFLOW_CALL_INTERACTION_ID'])
