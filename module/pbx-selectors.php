<?php
if (!defined('ISSABELPBX_IS_AUTH')) { die('No direct script access allowed'); }

function callflowhooks_destination_catalog() {
    static $loaded = false, $catalog = null;
    if (!$loaded) {
        $loaded = true;
        // The legacy native bootstrap loads only our bridge, not every destination module.
        if (!defined('CFH_NATIVE_AUTHORIZED') && function_exists('drawselects')) {
            try {
                $result = drawselects('', 'callflow_catalog', false, false, '', false, true);
                if (is_array($result)) {
                    $catalog = array();
                    foreach ($result as $label=>$items) {
                        foreach ($items as $item) {
                            if ($item['destination'] !== 'popover') $catalog[$label][] = $item;
                        }
                    }
                }
            } catch (Exception $error) { $catalog = null; }
        }
    }
    return $catalog;
}

function callflowhooks_recording_catalog() {
    if (defined('CFH_NATIVE_AUTHORIZED') || !function_exists('recordings_list')) return null;
    try {
        $items = recordings_list(false); // GET DATA accepts one sound, not a compound recording.
        return is_array($items) ? $items : null;
    } catch (Exception $error) { return null; }
}

function callflowhooks_category_key($label, $catalog) {
    $key = str_replace(' ', '_', $label);
    // Native JS uses the key in a CSS selector. Keep ordinary PBX names; encode unusual labels.
    $collision = false;
    foreach ($catalog as $otherLabel=>$items) {
        if ($otherLabel !== $label && str_replace(' ', '_', $otherLabel) === $key) $collision = true;
    }
    return !$collision && preg_match('/^[A-Za-z_][A-Za-z0-9_-]*$/D', $key) && strpos($key, 'cfh_category_') !== 0 ?
        $key : 'cfh_category_'.sha1($label);
}

function callflowhooks_post_destination($name, $post, $manual) {
    if (!isset($post[$name.'_mode']) || $post[$name.'_mode'] === 'manual') return $manual;
    if ($post[$name.'_mode'] === 'pbx') {
        $catalog = callflowhooks_destination_catalog();
        $index = 'callflow_'.$name;
        $category = isset($post['goto'.$index]) ? $post['goto'.$index] : '';
        if (is_array($catalog) && is_string($category)) {
            foreach ($catalog as $label=>$items) {
                $key = callflowhooks_category_key($label, $catalog);
                if ($category !== $key) continue;
                $destination = isset($post[$key.$index]) ? $post[$key.$index] : '';
                foreach ($items as $item) {
                    if (is_string($destination) && $destination !== 'popover' && $destination === $item['destination']) return $destination;
                }
            }
        }
    }
    $error = 'Seleccionar un destino existente de PBX o usar entrada manual.';
    throw new callflowhooks_backend_error($error, array($name=>$error));
}

function callflowhooks_post_recording($post, $manual) {
    if (!isset($post['input_prompt_mode']) || $post['input_prompt_mode'] === 'manual') return $manual;
    if ($post['input_prompt_mode'] === 'pbx') {
        $id = isset($post['input_prompt_recording_id']) ? $post['input_prompt_recording_id'] : null;
        if ($id === '') return '';
        // The distribution's recording lookup interpolates its ID: never pass untrusted text.
        if (is_string($id) && preg_match('/^[1-9][0-9]{0,9}$/D', $id) && function_exists('recordings_get_file')) {
            $file = recordings_get_file($id);
            if (is_string($file) && $file !== '' && strpos($file, '&') === false) return $file;
        }
    }
    $error = 'Seleccionar una grabación simple existente, Sin audio o entrada manual.';
    throw new callflowhooks_backend_error($error, array('input_prompt'=>$error));
}

function callflowhooks_resolve_selectors(&$profile, $post) {
    $errors = array();
    foreach (array('next_destination', 'fallback_destination', 'input_prompt') as $name) {
        try {
            $profile[$name] = $name === 'input_prompt' ? callflowhooks_post_recording($post, $profile[$name]) :
                callflowhooks_post_destination($name, $post, $profile[$name]);
        } catch (callflowhooks_backend_error $error) {
            $errors = array_merge($errors, $error->fields);
        }
    }
    // Resolve every valid selection before failing, so an unrelated error cannot erase it from the draft.
    if ($errors) throw new callflowhooks_backend_error('Corregir las selecciones indicadas.', $errors);
}

function callflowhooks_selector_start($name, $field, $manualMode) {
    $id = 'callflowhooks-'.$name.'-mode';
    callflowhooks_field_open($field, $id);
    echo '<div class="callflowhooks-picker"><select name="'.$name.'_mode" id="'.$id.'" onchange="callflowhooksToggleSelector(this)" aria-label="'.callflowhooks_escape($field['label'].': forma de selección').'">';
    echo '<option value="pbx"'.(!$manualMode ? ' selected' : '').'>Seleccionar de PBX</option><option value="manual"'.($manualMode ? ' selected' : '').'>Ingresar manualmente</option></select>';
}

