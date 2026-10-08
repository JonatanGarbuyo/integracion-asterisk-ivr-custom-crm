<?php
if (!defined('ISSABELPBX_IS_AUTH')) { die('No direct script access allowed'); }

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
    if ($payload === false || strlen($payload) > 65536) throw new Exception('Solicitud demasiado grande');
    $pipes = array();
    $process = proc_open($command, array(0=>array('pipe','r'), 1=>array('pipe','w'), 2=>array('file','/dev/null','a')), $pipes);
    if (!is_resource($process)) throw new Exception('No se pudo ejecutar el administrador local');
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
    if (microtime(true) > $deadline || strlen($output) > 262144) throw new Exception('Administrador local fuera de límite');
    $response = json_decode($output, true);
    if (!is_array($response) || empty($response['ok'])) throw new Exception('Configuración inválida o no disponible; revisar campos, versión y permisos');
    return $response;
}

function callflowhooks_register($identifier) {
    if (!is_string($identifier) || !preg_match('/^[a-z][a-z0-9_-]{0,39}$/D', $identifier)) throw new Exception('Identificador inválido');
    if (!function_exists('customappsreg_customdests_get')) throw new Exception('Activar Custom Destinations antes de CallFlow Hooks');
    $destination = 'callflow-profile-'.$identifier.',s,1';
    $existing = customappsreg_customdests_get($destination);
    if ($existing) {
        if ($existing['notes'] !== 'Managed by CallFlow Hooks') throw new Exception('Destino ocupado por otra configuración');
        return false;
    }
    if (!customappsreg_customdests_add($destination, 'CallFlow Hooks: '.$identifier, 'Managed by CallFlow Hooks')) {
        throw new Exception('No se pudo registrar el destino');
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

function callflowhooks_field($name, $field, $value) {
    $name = callflowhooks_escape($name);
    $label = callflowhooks_escape($field['label']);
    echo '<p><label>'.$label.' ';
    if ($field['type'] === 'choice') {
        echo '<select name="'.$name.'">';
        foreach ($field['options'] as $option) {
            echo '<option value="'.callflowhooks_escape($option).'"'.($option === $value ? ' selected' : '').'>'.callflowhooks_escape($option).'</option>';
        }
        echo '</select>';
    } elseif ($field['type'] === 'boolean') {
        echo '<input type="checkbox" name="'.$name.'" value="1"'.($value ? ' checked' : '').'>';
    } else {
        $type = $field['type'] === 'secret' ? 'password' : ($field['type'] === 'integer' ? 'number' : 'text');
        // Credentials are write-only in the form. Blank preserves a stored value.
        echo '<input type="'.$type.'" name="'.$name.'" value="'.($type === 'password' ? '' : callflowhooks_escape($value)).'"';
        foreach (array('minimum'=>'min', 'maximum'=>'max', 'max_length'=>'maxlength') as $key=>$attribute) {
            if (isset($field[$key])) echo ' '.$attribute.'="'.(int)$field[$key].'"';
        }
        echo '>';
        if ($type === 'password') echo ' (vacío conserva la credencial)';
    }
    echo '</label></p>';
}
