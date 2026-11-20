#!/usr/bin/php -q
<?php
// PHP 5.4+; standalone lookup. Dynamic Routes owns all call-control actions.
if (PHP_SAPI !== 'cli') { exit(1); }

function crm_config_path() {
    $path = getenv('AFILIADOS_CRM_CONF');
    return $path !== false && $path !== '' ? $path : '/etc/asterisk/afiliados-crm.conf';
}

function crm_load_config() {
    $ini = @parse_ini_file(crm_config_path(), true, INI_SCANNER_RAW);
    if (!is_array($ini) || !isset($ini['atenciones']) || !is_array($ini['atenciones'])) { return false; }
    $connection = $ini['atenciones'];
    $runtime = isset($ini['runtime']) && is_array($ini['runtime']) ? $ini['runtime'] : array();
    foreach (array('base_url', 'api_key', 'ca_file', 'allow_http_loopback') as $name) {
        if (isset($connection[$name]) && !is_string($connection[$name])) { return false; }
    }
    foreach (array('spool_dir') as $name) {
        if (isset($runtime[$name]) && !is_string($runtime[$name])) { return false; }
    }
    $base = isset($connection['base_url']) ? rtrim(trim($connection['base_url']), '/') : '';
    $key = isset($connection['api_key']) ? $connection['api_key'] : '';
    $url = @parse_url($base);
    if (!is_array($url) || !isset($url['scheme'], $url['host']) || isset($url['user']) ||
        isset($url['pass']) || isset($url['query']) || isset($url['fragment']) ||
        $key === '' || strlen($key) > 512 || preg_match('/[\x00-\x1f\x7f]/', $key)) { return false; }
    $loopback = in_array(strtolower($url['host']), array('127.0.0.1', 'localhost', '[::1]', '::1'), true);
    $allowHttp = isset($connection['allow_http_loopback']) && $connection['allow_http_loopback'] === '1';
    if ($url['scheme'] !== 'https' && !($url['scheme'] === 'http' && $loopback && $allowHttp)) { return false; }
    $ca = isset($connection['ca_file']) ? $connection['ca_file'] : '';
    if ($ca !== '' && (!is_file($ca) || !is_readable($ca))) { return false; }
    return array('base_url' => $base, 'api_key' => $key, 'ca_file' => $ca,
        'spool_dir' => isset($runtime['spool_dir']) ? $runtime['spool_dir'] : '/var/spool/asterisk/afiliados-crm');
}

function crm_identification_config() {
    $ini = @parse_ini_file(crm_config_path(), true, INI_SCANNER_RAW);
    if (!is_array($ini) || (isset($ini['identification']) && !is_array($ini['identification']))) { return false; }
    $input = isset($ini['identification']) ? $ini['identification'] : array();
    $config = array('max_attempts' => '3', 'input_timeout' => '5', 'confirmation_timeout' => '5',
        'request_audio' => 'custom/atenciones/ingrese-cuil',
        'entered_audio' => 'custom/atenciones/usted-ingreso',
        'confirm_audio' => 'custom/atenciones/confirme-cuil',
        'digit_audio_prefix' => 'custom/atenciones/digito-');
    foreach ($config as $name => $default) {
        $value = isset($input[$name]) ? $input[$name] : $default;
        if (!is_string($value)) { return false; }
        if (in_array($name, array('max_attempts', 'input_timeout', 'confirmation_timeout'), true)) {
            if (!preg_match('/^[1-9][0-9]{0,2}$/D', $value)) { return false; }
            $config[$name] = (int) $value;
        } else {
            // Relative sound names only; no extension, traversal or AGI syntax.
            if (!preg_match('~^[A-Za-z0-9_-]+(?:/[A-Za-z0-9_-]+)*$~D', $value)) { return false; }
            $config[$name] = $value;
        }
    }
    return $config;
}

function crm_log($category) {
    // Only fixed categories; never log URLs, exception messages or remote data.
    fwrite(STDERR, 'atenciones: ' . $category . "\n");
}

function crm_agi_read_env() {
    $env = array();
    for ($i = 0; $i < 200; $i++) {
        $line = fgets(STDIN, 8192);
        if ($line === false || rtrim($line, "\r\n") === '') { break; }
        $parts = explode(':', rtrim($line, "\r\n"), 2);
        if (count($parts) === 2) { $env[trim($parts[0])] = ltrim($parts[1]); }
    }
    return $env;
}

