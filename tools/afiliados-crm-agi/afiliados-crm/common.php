<?php
// Afiliados CRM — auxiliar comun para AGI standalone (Dynamic Routes).
// PHP 5.4 compatible: solo sintaxis array(), sin ??, sin tipos escalares.
// Sin Composer, sin clases del addon, sin Python de runtime.
// Contrato CRM provisional: pedir URL/auth/samples reales antes de afirmar CRM real.

if (PHP_SAPI !== 'cli') {
    exit(1);
}

function crm_default_config() {
    return array(
        'lookup_base_url' => '',
        'lookup_path' => '/afiliado?cuil={CUIL}',
        'lookup_connect_timeout_s' => 1,
        'lookup_total_timeout_s' => 2,
        'lookup_max_bytes' => 8192,
        'lookup_verify_tls' => 1,
        'lookup_max_redirects' => 0,
        'lookup_allow_loopback' => 0,
        'lookup_id_field' => 'id',
        'lookup_obra_field' => 'obra_social',
        'post_path' => '/atencion',
        'post_connect_timeout_s' => 1,
        'post_total_timeout_s' => 2,
        'post_max_bytes' => 8192,
        'post_verify_tls' => 1,
        'post_max_redirects' => 0,
        'post_allow_loopback' => 0,
        'api_token' => '',
        'spool_dir' => '/var/spool/asterisk/afiliados-crm',
        'worker_php' => '/var/lib/asterisk/agi-bin/afiliados-crm/crm_worker.php',
        'attendant_script' => 'crm_set_atencion.agi.php',
        'agents' => array(),
        'extensions' => array(),
    );
}

function crm_config_path() {
    $override = getenv('AFILIADOS_CRM_CONF');
    if (is_string($override) && $override !== '') {
        return $override;
    }
    return '/etc/asterisk/afiliados-crm.conf';
}

function crm_spool_dir($config) {
    $override = getenv('AFILIADOS_CRM_SPOOL');
    if (is_string($override) && $override !== '') {
        return $override;
    }
    return $config['spool_dir'];
}

function crm_worker_path($config) {
    $override = getenv('AFILIADOS_CRM_WORKER');
    if (is_string($override) && $override !== '') {
        return $override;
    }
    return $config['worker_php'];
}

function crm_to_int($value, $fallback) {
    if (is_int($value)) {
        return $value;
    }
    if (is_string($value) && preg_match('/^[0-9]+$/', trim($value))) {
        return (int) trim($value);
    }
    if (is_numeric($value)) {
        return (int) $value;
    }
    return $fallback;
}

function crm_to_bool_int($value, $fallback) {
    if (is_int($value)) {
        return $value ? 1 : 0;
    }
    if (is_string($value)) {
        $v = strtolower(trim($value));
        if ($v === '1' || $v === 'true' || $v === 'yes' || $v === 'on') {
            return 1;
        }
        if ($v === '0' || $v === 'false' || $v === 'no' || $v === 'off' || $v === '') {
            return 0;
        }
    }
    if (is_bool($value)) {
        return $value ? 1 : 0;
    }
    return $fallback;
}

