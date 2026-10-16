<?php
// crm_worker.php — worker de un solo uso para POST setAtencion.
// Lo lanza crm_set_atencion.agi.php en background; no consulta Asterisk.
// Best effort explicito: sin retries/daemon/cron, limpia el job siempre,
// sin prometer entrega durable. No recibe CUIL/token/body en argv.
// PHP 5.4 compatible. Contrato CRM provisional.

if (PHP_SAPI !== 'cli') {
    exit(1);
}

require_once dirname(__FILE__) . '/common.php';

function worker_log($message) {
    // Sin PII: solo event_id y estado, nunca CUIL/token/body.
    $text = (string) $message;
    $text = str_replace(array("\r", "\n"), array(' ', ' '), $text);
    if (strlen($text) > 256) {
        $text = substr($text, 0, 256);
    }
    fwrite(STDERR, 'afiliados-crm-worker: ' . $text . "\n");
}

function main_worker($argv) {
    if (!isset($argv[1]) || !is_string($argv[1]) || $argv[1] === '') {
        worker_log('missing job argument');
        return 0;
    }
    $jobPath = $argv[1];
    if (strlen($jobPath) > 512) {
        worker_log('bad job path');
        return 0;
    }
    if (!is_file($jobPath) || !is_readable($jobPath)) {
        worker_log('unreadable job');
        return 0;
    }
    $raw = @file_get_contents($jobPath);
    if (!is_string($raw) || $raw === '' || strlen($raw) > 8192) {
        worker_log('bad job content');
        @unlink($jobPath);
        return 0;
    }
    $job = json_decode($raw, true);
    if (!is_array($job)) {
        worker_log('bad job json');
        @unlink($jobPath);
        return 0;
    }
    $eventId = isset($job['event_id']) ? preg_replace('/[^A-Za-z0-9._-]/', '', (string) $job['event_id']) : '';
    $callId = isset($job['call_id']) ? substr(trim((string) $job['call_id']), 0, 64) : '';
    $afiliadoId = isset($job['afiliado_id']) ? substr(trim((string) $job['afiliado_id']), 0, 64) : '';
    $cuil = isset($job['cuil']) ? substr(trim((string) $job['cuil']), 0, 32) : '';
    $obra = isset($job['obra']) ? substr(trim((string) $job['obra']), 0, 64) : '';
    $agenteCrm = isset($job['agente_crm']) ? substr(trim((string) $job['agente_crm']), 0, 64) : '';
    $interno = isset($job['interno']) ? substr(trim((string) $job['interno']), 0, 32) : '';
    if ($eventId === '' || $eventId === null || $callId === '' || $agenteCrm === '' || $interno === '') {
        worker_log('incomplete job ' . substr((string) $eventId, 0, 64));
        @unlink($jobPath);
        return 0;
    }
    if ($afiliadoId === '' && $cuil === '') {
        worker_log('missing afiliado ' . substr((string) $eventId, 0, 64));
        @unlink($jobPath);
        return 0;
    }

    $loaded = crm_load_config(crm_config_path());
    if (!$loaded['ok']) {
        worker_log('config error ' . substr((string) $eventId, 0, 64));
        @unlink($jobPath);
        return 0;
    }
    $config = $loaded['config'];
    $url = crm_build_post_url($config);
    $payload = array(
        'event_id' => $eventId,
        'call_id' => $callId,
        'afiliado_id' => $afiliadoId,
        'cuil' => $cuil,
        'obra' => $obra,
        'agente_crm' => $agenteCrm,
        'interno' => $interno,
        'answered_at' => isset($job['answered_at']) ? substr((string) $job['answered_at'], 0, 32) : gmdate('Y-m-d\TH:i:s\Z'),
    );
    $result = crm_http_post_json($url, $payload, $config);
    // Limpieza siempre, exito o fallo: sin outbox durable.
    @unlink($jobPath);
    if ($result['ok']) {
        worker_log('posted ' . substr((string) $eventId, 0, 64));
    } else {
        worker_log('post failed ' . substr((string) $eventId, 0, 64));
    }
    return 0;
}

try {
    exit((int) main_worker($argv));
} catch (Exception $e) {
    try {
        if (isset($argv[1]) && is_string($argv[1])) {
            @unlink($argv[1]);
        }
        worker_log('worker error');
    } catch (Exception $ignored) {
    }
    exit(0);
}
