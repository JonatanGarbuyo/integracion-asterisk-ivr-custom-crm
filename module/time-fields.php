<?php
if (!defined('ISSABELPBX_IS_AUTH')) { die('No direct script access allowed'); }
function callflowhooks_seconds($milliseconds) {
    $digits = str_pad((string)(int)$milliseconds, 4, '0', STR_PAD_LEFT);
    $whole = ltrim(substr($digits, 0, -3), '0');
    $fraction = substr($digits, -3);
    return ($whole === '' ? '0' : $whole).($fraction === '000' ? '' : '.'.rtrim($fraction, '0'));
}
function callflowhooks_post_seconds(&$profile, $post, $fields) {
    $errors = array();
    foreach (array('execution_budget_ms', 'input_timeout_ms') as $name) {
        $secondsName = str_replace('_ms', '_seconds', $name);
        $maximum = (int)($fields[$name]['maximum'] / 1000);
        $valid = false;
        if (array_key_exists($secondsName, $post)) {
            $raw = $post[$secondsName];
            $valid = is_string($raw) && preg_match('/^[0-9]{1,3}$/D', $raw) && (int)$raw > 0 && (int)$raw <= $maximum;
            if ($valid) $profile[$name] = (int)$raw * 1000;
        } else {
            // Old HTTP clients cannot bypass the whole-second rule with canonical ms.
            $value = $profile[$name];
            $valid = is_int($value) && $value >= 1000 && $value <= $fields[$name]['maximum'] && $value % 1000 === 0;
        }
        if (!$valid) $errors[$name] = sprintf('Enter a whole number of seconds between 1 and %s.', $maximum);
    }
    if ($errors) throw new callflowhooks_backend_error('Correct the highlighted selections.', $errors);
}
function callflowhooks_seconds_field($name, $field, $value, $error = '', $raw = null) {
    $id = 'callflowhooks-'.$name;
    unset($field['help']);
    callflowhooks_field_open($field, $id);
    $display = $raw !== null ? $raw : callflowhooks_seconds($value);
    echo '<input type="number" min="1" max="'.(int)($field['maximum']/1000).'" step="1" name="'.str_replace('_ms', '_seconds', $name).'" id="'.$id.'" value="'.callflowhooks_escape($display).'" required'.($error ? ' aria-invalid="true"' : '').'>';
    callflowhooks_field_close($field, $error);
}
