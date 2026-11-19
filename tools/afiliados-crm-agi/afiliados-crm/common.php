<?php
// PHP 5.4-compatible transport and AGI protocol. No call-control applications.
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
    foreach (array('cuil_variable', 'spool_dir') as $name) {
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
    $variable = isset($runtime['cuil_variable']) ? $runtime['cuil_variable'] : 'dtmfinput';
    if (!preg_match('/^[A-Za-z_][A-Za-z0-9_]{0,63}$/D', $variable)) { return false; }
    $ca = isset($connection['ca_file']) ? $connection['ca_file'] : '';
    if ($ca !== '' && (!is_file($ca) || !is_readable($ca))) { return false; }
    return array('base_url' => $base, 'api_key' => $key, 'ca_file' => $ca,
        'cuil_variable' => $variable,
        'spool_dir' => isset($runtime['spool_dir']) ? $runtime['spool_dir'] : '/var/spool/asterisk/afiliados-crm');
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
    if ($line !== false && preg_match('/^200 result=(-?[0-9]+)(?: \((.*)\))?\s*$/D', $line, $match)) {
        return array($match[1], isset($match[2]) ? $match[2] : '');
    }
    return array('-1', '');
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

function crm_preatendedor_data($body) {
    $object = json_decode($body);
    if (!is_object($object)) { return false; }
    $data = get_object_vars($object);
    foreach (array('cuilValido', 'esTitular', 'activo', 'esProveedor') as $field) {
        if (!array_key_exists($field, $data) || !is_bool($data[$field])) { return false; }
    }
    foreach (array('prestadora', 'provincia') as $field) {
        if (!array_key_exists($field, $data) ||
            ($data[$field] !== null && (!is_string($data[$field]) || strlen($data[$field]) > 512 ||
                preg_match('/[\x00-\x1f\x7f]/', $data[$field])))) { return false; }
    }
    if (!isset($data['referencias']) || !is_array($data['referencias'])) { return false; }
    $index = 0;
    foreach ($data['referencias'] as $key => $reference) {
        if ($key !== $index++ || !is_string($reference)) { return false; }
    }
    return $data;
}

function crm_decision($option, $data) {
    if (!$data['cuilValido']) { return 'INVALID_CUIL'; }
    if ($option === '1') {
        if ($data['esProveedor'] || ($data['esTitular'] && $data['activo'])) { return 'END_CALL'; }
        return 'CALL_CENTER';
    }
    if (!$data['esTitular'] || !$data['activo']) { return 'END_CALL'; }
    return count($data['referencias']) > 0 ? 'PORTAL' : 'CALL_CENTER';
}

function crm_member_extension($interface) {
    if (preg_match('/^Local\/([0-9]{1,10})@from-queue(?:\/n)?$/D', $interface, $match) ||
        preg_match('/^(?:SIP|PJSIP)\/([0-9]{1,10})$/D', $interface, $match)) {
        return $match[1];
    }
    return '';
}

function crm_private_spool($directory, $create) {
    if (!is_string($directory) || $directory === '' || $directory[0] !== '/' || is_link($directory)) {
        return false;
    }
    if (!is_dir($directory) && $create) {
        $mask = umask(0077);
        $made = @mkdir($directory, 0700, true);
        umask($mask);
        if (!$made) { return false; }
    }
    clearstatcache(true, $directory);
    if (!is_dir($directory) || (fileperms($directory) & 0077) !== 0) { return false; }
    return realpath($directory);
}

function crm_job_write($spool, $callId, $extension) {
    $directory = crm_private_spool($spool, true);
    if ($directory === false || !is_writable($directory)) { return false; }
    $data = json_encode(array('llamada' => $callId, 'interno' => $extension));
    $temporary = @tempnam($directory, 'atencion-');
    if ($temporary === false) { return false; }
    if (dirname($temporary) !== $directory) { @unlink($temporary); return false; }
    @chmod($temporary, 0600);
    $final = $temporary . '.job';
    if (@file_put_contents($temporary, $data, LOCK_EX) !== strlen($data) || !@rename($temporary, $final)) {
        @unlink($temporary);
        return false;
    }
    return $final;
}

function crm_dispatch_worker($job) {
    $worker = dirname(__FILE__) . '/crm_worker.php';
    if (!function_exists('exec') || !is_readable($worker) || !is_executable(PHP_BINARY)) { return false; }
    // Only an opaque local filename is passed; no key, CUIL or request body in argv.
    $command = escapeshellarg(PHP_BINARY) . ' ' . escapeshellarg($worker) . ' ' .
        escapeshellarg($job) . ' </dev/null >/dev/null 2>&1 &';
    @exec($command, $output, $status);
    return $status === 0;
}

function crm_take_job($path, $spool) {
    $directory = crm_private_spool($spool, false);
    if ($directory === false || dirname($path) !== $directory || is_link($path) ||
        !preg_match('/^atencion-[A-Za-z0-9]+\.job$/D', basename($path)) || !is_file($path) ||
        (fileperms($path) & 0077) !== 0 || fileowner($path) !== fileowner($directory)) { return false; }
    $handle = @fopen($path, 'rb');
    if ($handle === false) { return false; }
    if (!flock($handle, LOCK_EX | LOCK_NB)) { fclose($handle); return false; }
    clearstatcache(true, $path);
    if (!is_file($path)) { fclose($handle); return false; }
    $raw = stream_get_contents($handle, 1025);
    // Claim the one-use job before HTTP; failures do not create retries or stale notices.
    $claimed = @unlink($path);
    fclose($handle);
    if (!$claimed || $raw === false || strlen($raw) > 1024) { return false; }
    $data = json_decode($raw, true);
    if (!is_array($data) || count($data) !== 2 || !isset($data['llamada'], $data['interno']) ||
        !crm_valid_call_id($data['llamada']) || !is_string($data['interno']) ||
        !preg_match('/^[0-9]{1,10}$/D', $data['interno'])) { return false; }
    return $data;
}
