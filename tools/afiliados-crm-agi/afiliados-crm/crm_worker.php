<?php
// Single-use delivery. Only llamada/interno in the job; no retry or Asterisk access.
if (PHP_SAPI !== 'cli') { exit(1); }
require_once dirname(__FILE__) . '/common.php';

function main_worker($argv) {
    if (!isset($argv[1]) || !is_string($argv[1])) { return; }
    $config = crm_load_config();
    if ($config === false) { crm_log('configuration_unavailable'); return; }
    $payload = crm_take_job($argv[1], $config['spool_dir']);
    if ($payload === false) { crm_log('notification_invalid_job'); return; }
    $response = crm_http($config, 'POST', '/api/central/llamada-atendida', $payload);
    if (!$response['ok'] || $response['status'] !== 200) { crm_log('notification_http_failed'); }
    // OK, SIN_VALIDACION, SIN_OPERADOR and errors never change the live call.
}

try { main_worker($argv); } catch (Exception $error) { crm_log('notification_worker_failed'); }
exit(0);
