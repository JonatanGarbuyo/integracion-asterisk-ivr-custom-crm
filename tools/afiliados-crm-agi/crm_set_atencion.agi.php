#!/usr/bin/php -q
<?php
// Queue's answer hook: capture data, dispatch a one-use worker, return to Queue.
if (PHP_SAPI !== 'cli') { exit(1); }
require_once dirname(__FILE__) . '/afiliados-crm/common.php';

function main_attendant() {
    crm_agi_read_env();
    // Never substitute this hook's channel UNIQUEID for the original caller ID.
    $callId = crm_agi_get('CRM_CALL_ID');
    $extension = crm_member_extension(crm_agi_get('MEMBERINTERFACE'));
    if (!crm_valid_call_id($callId) || $extension === '') {
        crm_log('notification_missing_identity');
        return;
    }
    $config = crm_load_config();
    if ($config === false) { crm_log('configuration_unavailable'); return; }
    $job = crm_job_write($config['spool_dir'], $callId, $extension);
    if ($job === false) { crm_log('notification_spool_failed'); return; }
    if (!crm_dispatch_worker($job)) {
        @unlink($job);
        crm_log('notification_dispatch_failed');
    }
}

try { main_attendant(); } catch (Exception $error) { crm_log('notification_failed'); }
exit(0);
