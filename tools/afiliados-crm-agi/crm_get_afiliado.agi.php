#!/usr/bin/php -q
<?php
// crm_get_afiliado.agi.php — consulta CUIL y devuelve CRM_ROUTE_KEY desde Dynamic Routes.
// Instalacion: /var/lib/asterisk/agi-bin/crm_get_afiliado.agi.php (root:asterisk 0750).
// Uso PBX: AGI script and parameters = crm_get_afiliado.agi.php,[INPUT]; result variable = CRM_ROUTE_KEY.
// PHP 5.4 compatible. Sin Composer ni clases del addon. Contrato CRM provisional.

if (PHP_SAPI !== 'cli') {
    exit(1);
}

require_once dirname(__FILE__) . '/afiliados-crm/common.php';

function lookup_clear_context() {
    $names = array(
        'CRM_ROUTE_KEY', 'CRM_CUIL', 'CRM_AFILIADO_ID', 'CRM_OBRA',
        'CRM_CALL_ID', 'CRM_QAGI_CONFLICT',
        '__CRM_CUIL', '__CRM_AFILIADO_ID', '__CRM_OBRA', '__CRM_CALL_ID',
    );
    foreach ($names as $name) {
        crm_agi_set($name, '');
    }
}

function lookup_set_context($cuil, $afiliadoId, $obra, $callId) {
    crm_agi_set('CRM_CUIL', $cuil);
    crm_agi_set('CRM_AFILIADO_ID', $afiliadoId);
    crm_agi_set('CRM_OBRA', $obra);
    crm_agi_set('CRM_CALL_ID', $callId);
    crm_agi_set('__CRM_CUIL', $cuil);
    crm_agi_set('__CRM_AFILIADO_ID', $afiliadoId);
    crm_agi_set('__CRM_OBRA', $obra);
    crm_agi_set('__CRM_CALL_ID', $callId);
}

function lookup_finish($routeKey, $cuil, $afiliadoId, $obra, $callId) {
    lookup_set_context($cuil, $afiliadoId, $obra, $callId);
    crm_agi_set('CRM_ROUTE_KEY', $routeKey);
}

function lookup_prepare_qagi($config) {
    $want = trim((string) $config['attendant_script']);
    if ($want === '') {
        return;
    }
    $current = trim(crm_agi_get('QAGI'));
    $vcurrent = trim(crm_agi_get('VQ_AGI'));
    $conflict = false;
    if ($current !== '' && $current !== $want && strpos($current, $want) === false) {
        $conflict = true;
    }
    if ($vcurrent !== '' && $vcurrent !== $want && strpos($vcurrent, $want) === false) {
        $conflict = true;
    }
    if ($conflict) {
        // No sobreescribir hooks ajenos QAGI/VQ_AGI.
        crm_agi_set('CRM_QAGI_CONFLICT', '1');
        crm_agi_log('QAGI conflict: foreign hook preserved');
        return;
    }
    crm_agi_set('CRM_QAGI_CONFLICT', '');
    if ($current === '' || $current === $want) {
        crm_agi_set('QAGI', $want);
    }
}

function main_lookup() {
    $env = crm_agi_read_env();
    $rawArg = isset($env['agi_arg_1']) ? (string) $env['agi_arg_1'] : '';
    if ($rawArg === '') {
        // Respaldo: variable de Dynamic Routes si [INPUT] llego vacio.
        $rawArg = crm_agi_get('DYNROUTE_afiliado_cuil');
    }
    $uniqueId = isset($env['agi_uniqueid']) ? trim((string) $env['agi_uniqueid']) : '';
    if ($uniqueId === '') {
        $uniqueId = trim(crm_agi_get('UNIQUEID'));
    }
    if (strlen($uniqueId) > 64) {
        $uniqueId = substr($uniqueId, 0, 64);
    }

    lookup_clear_context();

    $cuilForLog = '';
    if (!crm_validate_cuil($rawArg)) {
        $clean = crm_clean_cuil($rawArg);
        lookup_finish('CRM_INVALID_INPUT', $clean, '', '', $uniqueId);
        crm_agi_log('invalid CUIL input');
        return 0;
    }
    $cuil = substr(rtrim(trim($rawArg), "#* \t"), 0, 32);
    // Normalizar a 11 digitos exactos.
    $cuil = trim($cuil);
    $cuilForLog = $cuil;

    $loaded = crm_load_config(crm_config_path());
    if (!$loaded['ok']) {
        lookup_finish('CRM_ERROR', $cuil, '', '', $uniqueId);
        crm_agi_log('config error');
        return 0;
    }
    $config = $loaded['config'];

    $url = crm_build_lookup_url($config, $cuil);
    $http = crm_http_get($url, $config);
    if (!$http['ok']) {
        if ($http['error'] === 'curl_28') {
            crm_agi_log('lookup timeout');
        } else {
            crm_agi_log('lookup transport error');
        }
        lookup_finish('CRM_ERROR', $cuil, '', '', $uniqueId);
        return 0;
    }
    if ($http['status'] === 404) {
        lookup_finish('CRM_NOT_FOUND', $cuil, '', '', $uniqueId);
        return 0;
    }
    if ($http['status'] < 200 || $http['status'] >= 300) {
        lookup_finish('CRM_ERROR', $cuil, '', '', $uniqueId);
        crm_agi_log('lookup http status');
        return 0;
    }
    $data = json_decode($http['body'], true);
    if (!is_array($data)) {
        lookup_finish('CRM_ERROR', $cuil, '', '', $uniqueId);
        crm_agi_log('lookup json error');
        return 0;
    }
    $idField = $config['lookup_id_field'];
    $obraField = $config['lookup_obra_field'];
    $afiliadoId = '';
    $obraRaw = '';
    if (isset($data[$idField]) && (is_string($data[$idField]) || is_numeric($data[$idField]))) {
        $afiliadoId = substr(trim((string) $data[$idField]), 0, 64);
    }
    if (isset($data[$obraField]) && (is_string($data[$obraField]) || is_numeric($data[$obraField]))) {
        $obraRaw = (string) $data[$obraField];
    }
    if (isset($data['error']) && is_string($data['error']) && strtolower(trim($data['error'])) === 'not_found') {
        lookup_finish('CRM_NOT_FOUND', $cuil, '', '', $uniqueId);
        return 0;
    }
    if ($afiliadoId === '' || $obraRaw === '') {
        lookup_finish('CRM_NOT_FOUND', $cuil, '', '', $uniqueId);
        return 0;
    }
    $routeKey = crm_normalize_obra($obraRaw);
    if (!crm_validate_route_key($routeKey)) {
        lookup_finish('CRM_ERROR', $cuil, '', '', $uniqueId);
        crm_agi_log('lookup obra normalize error');
        return 0;
    }
    lookup_finish($routeKey, $cuil, $afiliadoId, $routeKey, $uniqueId);
    lookup_prepare_qagi($config);
    unset($cuilForLog);
    return 0;
}

try {
    $code = main_lookup();
    exit((int) $code);
} catch (Exception $e) {
    // Clave de contingencia, sin stacktrace/PII ni llamada colgada.
    try {
        lookup_clear_context();
        crm_agi_set('CRM_ROUTE_KEY', 'CRM_ERROR');
    } catch (Exception $ignored) {
    }
    exit(0);
}