function crm_load_config($path) {
    $defaults = crm_default_config();
    if (!is_string($path) || $path === '') {
        $path = crm_config_path();
    }
    if (!is_file($path) || !is_readable($path)) {
        return array('ok' => false, 'config' => $defaults, 'error' => 'config_unreadable');
    }
    $parsed = @parse_ini_file($path, true);
    if (!is_array($parsed)) {
        return array('ok' => false, 'config' => $defaults, 'error' => 'config_invalid');
    }
    $config = $defaults;
    if (isset($parsed['lookup']) && is_array($parsed['lookup'])) {
        $lookup = $parsed['lookup'];
        if (isset($lookup['base_url'])) {
            $config['lookup_base_url'] = trim((string) $lookup['base_url']);
        }
        if (isset($lookup['lookup_path'])) {
            $config['lookup_path'] = trim((string) $lookup['lookup_path']);
        }
        if (isset($lookup['connect_timeout_s'])) {
            $config['lookup_connect_timeout_s'] = crm_to_int($lookup['connect_timeout_s'], 1);
        }
        if (isset($lookup['total_timeout_s'])) {
            $config['lookup_total_timeout_s'] = crm_to_int($lookup['total_timeout_s'], 2);
        }
        if (isset($lookup['max_bytes'])) {
            $config['lookup_max_bytes'] = crm_to_int($lookup['max_bytes'], 8192);
        }
        if (isset($lookup['verify_tls'])) {
            $config['lookup_verify_tls'] = crm_to_bool_int($lookup['verify_tls'], 1);
        }
        if (isset($lookup['max_redirects'])) {
            $config['lookup_max_redirects'] = crm_to_int($lookup['max_redirects'], 0);
        }
        if (isset($lookup['allow_loopback'])) {
            $config['lookup_allow_loopback'] = crm_to_bool_int($lookup['allow_loopback'], 0);
        }
        if (isset($lookup['id_field'])) {
            $config['lookup_id_field'] = trim((string) $lookup['id_field']);
        }
        if (isset($lookup['obra_field'])) {
            $config['lookup_obra_field'] = trim((string) $lookup['obra_field']);
        }
    }
    if (isset($parsed['atencion']) && is_array($parsed['atencion'])) {
        $at = $parsed['atencion'];
        if (isset($at['post_path'])) {
            $config['post_path'] = trim((string) $at['post_path']);
        }
        if (isset($at['base_url'])) {
            $config['lookup_base_url'] = trim((string) $at['base_url']);
        }
        if (isset($at['connect_timeout_s'])) {
            $config['post_connect_timeout_s'] = crm_to_int($at['connect_timeout_s'], 1);
        }
        if (isset($at['total_timeout_s'])) {
            $config['post_total_timeout_s'] = crm_to_int($at['total_timeout_s'], 2);
        }
        if (isset($at['max_bytes'])) {
            $config['post_max_bytes'] = crm_to_int($at['max_bytes'], 8192);
        }
        if (isset($at['verify_tls'])) {
            $config['post_verify_tls'] = crm_to_bool_int($at['verify_tls'], 1);
        }
        if (isset($at['max_redirects'])) {
            $config['post_max_redirects'] = crm_to_int($at['max_redirects'], 0);
        }
        if (isset($at['allow_loopback'])) {
            $config['post_allow_loopback'] = crm_to_bool_int($at['allow_loopback'], 0);
        }
        if (isset($at['api_token'])) {
            $config['api_token'] = (string) $at['api_token'];
        }
        if (isset($at['spool_dir'])) {
            $config['spool_dir'] = trim((string) $at['spool_dir']);
        }
        if (isset($at['worker_php'])) {
            $config['worker_php'] = trim((string) $at['worker_php']);
        }
        if (isset($at['attendant_script'])) {
            $config['attendant_script'] = trim((string) $at['attendant_script']);
        }
    }
    if (isset($parsed['agents']) && is_array($parsed['agents'])) {
        foreach ($parsed['agents'] as $k => $v) {
            $key = trim((string) $k);
            $val = trim((string) $v);
            if ($key !== '' && $val !== '' && strlen($key) < 128 && strlen($val) < 128) {
                $config['agents'][$key] = $val;
            }
        }
    }
    if (isset($parsed['extensions']) && is_array($parsed['extensions'])) {
        foreach ($parsed['extensions'] as $k => $v) {
            $key = trim((string) $k);
            $val = trim((string) $v);
            if ($key !== '' && $val !== '' && strlen($key) < 128 && strlen($val) < 128) {
                $config['extensions'][$key] = $val;
            }
        }
    }
    if ($config['lookup_base_url'] === '') {
        return array('ok' => false, 'config' => $config, 'error' => 'config_missing_base_url');
    }
    $scheme = strtolower((string) parse_url($config['lookup_base_url'], PHP_URL_SCHEME));
    if ($scheme !== 'http' && $scheme !== 'https') {
        return array('ok' => false, 'config' => $config, 'error' => 'config_bad_scheme');
    }
    if ($config['lookup_id_field'] === '' || $config['lookup_obra_field'] === '') {
        return array('ok' => false, 'config' => $config, 'error' => 'config_bad_fields');
    }
    if ($config['lookup_connect_timeout_s'] < 1) {
        $config['lookup_connect_timeout_s'] = 1;
    }
    if ($config['lookup_total_timeout_s'] < 1) {
        $config['lookup_total_timeout_s'] = 2;
    }
    if ($config['lookup_max_bytes'] < 512 || $config['lookup_max_bytes'] > 65536) {
        $config['lookup_max_bytes'] = 8192;
    }
    if ($config['post_max_bytes'] < 512 || $config['post_max_bytes'] > 65536) {
        $config['post_max_bytes'] = 8192;
    }
    if ($config['attendant_script'] === '') {
        return array('ok' => false, 'config' => $config, 'error' => 'config_bad_attendant');
    }
    return array('ok' => true, 'config' => $config, 'error' => '');
}

