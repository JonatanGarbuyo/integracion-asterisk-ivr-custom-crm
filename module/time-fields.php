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
        if (!isset($post[str_replace('_ms', '_seconds', $name)])) continue; // Older clients still send canonical milliseconds.
        $raw = $post[str_replace('_ms', '_seconds', $name)];
        $valid = is_string($raw) && strlen($raw) <= 16 && preg_match('/^([0-9]{1,5})?(?:\.([0-9]{1,3}))?$/D', $raw, $parts) && $raw !== '' && $raw !== '.';
        $milliseconds = 0;
        if ($valid) $milliseconds = (isset($parts[1]) && $parts[1] !== '' ? (int)$parts[1] : 0) * 1000 + (isset($parts[2]) ? (int)str_pad($parts[2], 3, '0') : 0);
        if (!$valid || $milliseconds < $fields[$name]['minimum'] || $milliseconds > $fields[$name]['maximum']) {
            $errors[$name] = sprintf('Enter seconds between %s and %s, with up to three decimal places.', callflowhooks_seconds($fields[$name]['minimum']), callflowhooks_seconds($fields[$name]['maximum']));
        } else $profile[$name] = $milliseconds;
    }
    if ($errors) throw new callflowhooks_backend_error('Correct the highlighted selections.', $errors);
}
function callflowhooks_seconds_field($name, $field, $value, $error = '', $raw = null) {
    $id = 'callflowhooks-'.$name;
    $field['help'] = $name === 'execution_budget_ms' ? 'The timeout is independent of digit entry. Fractions of a second are allowed.' : 'Time to enter DTMF digits. Fractions of a second are allowed.';
    callflowhooks_field_open($field, $id);
    $display = $raw !== null ? $raw : callflowhooks_seconds($value);
    echo '<input type="text" inputmode="decimal" name="'.str_replace('_ms', '_seconds', $name).'" id="'.$id.'" value="'.callflowhooks_escape($display).'" required'.($error ? ' aria-invalid="true"' : '').'>';
    echo '<p>'.callflowhooks_escape(sprintf(callflowhooks_text('Enter seconds between %s and %s, with up to three decimal places.'),callflowhooks_seconds($field['minimum']),callflowhooks_seconds($field['maximum']))).'</p>';
    callflowhooks_field_close($field, $error);
}