function crm_agi_cmd($command) {
    fwrite(STDOUT, $command . "\n");
    fflush(STDOUT);
    $line = fgets(STDIN, 8192);
    if ($line !== false && preg_match('/^200 result=(-?[0-9]+)(?: \((.*)\))?(?: endpos=-?[0-9]+)?\s*$/D', $line, $match)) {
        return array($match[1], isset($match[2]) ? $match[2] : '');
    }
    return array('-1', '');
}

function crm_input_digit($command) {
    $reply = crm_agi_cmd($command);
    $code = (int) $reply[0];
    if ($code < 0) { throw new Exception('audio_or_channel_failed'); }
    if ($code === 0) { return ''; }
    if ($code < 0 || $code > 127 || strpos('0123456789*#', chr($code)) === false) {
        throw new Exception('unexpected_dtmf_response');
    }
    return chr($code);
}

function crm_confirmed_cuil($config) {
    for ($attempt = 0; $attempt < $config['max_attempts']; $attempt++) {
        $digit = crm_input_digit('GET OPTION "' . $config['request_audio'] . '" "0123456789*#" ' . ($config['input_timeout'] * 1000));
        $cuil = '';
        while ($digit !== '' && $digit !== '#' && strlen($cuil) < 11) {
            if ($digit === '*') { $cuil = ''; break; }
            $cuil .= $digit;
            if (strlen($cuil) === 11) { break; }
            $digit = crm_input_digit('WAIT FOR DIGIT ' . ($config['input_timeout'] * 1000));
        }
        // A timeout midway is incomplete input. '#' may submit a short value:
        // its semantic validity still belongs to Atenciones.
        if ($cuil === '' || $digit === '') { continue; }
        $reply = crm_agi_cmd('STREAM FILE "' . $config['entered_audio'] . '" ""');
        if ($reply[0] !== '0') { throw new Exception('audio_or_channel_failed'); }
        foreach (str_split($cuil) as $number) {
            $reply = crm_agi_cmd('STREAM FILE "' . $config['digit_audio_prefix'] . $number . '" ""');
            if ($reply[0] !== '0') { throw new Exception('audio_or_channel_failed'); }
        }
        $confirmed = crm_input_digit('GET OPTION "' . $config['confirm_audio'] . '" "0123456789*#" ' . ($config['confirmation_timeout'] * 1000));
        if ($confirmed === '1') { return $cuil; }
    }
    return false;
}

function crm_agi_get($name) {
    $reply = crm_agi_cmd('GET VARIABLE ' . $name);
    return $reply[0] === '1' ? $reply[1] : '';
}

function crm_agi_set($name, $value) {
    $value = str_replace(array("\r", "\n", "\0"), '', (string) $value);
    $value = str_replace(array('\\', '"'), array('\\\\', '\\"'), $value);
    crm_agi_cmd('SET VARIABLE ' . $name . ' "' . $value . '"');
}

function crm_valid_call_id($id) {
    return is_string($id) && strlen($id) > 0 && strlen($id) <= 40 && !preg_match('/[\x00-\x20\x7f]/', $id);
}

function crm_call_id($env) {
    $saved = crm_agi_get('CRM_CALL_ID');
    if ($saved !== '') { return crm_valid_call_id($saved) ? $saved : ''; }
    $original = isset($env['agi_uniqueid']) ? $env['agi_uniqueid'] : '';
    if (!crm_valid_call_id($original)) { return ''; }
    crm_agi_set('__CRM_CALL_ID', $original);
    return $original;
}

function crm_prepare_qagi() {
    $script = 'crm_set_atencion.agi.php';
    $current = crm_agi_get('QAGI');
    $virtual = crm_agi_get('VQ_AGI');
    if (($current !== '' && $current !== $script) || ($virtual !== '' && $virtual !== $script)) {
        crm_agi_set('CRM_QAGI_CONFLICT', '1');
        crm_log('foreign_queue_hook_preserved');
        return;
    }
    crm_agi_set('CRM_QAGI_CONFLICT', '');
    crm_agi_set('__QAGI', $script);
}