function crm_validate_cuil($value) {
    if (!is_string($value)) {
        return false;
    }
    $v = trim($value);
    if ($v === '') {
        return false;
    }
    // Dynamic Routes puede entregar el terminador '#'; se acepta y se ignora solo al final.
    $v = rtrim($v, "#* \t");
    $v = trim($v);
    if (!preg_match('/^[0-9]{11}$/', $v)) {
        return false;
    }
    return true;
}

function crm_clean_cuil($value) {
    if (!is_string($value)) {
        return '';
    }
    $v = trim($value);
    $v = rtrim($v, "#* \t");
    $v = trim($v);
    if (!preg_match('/^[0-9]{1,32}$/', $v)) {
        // No propagar PII arbitraria; conservar solo digitos cortos.
        $digits = preg_replace('/[^0-9]/', '', $v);
        if ($digits === null) {
            return '';
        }
        return substr($digits, 0, 32);
    }
    return substr($v, 0, 32);
}

function crm_normalize_obra($value) {
    if (!is_string($value)) {
        return '';
    }
    $v = trim($value);
    if ($v === '') {
        return '';
    }
    if (function_exists('mb_strtoupper')) {
        $v = mb_strtoupper($v, 'UTF-8');
    } else {
        $v = strtoupper($v);
    }
    $v = str_replace(array(' ', '-', '.', '/'), '_', $v);
    $v = preg_replace('/[^A-Z0-9_]/', '', $v);
    if ($v === null) {
        return '';
    }
    $v = preg_replace('/_+/', '_', $v);
    $v = trim($v, '_');
    if (strlen($v) > 64 || strlen($v) < 1) {
        return '';
    }
    return $v;
}

function crm_validate_route_key($value) {
    if (!is_string($value) || $value === '') {
        return false;
    }
    if (strlen($value) > 64) {
        return false;
    }
    return (bool) preg_match('/^[A-Z0-9_]+$/', $value);
}

function crm_is_loopback_host($host) {
    if (!is_string($host)) {
        return false;
    }
    $h = strtolower(trim($host));
    if ($h === 'localhost' || $h === '::1' || $h === '[::1]') {
        return true;
    }
    if (preg_match('/^127\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$/', $h)) {
        return true;
    }
    return false;
}

function crm_is_loopback_url($url) {
    $host = @parse_url($url, PHP_URL_HOST);
    if (!is_string($host)) {
        return false;
    }
    return crm_is_loopback_host($host);
}

