<?php
/* Only the distribution's catalog/UI APIs are simulated; CFH and AGI run normally. */
function recordings_list($compound = true) {
    $items = isset($GLOBALS['request']['recordings']) ? $GLOBALS['request']['recordings'] : array(
        array('id'=>2, 'displayname'=>'bienvenido', 'filename'=>'custom/bienvenido'),
        array('id'=>3, 'displayname'=>'secuencia', 'filename'=>'custom/uno&custom/dos')
    );
    if ($compound) return $items;
    $simple = array();
    foreach ($items as $item) if (strpos($item['filename'], '&') === false) $simple[] = $item;
    return $simple;
}
function recordings_get_file($id) {
    foreach (recordings_list() as $item) if ((string)$item['id'] === (string)$id) return $item['filename'];
    return '';
}
function drawselects($current, $index, $custom=false, $table=true, $message='', $required=false, $output_array=false, $reset=false) {
    $catalog = isset($GLOBALS['request']['destination_catalog']) ? $GLOBALS['request']['destination_catalog'] : array('Queues'=>array(array('destination'=>'ext-queues,6000,1','description'=>'general <6000>')),
                     'Extensions'=>array(array('destination'=>'from-did-direct,101,1','description'=>'101')),
                     'Terminate Call'=>array(array('destination'=>'app-blackhole,hangup,1','description'=>'Hangup')));
    if ($output_array) return $catalog;
    $selected = '';
    foreach ($catalog as $category=>$items) foreach ($items as $item) {
        if ($item['destination'] === $current) $selected = str_replace(' ', '_', $category);
    }
    $html = '<select name="goto'.$index.'" id="goto'.$index.'" class="destdropdown" data-id="'.$index.'"'.($required ? ' required' : '').'><option value="">choose one</option>';
    foreach ($catalog as $category=>$items) {
        $key = str_replace(' ', '_', $category);
        $html .= '<option value="'.$key.'"'.($key === $selected ? ' selected' : '').'>'.$category.'</option>';
    }
    $html .= '</select>';
    foreach ($catalog as $category=>$items) {
        $key = str_replace(' ', '_', $category);
        $html .= '<select name="'.$key.$index.'" id="'.$key.$index.'" class="destdropdown2" data-id="'.$index.'"'.($key === $selected ? '' : ' style="display:none"').'>';
        foreach ($items as $item) {
            // The old PBX helper returns unescaped descriptions; do not invent a safer dependency.
            $html .= '<option value="'.$item['destination'].'"'.($item['destination'] === $current ? ' selected' : '').'>'.$item['description'].'</option>';
        }
        $html .= '</select>';
    }
    return $html;
}
