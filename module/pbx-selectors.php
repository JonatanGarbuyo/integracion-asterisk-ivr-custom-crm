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
                    $catalog = $result;
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
        if ($category === 'cfh_existing' && isset($post['cfh_existing'.$index]) && $post['cfh_existing'.$index] === $manual) return $manual;
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
    $error = 'Seleccionar un destino de PBX. Para crearlo, usar Agregar nuevo en el selector.';
    throw new callflowhooks_backend_error($error, array($name=>$error));
}

function callflowhooks_post_recording($post, $manual) {
    if (!isset($post['input_prompt_mode']) || $post['input_prompt_mode'] === 'manual') return $manual;
    if ($post['input_prompt_mode'] === 'pbx') {
        $id = isset($post['input_prompt_recording_id']) ? $post['input_prompt_recording_id'] : null;
        if ($id === '') return '';
        if ($id === 'cfh_existing') return $manual;
        // The distribution's recording lookup interpolates its ID: never pass untrusted text.
        if (is_string($id) && preg_match('/^[1-9][0-9]{0,9}$/D', $id) && function_exists('recordings_get_file')) {
            $file = recordings_get_file($id);
            if (is_string($file) && $file !== '' && strpos($file, '&') === false) return $file;
        }
    }
    $error = 'Seleccionar una grabación simple existente o Sin audio.';
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

function callflowhooks_popover_metadata($label, $items) {
    global $active_modules, $drawselects_module_hash, $fw_popover;
    if (!empty($fw_popover) || !isset($drawselects_module_hash[$label])) return array();
    $module = $drawselects_module_hash[$label];
    $id = $module;
    foreach ($items as $item) if ($item['destination'] !== 'popover') $id = isset($item['id']) ? $item['id'] : $module;
    $provider = strtolower($module.'_destination_popovers');
    if (function_exists($provider)) {
        foreach ($provider() as $popoverId=>$category) {
            if ($category === $label) { $id = $popoverId; break; }
        }
    }
    if (!isset($active_modules[$module]['popovers'][$id])) return array();
    // Metadata comes from installed module.xml; escape it when emitting attributes.
    return array('module'=>$module, 'id'=>$id, 'url'=>'config.php?'.http_build_query($active_modules[$module]['popovers'][$id], '', '&'));
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
        echo '<option value="'.callflowhooks_escape($key).'"'.($key === $selectedCategory ? ' selected' : '').'>'.callflowhooks_escape($label === 'cfh_existing' ? 'Destino actual' : $label).'</option>';
    }
    echo '</select> ';
    foreach ($catalog as $label=>$items) {
        $key = callflowhooks_category_key($label, $catalog);
        $id = callflowhooks_escape($key.$index);
        $metadata = callflowhooks_popover_metadata($label, $items);
        $classes = $metadata ? ' '.callflowhooks_escape($metadata['module']).($metadata['id'] !== $metadata['module'] ? ' '.callflowhooks_escape($metadata['id']) : '') : '';
        $attributes = $metadata ? ' data-url="'.callflowhooks_escape($metadata['url']).'" data-class="'.callflowhooks_escape($metadata['id']).'" data-mod="'.callflowhooks_escape($metadata['module']).'"' : '';
        echo '<select'.$attributes.' name="'.$id.'" id="'.$id.'" class="destdropdown2'.$classes.'" data-id="'.$escapedIndex.'" data-last="'.callflowhooks_escape($value).'"'.($key === $selectedCategory ? '' : ' style="display:none"').' aria-label="'.callflowhooks_escape('Destino: '.$label).'">';
        foreach ($items as $item) {
            if ($item['destination'] === 'popover' && !$metadata) continue;
            $description = html_entity_decode($item['description'], ENT_QUOTES, 'UTF-8');
            echo '<option value="'.callflowhooks_escape($item['destination']).'"'.($value === $item['destination'] ? ' selected' : '').'>'.callflowhooks_escape($description).'</option>';
        }
        echo '</select>';
    }
}

function callflowhooks_destination_field($name, $field, $value, $error = '') {
    $catalog = callflowhooks_destination_catalog();
    if ($catalog === null) {
        callflowhooks_field_open($field, 'callflowhooks-'.$name);
        echo '<input type="hidden" name="'.$name.'" value="'.callflowhooks_escape($value).'">';
        echo '<p role="alert">Selector PBX no disponible. Revisar los módulos de Configuración PBX.</p>';
        callflowhooks_field_close($field, $error);
        return;
    }
    $known = $value === '';
    foreach ($catalog as $items) foreach ($items as $item) if ($value === $item['destination']) $known = true;
    if (!$known) $catalog['cfh_existing'] = array(array('destination'=>$value, 'description'=>'Valor actual de .conf: '.$value));
    callflowhooks_field_open($field, 'gotocallflow_'.$name);
    echo '<input type="hidden" name="'.$name.'" value="'.callflowhooks_escape($value).'"><input type="hidden" name="'.$name.'_mode" value="pbx">';
    callflowhooks_destination_selects($catalog, 'callflow_'.$name, $value, true);
    callflowhooks_field_close($field, $error);
}

function callflowhooks_recording_field($name, $field, $value, $error = '') {
    $items = callflowhooks_recording_catalog();
    callflowhooks_field_open($field, 'callflowhooks-recording');
    echo '<input type="hidden" name="'.$name.'" value="'.callflowhooks_escape($value).'">';
    if ($items === null) {
        echo '<p role="alert">System Recordings no disponible. El audio actual se conserva.</p>';
    } else {
        $selectedId = $value === '' ? '' : null;
        foreach ($items as $item) if ($value === $item['filename']) $selectedId = (string)$item['id'];
        echo '<input type="hidden" name="input_prompt_mode" value="pbx"><select name="input_prompt_recording_id" id="callflowhooks-recording"><option value="">Sin audio</option>';
        if ($selectedId === null) echo '<option value="cfh_existing" selected>'.callflowhooks_escape('Valor actual de .conf: '.$value).'</option>';
        foreach ($items as $item) {
            echo '<option value="'.callflowhooks_escape($item['id']).'"'.((string)$item['id'] === $selectedId ? ' selected' : '').'>'.callflowhooks_escape($item['displayname']).'</option>';
        }
        echo '</select>';
    }
    callflowhooks_field_close($field, $error);
}