function crm_build_lookup_url($config, $cuil) {
    $path = $config['lookup_path'];
    if (strpos($path, '{CUIL}') !== false) {
        $path = str_replace('{CUIL}', rawurlencode($cuil), $path);
    } else {
        $sep = (strpos($path, '?') === false) ? '?' : '&';
        $path = $path . $sep . 'cuil=' . rawurlencode($cuil);
    }
    $base = rtrim($config['lookup_base_url'], '/');
    if ($path === '' || $path[0] !== '/') {
        $path = '/' . $path;
    }
    return $base . $path;
}

function crm_build_post_url($config) {
    $base = rtrim($config['lookup_base_url'], '/');
    $path = $config['post_path'];
    if ($path === '' || $path[0] !== '/') {
        $path = '/' . $path;
    }
    return $base . $path;
}

function crm_curl_common($ch, $url, $connect_s, $total_s, $verify_tls, $max_redirects) {
    curl_setopt($ch, CURLOPT_URL, $url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_HEADER, true);
    curl_setopt($ch, CURLOPT_CONNECTTIMEOUT, (int) $connect_s);
    curl_setopt($ch, CURLOPT_TIMEOUT, (int) $total_s);
    curl_setopt($ch, CURLOPT_NOSIGNAL, true);
    if ($verify_tls) {
        curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, true);
        curl_setopt($ch, CURLOPT_SSL_VERIFYHOST, 2);
    } else {
        curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
        curl_setopt($ch, CURLOPT_SSL_VERIFYHOST, 0);
    }
    if ((int) $max_redirects > 0) {
        curl_setopt($ch, CURLOPT_FOLLOWLOCATION, true);
        curl_setopt($ch, CURLOPT_MAXREDIRS, (int) $max_redirects);
    } else {
        curl_setopt($ch, CURLOPT_FOLLOWLOCATION, false);
    }
    curl_setopt($ch, CURLOPT_PROTOCOLS, CURLPROTO_HTTP | CURLPROTO_HTTPS);
    curl_setopt($ch, CURLOPT_REDIR_PROTOCOLS, CURLPROTO_HTTP | CURLPROTO_HTTPS);
}

function crm_http_get($url, $config) {
    if (!function_exists('curl_init')) {
        return array('ok' => false, 'status' => 0, 'body' => '', 'error' => 'no_curl');
    }
    if (crm_is_loopback_url($url) && empty($config['lookup_allow_loopback'])) {
        return array('ok' => false, 'status' => 0, 'body' => '', 'error' => 'loopback_blocked');
    }
    $ch = curl_init();
    if ($ch === false) {
        return array('ok' => false, 'status' => 0, 'body' => '', 'error' => 'curl_init');
    }
    crm_curl_common($ch, $url, $config['lookup_connect_timeout_s'], $config['lookup_total_timeout_s'], $config['lookup_verify_tls'], $config['lookup_max_redirects']);
    curl_setopt($ch, CURLOPT_HTTPGET, true);
    $raw = curl_exec($ch);
    $errno = curl_errno($ch);
    $status = (int) curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);
    if ($errno !== 0) {
        return array('ok' => false, 'status' => 0, 'body' => '', 'error' => 'curl_' . $errno);
    }
    if (!is_string($raw)) {
        return array('ok' => false, 'status' => $status, 'body' => '', 'error' => 'empty_response');
    }
    // Separar cabeceras y cuerpo sin exponer PII.
    $body = $raw;
    $pos = strrpos($raw, "\r\n\r\n");
    if ($pos !== false) {
        $body = substr($raw, $pos + 4);
    }
    if (strlen($body) > $config['lookup_max_bytes']) {
        return array('ok' => false, 'status' => $status, 'body' => '', 'error' => 'too_large');
    }
    return array('ok' => true, 'status' => $status, 'body' => $body, 'error' => '');
}

