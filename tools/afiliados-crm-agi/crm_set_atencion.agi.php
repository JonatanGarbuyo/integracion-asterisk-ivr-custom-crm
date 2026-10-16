#!/usr/bin/php -q
<?php
// crm_set_atencion.agi.php — hook de Queue (QAGI): captura identidad y despacha worker.
// Instalacion: /var/lib/asterisk/agi-bin/crm_set_atencion.agi.php (root:asterisk 0750).
// Requiere setinterfacevar=yes en queues_post_custom.conf para MEMBERINTERFACE/MEMBERNAME.
// No adivina interno; ante identidad/config incompleta continua la llamada sin aviso falso.
// POST fuera del proceso AGI mediante worker de un solo uso; best effort sin retries.
// PHP 5.4 compatible. Contrato CRM provisional.

if (PHP_SAPI !== 'cli') {
    exit(1);
}

require_once dirname(__FILE__) . '/afiliados-crm/common.php';

function main_attendant() {
    $env = crm_agi_read_env();
    $uniqueId = isset($env['agi_uniqueid']) ? trim((string) $env['agi_uniqueid']) : '';
    $channel = isset($env['agi_channel']) ? trim((string) $env['agi_channel']) : '';
    if (strlen($uniqueId) > 64) {
        $uniqueId = substr($uniqueId, 0, 64);
    }

    $memberInterface = trim(crm_agi_get('MEMBERINTERFACE'));
    $memberName = trim(crm_agi_get('MEMBERNAME'));
    $cuil = substr(trim(crm_agi_get('CRM_CUIL')), 0, 32);
    $afiliadoId = substr(trim(crm_agi_get('CRM_AFILIADO_ID')), 0, 64);
    $obra = substr(trim(crm_agi_get('CRM_OBRA')), 0, 64);
    $callId = trim(crm_agi_get('CRM_CALL_ID'));
    if ($callId === '') {
        $callId = $uniqueId;
    }
    if (strlen($callId) > 64) {
        $callId = substr($callId, 0, 64);
    }

    if ($memberInterface === '') {
        // Oferta sin respuesta o hook sin miembro: continuar llamada.
        crm_agi_log('missing member: continue without dispatch');
        return 0;
    }
    if ($cuil === '' && $afiliadoId === '') {
        crm_agi_log('missing afiliado identity: continue without dispatch');
        return 0;
    }

    $loaded = crm_load_config(crm_config_path());
    if (!$loaded['ok']) {
        crm_agi_log('config error: continue without dispatch');
        return 0;
    }
    $config = $loaded['config'];

    $agentFull = '';
    $agentNum = crm_parse_agent_number($memberInterface);
    if ($agentNum !== '') {
        // AGENT(id:fullchannel) en Asterisk 11 da el canal de login del agente.
        $agentFull = trim(crm_agi_get_full('AGENT(' . $agentNum . ':fullchannel)'));
    }

    $resolved = crm_resolve_member($memberInterface, $config, $agentFull);
    if (!$resolved['ok']) {
        crm_agi_log('unresolved member: continue without dispatch');
        return 0;
    }
    $agentCrm = $resolved['agent_crm'];
    $interno = $resolved['interno'];

    $eventId = $callId . '-' . substr(md5($memberInterface . '|' . $uniqueId . '|' . microtime(true)), 0, 8);
    $eventId = preg_replace('/[^A-Za-z0-9._-]/', '', $eventId);
    if ($eventId === '' || $eventId === null) {
        crm_agi_log('event build error: continue without dispatch');
        return 0;
    }
    $eventId = substr($eventId, 0, 96);

    $job = array(
        'event_id' => $eventId,
        'call_id' => $callId,
        'unique_id' => $uniqueId,
        'channel' => substr($channel, 0, 128),
        'afiliado_id' => $afiliadoId,
        'cuil' => $cuil,
        'obra' => $obra,
        'agente_crm' => $agentCrm,
        'interno' => $interno,
        'memberinterface' => substr($memberInterface, 0, 128),
        'membername' => substr($memberName, 0, 128),
        'answered_at' => gmdate('Y-m-d\TH:i:s\Z'),
    );

    $spoolDir = crm_spool_dir($config);
    $jobPath = crm_job_write($spoolDir, $job);
    if ($jobPath === false) {
        crm_agi_log('spool error: continue without dispatch');
        return 0;
    }
    $worker = crm_worker_path($config);
    crm_dispatch_worker($worker, $jobPath);
    // POST lento/fallido no retiene la conversacion; el worker limpia el job.
    return 0;
}

try {
    $code = main_attendant();
    exit((int) $code);
} catch (Exception $e) {
    // Nunca colgar ni romper la llamada por el aviso.
    try {
        crm_agi_log('attendant error: continue call');
    } catch (Exception $ignored) {
    }
    exit(0);
}