function callflowhooks_selector_manual($name, $field, $value, $manualMode) {
    echo '<div class="callflowhooks-manual"'.(!$manualMode ? ' style="display:none"' : '').'><input type="text" name="'.$name.'" value="'.callflowhooks_escape($value).'" id="callflowhooks-'.$name.'" size="35" maxlength="'.(int)$field['max_length'].'"'.($manualMode && !empty($field['required']) ? ' required' : '').' aria-label="'.callflowhooks_escape($field['label'].' manual').'" data-required="'.(!empty($field['required']) ? '1' : '0').'"></div>';
}

function callflowhooks_destination_selects($catalog, $index, $value, $required) {
    $selectedCategory = '';
    foreach ($catalog as $label=>$items) foreach ($items as $item) {
        if ($value === $item['destination']) $selectedCategory = callflowhooks_category_key($label, $catalog);
    }
    // Reuse the native catalog and JS contract, escaping text that old drawselects() inserts raw.
    $escapedIndex = callflowhooks_escape($index);
    echo '<select name="goto'.$escapedIndex.'" id="goto'.$escapedIndex.'" class="destdropdown" data-id="'.$escapedIndex.'" data-last="'.callflowhooks_escape($selectedCategory).'"'.($required ? ' required' : '').' aria-label="Categoría de destino"><option value="">Seleccionar categoría</option>';
    foreach ($catalog as $label=>$items) {
        $key = callflowhooks_category_key($label, $catalog);
        echo '<option value="'.callflowhooks_escape($key).'"'.($key === $selectedCategory ? ' selected' : '').'>'.callflowhooks_escape($label).'</option>';
    }
    echo '</select> ';
    foreach ($catalog as $label=>$items) {
        $key = callflowhooks_category_key($label, $catalog);
        $id = callflowhooks_escape($key.$index);
        echo '<select name="'.$id.'" id="'.$id.'" class="destdropdown2" data-id="'.$escapedIndex.'" data-last="'.callflowhooks_escape($value).'"'.($key === $selectedCategory ? '' : ' style="display:none"').' aria-label="'.callflowhooks_escape('Destino: '.$label).'">';
        foreach ($items as $item) {
            $description = html_entity_decode($item['description'], ENT_QUOTES, 'UTF-8');
            echo '<option value="'.callflowhooks_escape($item['destination']).'"'.($value === $item['destination'] ? ' selected' : '').'>'.callflowhooks_escape($description).'</option>';
        }
        echo '</select>';
    }
}

function callflowhooks_destination_field($name, $field, $value, $error = '') {
    $catalog = callflowhooks_destination_catalog();
    if ($catalog === null) { callflowhooks_field($name, $field, $value, $error); return; }
    $known = $value === '';
    foreach ($catalog as $items) foreach ($items as $item) if ($value === $item['destination']) $known = true;
    $manualMode = !$known || empty($catalog);
    callflowhooks_selector_start($name, $field, $manualMode);
    echo '<div class="callflowhooks-selection"'.($manualMode ? ' style="display:none"' : '').'>';
    callflowhooks_destination_selects($catalog, 'callflow_'.$name, $known ? $value : '', !$manualMode);
    echo '</div>';
    callflowhooks_selector_manual($name, $field, $value, $manualMode);
    echo '</div>';
    callflowhooks_field_close($field, $error);
}

function callflowhooks_recording_field($name, $field, $value, $error = '') {
    $items = callflowhooks_recording_catalog();
    if ($items === null) { callflowhooks_field($name, $field, $value, $error); return; }
    $selectedId = $value === '' ? '' : null;
    foreach ($items as $item) if ($value === $item['filename']) $selectedId = (string)$item['id'];
    $manualMode = $selectedId === null;
    callflowhooks_selector_start($name, $field, $manualMode);
    echo '<div class="callflowhooks-selection"'.($manualMode ? ' style="display:none"' : '').'><select name="input_prompt_recording_id" id="callflowhooks-recording" aria-label="Grabación del sistema"><option value="">Sin audio</option>';
    foreach ($items as $item) {
        echo '<option value="'.callflowhooks_escape($item['id']).'"'.((string)$item['id'] === $selectedId ? ' selected' : '').'>'.callflowhooks_escape($item['displayname']).'</option>';
    }
    echo '</select></div>';
    callflowhooks_selector_manual($name, $field, $value, $manualMode);
    echo '</div>';
    callflowhooks_field_close($field, $error);
}

function callflowhooks_selector_script() {
    echo '<script type="text/javascript">
function callflowhooksToggleSelector(select) {
    var picker = select.parentNode;
    var manual = select.value === "manual";
    picker.querySelector(".callflowhooks-manual").style.display = manual ? "" : "none";
    picker.querySelector(".callflowhooks-selection").style.display = manual ? "none" : "";
    var input = picker.querySelector(".callflowhooks-manual input");
    input.required = manual && input.getAttribute("data-required") === "1";
    var destination = picker.querySelector(".destdropdown");
    if (destination) destination.required = !manual;
}
</script>';
}