function crm_http_post_json($url, $payload, $config) {
    if (!function_exists('curl_init')) {
        return array('ok' => false, 'status' => 0, 'error' => 'no_curl');
    }
    if (crm_is_loopback_url($url) && empty($config['post_allow_loopback'])) {
        return array('ok' => false, 'status' => 0, 'error' => 'loopback_blocked');
    }
    $body = json_encode($payload);
    if (!is_string($body) || $body === '') {
        return array('ok' => false, 'status' => 0, 'error' => 'encode_error');
    }
    $ch = curl_init();
    if ($ch === false) {
        return array('ok' => false, 'status' => 0, 'error' => 'curl_init');
    }
    crm_curl_common($ch, $url, $config['post_connect_timeout_s'], $config['post_total_timeout_s'], $config['post_verify_tls'], $config['post_max_redirects']);
    $headers = array('Content-Type: application/json', 'Expect:');
    $token = isset($config['api_token']) ? (string) $config['api_token'] : '';
    if ($token !== '') {
        $headers[] = 'Authorization: Bearer ' . $token;
    }
    if (isset($payload['call_id'])) {
        $headers[] = 'X-Correlation-Id: ' . preg_replace('/[^A-Za-z0-9._-]/', '', (string) $payload['call_id']);
    }
    if (isset($payload['event_id'])) {
        $headers[] = 'X-Event-Id: ' . preg_replace('/[^A-Za-z0-9._-]/', '', (string) $payload['event_id']);
    }
    curl_setopt($ch, CURLOPT_POST, true);
    curl_setopt($ch, CURLOPT_POSTFIELDS, $body);
    curl_setopt($ch, CURLOPT_HTTPHEADER, $headers);
    $raw = curl_exec($ch);
    $errno = curl_errno($ch);
    $status = (int) curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);
    if ($errno !== 0) {
        return array('ok' => false, 'status' => 0, 'error' => 'curl_' . $errno);
    }
    if (is_string($raw) && strlen($raw) > $config['post_max_bytes'] + 1024) {
        return array('ok' => false, 'status' => $status, 'error' => 'too_large');
    }
    if ($status < 200 || $status >= 300) {
        return array('ok' => false, 'status' => $status, 'error' => 'http_' . $status);
    }
    return array('ok' => true, 'status' => $status, 'error' => '');
}

// --- AGI ---

function crm_agi_read_env() {
    $env = array();
    for ($i = 0; $i < 200; $i++) {
        $line = fgets(STDIN);
        if ($line === false) {
            break;
        }
        $line = rtrim($line, "\r\n");
        if ($line === '') {
            break;
        }
        $pos = strpos($line, ':');
        if ($pos === false) {
            continue;
        }
        $key = strtolower(trim(substr($line, 0, $pos)));
        $value = trim(substr($line, $pos + 1));
        $env[$key] = $value;
    }
    return $env;
}

function crm_agi_cmd($command) {
    fwrite(STDOUT, $command . "\n");
    if (function_exists('fflush')) {
        @fflush(STDOUT);
    }
    $line = fgets(STDIN);
    if ($line === false) {
        return array('code' => '-1', 'extra' => '');
    }
    $line = rtrim($line, "\r\n");
    if (preg_match('/^200 result=(-?\d+)(?: \((.*)\))?$/', $line, $m)) {
        $extra = isset($m[2]) ? $m[2] : '';
        return array('code' => $m[1], 'extra' => $extra);
    }
    return array('code' => '-1', 'extra' => '');
}

function crm_agi_get($name) {
    $res = crm_agi_cmd('GET VARIABLE ' . $name);
    if ($res['code'] === '1') {
        return $res['extra'];
    }
    return '';
}

function crm_agi_get_full($expr) {
    $res = crm_agi_cmd('GET FULL VARIABLE ' . $expr);
    if ($res['code'] === '1') {
        return $res['extra'];
    }
    return '';
}

function crm_agi_set($name, $value) {
    $text = (string) $value;
    $text = str_replace('\\', '\\\\', $text);
    $text = str_replace('"', '\\"', $text);
    $text = str_replace(array("\r", "\n"), array('', ''), $text);
    if (strlen($text) > 4096) {
        $text = substr($text, 0, 4096);
    }
    crm_agi_cmd('SET VARIABLE ' . $name . ' "' . $text . '"');
}

