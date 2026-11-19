#!/usr/bin/php -q
<?php
// Resolve values only. Dynamic Routes owns every destination and call-control action.
if (PHP_SAPI !== 'cli') { exit(1); }
require_once dirname(__FILE__) . '/afiliados-crm/common.php';

function main_lookup() {
    $env = crm_agi_read_env();
    crm_agi_set('CRM_ROUTE_KEY', 'CALL_CENTER');
    crm_agi_set('CRM_PRESTADORA', '');
    foreach (array('CRM_CUIL', 'CRM_AFILIADO_ID', 'CRM_OBRA') as $legacy) { crm_agi_set($legacy, ''); }
    $option = isset($env['agi_arg_1']) ? $env['agi_arg_1'] : '';
    if ($option === '') { $option = crm_agi_get('IVR_DIGIT_PRESSED'); }
    if ($option === '3') { crm_agi_set('CRM_ROUTE_KEY', 'OPTION_3'); return; }
    if ($option !== '1' && $option !== '2') { crm_log('invalid_menu_option'); return; }
    $callId = crm_call_id($env);
    if ($callId === '') { crm_log('invalid_original_call_id'); return; }
    // Contingency calls retain their notification hook, even without a successful GET.
    crm_prepare_qagi();
    $config = crm_load_config();
    $variable = $config === false ? 'dtmfinput' : $config['cuil_variable'];
    $input = crm_agi_get($variable);
    crm_agi_set($variable, '');
    if ($config === false) { crm_log('configuration_unavailable'); return; }
    // Validation/checksum and registration of invalid or empty CUIL belong to the API.
    $cuil = str_replace(array(' ', '-', "\t", "\r", "\n"), '', $input);
    $response = crm_http($config, 'GET', '/api/central/preatendedor',
        array('opcion' => $option, 'cuil' => $cuil, 'llamada' => $callId));
    unset($input, $cuil);
    if (!$response['ok'] || $response['status'] !== 200) { crm_log('lookup_http_failed'); return; }
    $data = crm_preatendedor_data($response['body']);
    unset($response);
    if ($data === false) { crm_log('lookup_invalid_response'); return; }
    $decision = crm_decision($option, $data);
    $prestadora = $data['cuilValido'] && $data['prestadora'] !== null ? $data['prestadora'] : '';
    unset($data); // No medical fields enter AGI/channel/job output.
    // One Dynamic Routes value: policies take precedence over provider-specific attention.
    if ($decision === 'CALL_CENTER' && $prestadora !== '') { $decision = $prestadora; }
    crm_agi_set('CRM_PRESTADORA', $prestadora);
    crm_agi_set('CRM_ROUTE_KEY', $decision);
}

try { main_lookup(); } catch (Exception $error) { crm_log('lookup_failed'); }
exit(0);