function crm_http($config, $method, $path, $parameters) {
    if (!function_exists('curl_init')) { return array('ok' => false, 'status' => 0, 'body' => ''); }
    $url = $config['base_url'] . $path;
    $encoded = http_build_query($parameters, '', '&', PHP_QUERY_RFC3986);
    if ($method === 'GET') { $url .= '?' . $encoded; }
    $headers = array('X-Api-Key: ' . $config['api_key'], 'Accept: application/json', 'Expect:');
    $body = '';
    $tooLarge = false;
    $curl = curl_init($url);
    curl_setopt($curl, CURLOPT_CONNECTTIMEOUT, 1);
    curl_setopt($curl, CURLOPT_TIMEOUT, 3);
    curl_setopt($curl, CURLOPT_NOSIGNAL, true);
    curl_setopt($curl, CURLOPT_FOLLOWLOCATION, false);
    curl_setopt($curl, CURLOPT_SSL_VERIFYPEER, true);
    curl_setopt($curl, CURLOPT_SSL_VERIFYHOST, 2);
    if ($config['ca_file'] !== '') { curl_setopt($curl, CURLOPT_CAINFO, $config['ca_file']); }
    if (defined('CURLOPT_PROTOCOLS_STR')) {
        curl_setopt($curl, CURLOPT_PROTOCOLS_STR, 'http,https');
    } else {
        curl_setopt($curl, CURLOPT_PROTOCOLS, CURLPROTO_HTTP | CURLPROTO_HTTPS);
    }
    curl_setopt($curl, CURLOPT_WRITEFUNCTION, function ($handle, $chunk) use (&$body, &$tooLarge) {
        if (strlen($body) + strlen($chunk) > 16384) { $tooLarge = true; return 0; }
        $body .= $chunk;
        return strlen($chunk);
    });
    if ($method === 'POST') {
        $headers[] = 'Content-Type: application/x-www-form-urlencoded';
        curl_setopt($curl, CURLOPT_POST, true);
        curl_setopt($curl, CURLOPT_POSTFIELDS, $encoded);
    }
    curl_setopt($curl, CURLOPT_HTTPHEADER, $headers);
    $completed = curl_exec($curl);
    $status = (int) curl_getinfo($curl, CURLINFO_HTTP_CODE);
    curl_close($curl);
    return array('ok' => $completed !== false && !$tooLarge, 'status' => $status,
                 'body' => $tooLarge ? '' : $body);
}

function crm_route_key($body) {
    $data = json_decode($body);
    if (!is_object($data) || !isset($data->destino) || !is_string($data->destino) ||
        trim($data->destino) === '' || strlen($data->destino) > 512 ||
        preg_match('/[\x00-\x1f\x7f]/', $data->destino)) { return false; }
    // No fixed list: new server decisions only require a new Dynamic Routes match.
    return $data->destino;
}

function main_lookup() {
    $env = crm_agi_read_env();
    crm_agi_set('CRM_ROUTE_KEY', 'ERROR');
    foreach (array('CRM_CUIL', 'CRM_AFILIADO_ID', 'CRM_OBRA', 'CRM_PRESTADORA') as $legacy) { crm_agi_set($legacy, ''); }
    $option = isset($env['agi_arg_1']) ? $env['agi_arg_1'] : '';
    if ($option === '') { $option = crm_agi_get('IVR_DIGIT_PRESSED'); }
    if (!preg_match('/^[0-9]$/D', $option)) { crm_log('invalid_menu_option'); return; }
    $callId = crm_call_id($env);
    if ($callId === '') { crm_log('invalid_original_call_id'); return; }
    // Contingency calls retain their notification hook, even without a successful GET.
    crm_prepare_qagi();
    $config = crm_load_config();
    $identification = crm_identification_config();
    if ($config === false || $identification === false) { crm_log('configuration_unavailable'); return; }
    $cuil = crm_confirmed_cuil($identification);
    if ($cuil === false) { crm_agi_set('CRM_ROUTE_KEY', 'INPUT_FAILED'); return; }
    $response = crm_http($config, 'GET', '/api/central/preatendedor',
        array('opcion' => $option, 'cuil' => $cuil, 'llamada' => $callId));
    unset($cuil);
    if (!$response['ok'] || $response['status'] !== 200) { crm_log('lookup_http_failed'); return; }
    $destination = crm_route_key($response['body']);
    unset($response);
    if ($destination === false) { crm_log('lookup_invalid_response'); return; }
    crm_agi_set('CRM_ROUTE_KEY', $destination);
}

try { main_lookup(); } catch (Exception $error) { crm_log('lookup_failed'); }
exit(0);