function crm_agi_log($message) {
    $text = (string) $message;
    $text = str_replace(array("\r", "\n"), array(' ', ' '), $text);
    if (strlen($text) > 512) {
        $text = substr($text, 0, 512);
    }
    fwrite(STDERR, 'afiliados-crm: ' . $text . "\n");
}

// --- Miembros de cola ---

function crm_interface_base($iface) {
    if (!is_string($iface)) {
        return '';
    }
    $v = trim($iface);
    if ($v === '') {
        return '';
    }
    // SIP/101-00000001 -> SIP/101 ; Local conserva hasta ';' solo.
    $semi = strpos($v, ';');
    if ($semi !== false) {
        $v = substr($v, 0, $semi);
    }
    if (stripos($v, 'SIP/') === 0 || stripos($v, 'PJSIP/') === 0 || stripos($v, 'IAX2/') === 0) {
        $dash = strrpos($v, '-');
        $slash = strrpos($v, '/');
        if ($dash !== false && $slash !== false && $dash > $slash) {
            $suffix = substr($v, $dash + 1);
            if (preg_match('/^[0-9a-f.]+$/i', $suffix)) {
                $v = substr($v, 0, $dash);
            }
        }
    }
    if (strlen($v) > 128) {
        return '';
    }
    return $v;
}

function crm_parse_agent_number($iface) {
    if (!is_string($iface)) {
        return '';
    }
    $v = trim($iface);
    if (preg_match('/^Agent\/([0-9]{1,16})(?:[\/-].*)?$/i', $v, $m)) {
        return $m[1];
    }
    return '';
}

function crm_extension_from_channel($channel) {
    if (!is_string($channel) || $channel === '') {
        return '';
    }
    $v = trim($channel);
    $semi = strpos($v, ';');
    if ($semi !== false) {
        $v = substr($v, 0, $semi);
    }
    if (preg_match('/^(?:SIP|PJSIP|IAX2)\/([A-Za-z0-9_.-]{1,64})(?:[-@\/].*)?$/i', $v, $m)) {
        $ext = $m[1];
        // El interno real suele ser numerico; aceptar alfanumerico corto verificado por config.
        if (preg_match('/^[A-Za-z0-9_.-]{1,32}$/', $ext)) {
            // Si trae dominio (@...), recortar.
            $at = strpos($ext, '@');
            if ($at !== false) {
                $ext = substr($ext, 0, $at);
            }
            return $ext;
        }
    }
    if (preg_match('/^Local\/([A-Za-z0-9_.-]{1,64})@/i', $v, $m)) {
        return $m[1];
    }
    return '';
}

function crm_lookup_map($map, $iface, $base) {
    if (isset($map[$iface]) && $map[$iface] !== '') {
        return $map[$iface];
    }
    if ($base !== '' && $base !== $iface && isset($map[$base]) && $map[$base] !== '') {
        return $map[$base];
    }
    return '';
}

