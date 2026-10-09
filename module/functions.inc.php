<?php
if (!defined('ISSABELPBX_IS_AUTH')) { die('No direct script access allowed'); }

class callflowhooks_backend_error extends Exception {
    public $fields;
    function __construct($message, $fields = array()) {
        parent::__construct($message);
        $this->fields = $fields;
    }
}

function callflowhooks_escape($value) {
    return htmlspecialchars((string)$value, ENT_QUOTES, 'UTF-8');
}

function callflowhooks_entry() {
    // The legacy archive keeps a private copy; RPM owns the shared runtime.
    if (defined('CFH_CORE_DIRECTORY')) return CFH_CORE_DIRECTORY.'/backend/entry.py';
    if (is_file('/usr/share/callflow-hooks/backend/entry.py')) return '/usr/share/callflow-hooks/backend/entry.py';
    if (is_file(dirname(__FILE__).'/backend/entry.py')) return dirname(__FILE__).'/backend/entry.py';
    return '/usr/share/callflow-hooks/backend/entry.py';
}

function callflowhooks_backend($request) {
    $python = defined('CFH_PYTHON_BINARY') ? CFH_PYTHON_BINARY : '/usr/bin/python3';
    $config = defined('CFH_CONFIGURATION_FILE') ? CFH_CONFIGURATION_FILE : '/etc/asterisk/callflow-hooks/profiles.conf';
    $command = escapeshellarg($python).' '.escapeshellarg(callflowhooks_entry()).
               ' --config '.escapeshellarg($config).' admin';
    $payload = json_encode($request);
    if ($payload === false || strlen($payload) > 65536) throw new callflowhooks_backend_error('Solicitud demasiado grande');
    $pipes = array();
    $process = proc_open($command, array(0=>array('pipe','r'), 1=>array('pipe','w'), 2=>array('file','/dev/null','a')), $pipes);
    if (!is_resource($process)) throw new callflowhooks_backend_error('No se pudo ejecutar el administrador local');
    stream_set_blocking($pipes[0], false);
    stream_set_blocking($pipes[1], false);
    $deadline = microtime(true) + 3;
    $output = '';
    $offset = 0;
    $stdinOpen = true;
    while (true) {
        if ($stdinOpen) {
            $written = fwrite($pipes[0], substr($payload, $offset));
            if ($written === false) break;
            $offset += $written;
            if ($offset === strlen($payload)) { fclose($pipes[0]); $stdinOpen = false; }
        }
        $chunk = fread($pipes[1], 8192);
        if ($chunk !== false) $output .= $chunk;
        if (strlen($output) > 262144 || microtime(true) > $deadline) break;
        if (feof($pipes[1])) break;
        usleep(10000);
    }
    if ($stdinOpen) fclose($pipes[0]);
    fclose($pipes[1]);
    $status = proc_get_status($process);
    if ($status['running']) proc_terminate($process, 9);
    proc_close($process);
    if (microtime(true) > $deadline || strlen($output) > 262144) throw new callflowhooks_backend_error('Administrador local fuera de límite');
    $response = json_decode($output, true);
    if (!is_array($response)) throw new callflowhooks_backend_error('No se recibió una respuesta válida del administrador local.');
    if (empty($response['ok'])) {
        $codes = array('validation_error', 'stale_configuration', 'permission_denied', 'io_error', 'configuration_error');
        $message = 'Configuración inválida o no disponible; revisar campos, versión y permisos';
        $fields = array();
        if (isset($response['error_code']) && in_array($response['error_code'], $codes, true) &&
            isset($response['error']) && is_string($response['error']) && strlen($response['error']) <= 1000) {
            $message = $response['error'];
            if (isset($response['field_errors']) && is_array($response['field_errors'])) {
                foreach ($response['field_errors'] as $name=>$error) {
                    if (is_string($name) && preg_match('/^(settings\.)?[A-Za-z][A-Za-z0-9_]{0,79}$/D', $name) &&
                        is_string($error) && strlen($error) <= 1000) $fields[$name] = $error;
                }
            }
        }
        throw new callflowhooks_backend_error($message, $fields);
    }
    return $response;
}

function callflowhooks_register($identifier) {
    if (!is_string($identifier) || !preg_match('/^[a-z][a-z0-9_-]{0,39}$/D', $identifier)) {
        $error = 'Usar una letra minúscula inicial, letras minúsculas, dígitos, guion o guion bajo; máximo 40 caracteres.';
        throw new callflowhooks_backend_error($error, array('identifier'=>$error));
    }
    if (!function_exists('customappsreg_customdests_get')) throw new callflowhooks_backend_error('Activar Custom Destinations antes de CallFlow Hooks');
    $destination = 'callflow-profile-'.$identifier.',s,1';
    $existing = customappsreg_customdests_get($destination);
    if ($existing) {
        if ($existing['notes'] !== 'Managed by CallFlow Hooks') throw new callflowhooks_backend_error('Destino ocupado por otra configuración');
        return false;
    }
    if (!customappsreg_customdests_add($destination, 'CallFlow Hooks: '.$identifier, 'Managed by CallFlow Hooks')) {
        throw new callflowhooks_backend_error('No se pudo registrar el destino');
    }
    return true;
}