function crm_resolve_member($memberInterface, $config, $agentFullChannel) {
    $iface = trim((string) $memberInterface);
    if ($iface === '') {
        return array('ok' => false, 'agent_crm' => '', 'interno' => '', 'reason' => 'missing_member');
    }
    $base = crm_interface_base($iface);
    if ($base === '') {
        return array('ok' => false, 'agent_crm' => '', 'interno' => '', 'reason' => 'bad_interface');
    }
    $agentNum = crm_parse_agent_number($iface);
    if ($agentNum !== '') {
        $agentCrm = crm_lookup_map($config['agents'], $iface, $base);
        if ($agentCrm === '') {
            // Probar tambien con la forma canonica Agent/NUM.
            $canon = 'Agent/' . $agentNum;
            if (isset($config['agents'][$canon])) {
                $agentCrm = $config['agents'][$canon];
            }
        }
        if ($agentCrm === '') {
            return array('ok' => false, 'agent_crm' => '', 'interno' => '', 'reason' => 'unknown_agent');
        }
        $full = trim((string) $agentFullChannel);
        if ($full === '') {
            return array('ok' => false, 'agent_crm' => '', 'interno' => '', 'reason' => 'agent_channel_missing');
        }
        $interno = crm_extension_from_channel($full);
        if ($interno === '') {
            return array('ok' => false, 'agent_crm' => '', 'interno' => '', 'reason' => 'agent_channel_unparsed');
        }
        if (!preg_match('/^[A-Za-z0-9_.-]{1,32}$/', $agentCrm)) {
            return array('ok' => false, 'agent_crm' => '', 'interno' => '', 'reason' => 'bad_agent_map');
        }
        return array('ok' => true, 'agent_crm' => $agentCrm, 'interno' => $interno, 'reason' => '');
    }
    $agentCrm = crm_lookup_map($config['agents'], $iface, $base);
    $interno = crm_lookup_map($config['extensions'], $iface, $base);
    if ($agentCrm === '' || $interno === '') {
        return array('ok' => false, 'agent_crm' => '', 'interno' => '', 'reason' => 'unmapped_member');
    }
    if (!preg_match('/^[A-Za-z0-9_.-]{1,64}$/', $agentCrm)) {
        return array('ok' => false, 'agent_crm' => '', 'interno' => '', 'reason' => 'bad_agent_map');
    }
    if (!preg_match('/^[A-Za-z0-9_.-]{1,32}$/', $interno)) {
        return array('ok' => false, 'agent_crm' => '', 'interno' => '', 'reason' => 'bad_extension_map');
    }
    return array('ok' => true, 'agent_crm' => $agentCrm, 'interno' => $interno, 'reason' => '');
}

// --- Jobs y worker ---

function crm_ensure_spool_dir($dir) {
    if (!is_string($dir) || $dir === '') {
        return false;
    }
    if (is_dir($dir)) {
        return true;
    }
    $old = umask(0077);
    $ok = @mkdir($dir, 0700, true);
    umask($old);
    if (!$ok) {
        return false;
    }
    @chmod($dir, 0700);
    return is_dir($dir);
}

function crm_job_write($spoolDir, $data) {
    if (!crm_ensure_spool_dir($spoolDir)) {
        return false;
    }
    $json = json_encode($data);
    if (!is_string($json) || $json === '') {
        return false;
    }
    $tmp = tempnam($spoolDir, 'job-');
    if ($tmp === false) {
        return false;
    }
    @chmod($tmp, 0600);
    $bytes = @file_put_contents($tmp, $json, LOCK_EX);
    if ($bytes === false || $bytes <= 0) {
        @unlink($tmp);
        return false;
    }
    @chmod($tmp, 0600);
    $final = $spoolDir . '/atencion-' . preg_replace('/[^A-Za-z0-9._-]/', '', (string) $data['event_id']) . '.job';
    if (strlen($final) > 512) {
        @unlink($tmp);
        return false;
    }
    if (!@rename($tmp, $final)) {
        @unlink($tmp);
        return false;
    }
    @chmod($final, 0600);
    return $final;
}

function crm_php_binary() {
    if (defined('PHP_BINARY') && is_string(PHP_BINARY) && PHP_BINARY !== '') {
        return PHP_BINARY;
    }
    return '/usr/bin/php';
}

function crm_dispatch_worker($workerPhp, $jobPath) {
    if (!is_string($workerPhp) || $workerPhp === '' || !is_string($jobPath) || $jobPath === '') {
        return false;
    }
    // Sin CUIL/token/body en argv: solo la ruta del job.
    $php = crm_php_binary();
    $cmd = escapeshellarg($php) . ' ' . escapeshellarg($workerPhp) . ' ' . escapeshellarg($jobPath) . ' >/dev/null 2>&1 </dev/null &';
    @exec($cmd, $out, $code);
    // Best effort: no bloquear ni fallar la llamada por el dispatch.
    return true;
}