function callflowhooks_save($profile, $version) {
    $identifier = $profile['identifier'];
    $created = callflowhooks_register($identifier);
    try {
        $result = callflowhooks_backend(array('action'=>'save', 'profile'=>$profile, 'expected_version'=>$version));
    } catch (Exception $error) {
        if ($created) customappsreg_customdests_delete('callflow-profile-'.$identifier.',s,1');
        throw $error;
    }
    needreload();
    return $result;
}

class callflowhooks_instruction {
    private $instruction;
    function __construct($instruction) { $this->instruction = $instruction; }
    function output() { return $this->instruction; }
    function incrementContents($value) { return true; }
}

function callflowhooks_get_config($engine) {
    global $ext;
    if ($engine !== 'asterisk') return;
    $configuration = callflowhooks_backend(array('action'=>'describe'));
    foreach ($configuration['profiles'] as $profile) {
        $context = 'callflow-profile-'.$profile['identifier'];
        // A valid fallback exists before invoking AGI, including interpreter/AGI failure.
        $commands = array(
            'Set(CALLFLOW_NEXT_DESTINATION='.$profile['fallback_destination'].')',
            'AGI('.callflowhooks_entry().',agi,'.$profile['identifier'].')',
            'Goto(${CALLFLOW_NEXT_DESTINATION})'
        );
        foreach ($commands as $command) $ext->add($context, 's', '', new callflowhooks_instruction($command));
    }
}

function callflowhooks_post_fields($fields, $source) {
    $values = array();
    foreach ($fields as $name=>$field) {
        $value = isset($source[$name]) ? $source[$name] : (isset($field['default']) ? $field['default'] : '');
        if ($field['type'] === 'boolean') $value = isset($source[$name]) && ($source[$name] === '1' || $source[$name] === true);
        elseif ($field['type'] === 'integer' && is_scalar($value) && preg_match('/^-?[0-9]+$/D', (string)$value)) $value = (int)$value;
        $values[$name] = $value;
    }
    return $values;
}

function callflowhooks_field($name, $field, $value, $error = '') {
    $id = 'callflowhooks-'.preg_replace('/[^A-Za-z0-9_-]/', '-', $name);
    $name = callflowhooks_escape($name);
    $label = callflowhooks_escape($field['label']);
    echo '<tr><td><label for="'.$id.'">'.$label.'</label>';
    if (isset($field['help'])) echo '<span class="help">?<span>'.callflowhooks_escape($field['help']).'</span></span>';
    echo '</td><td>';
    if ($field['type'] === 'choice') {
        echo '<select name="'.$name.'" id="'.$id.'"'.($error ? ' aria-invalid="true"' : '').'>';
        foreach ($field['options'] as $option) {
            echo '<option value="'.callflowhooks_escape($option).'"'.($option === $value ? ' selected' : '').'>'.callflowhooks_escape($option).'</option>';
        }
        echo '</select>';
    } elseif ($field['type'] === 'boolean') {
        echo '<input type="checkbox" name="'.$name.'" value="1" id="'.$id.'"'.($value ? ' checked' : '').'>';
    } else {
        $type = $field['type'] === 'secret' ? 'password' : ($field['type'] === 'integer' ? 'number' : 'text');
        // Credentials are write-only in the form. Blank preserves a stored value.
        echo '<input type="'.$type.'" name="'.$name.'" value="'.($type === 'password' ? '' : callflowhooks_escape($value)).'" id="'.$id.'"';
        if ($type === 'text' || $type === 'password') echo ' size="35"';
        if ($error) echo ' aria-invalid="true"';
        if (!empty($field['required']) && $type !== 'password') echo ' required';
        foreach (array('minimum'=>'min', 'maximum'=>'max', 'max_length'=>'maxlength') as $key=>$attribute) {
            if (isset($field[$key])) echo ' '.$attribute.'="'.(int)$field[$key].'"';
        }
        echo '>';
        if ($type === 'password') echo ' (vacío conserva la credencial)';
    }

    if ($error) echo '<p role="alert">'.$label.': '.callflowhooks_escape($error).'</p>';
    echo '</td></tr>';
}

function callflowhooks_section($title) {
    echo '<tr><td colspan="2"><h5>'.callflowhooks_escape($title).'</h5><hr></td></tr>';
}

function callflowhooks_form_hidden($configuration, $embedded) {
    $values = array('csrf_token'=>$_SESSION['callflowhooks_csrf'], 'configuration_version'=>$configuration['configuration_version'], 'display'=>'callflowhooks', 'type'=>'setup');
    if ($embedded) $values['menu'] = 'pbxadmin';
    foreach ($values as $name=>$value) echo '<input type="hidden" name="'.$name.'" value="'.callflowhooks_escape($value).'">';
}

function callflowhooks_draft_value($value) {
    return is_scalar($value) && (!is_string($value) || strlen($value) <= 8192) ? $value : '';
}

function callflowhooks_public_draft($profile, $core, $extension) {
    $draft = array('identifier'=>callflowhooks_draft_value($profile['identifier']),
                   'extension'=>$extension['identifier'], 'settings'=>array());
    foreach ($core as $name=>$field) $draft[$name] = callflowhooks_draft_value($profile[$name]);
    $secretRetry = false;
    foreach ($extension['fields'] as $name=>$field) {
        $value = $profile['settings'][$name];
        if ($field['type'] === 'secret') {
            if (is_scalar($value) && (string)$value !== '') $secretRetry = true;
            $draft['settings'][$name] = '';
        } else $draft['settings'][$name] = callflowhooks_draft_value($value);
    }
    return array('profile'=>$draft, 'secret_retry'=>$secretRetry);
}
