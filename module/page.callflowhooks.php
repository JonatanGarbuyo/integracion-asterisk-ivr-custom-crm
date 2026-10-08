<?php
if (!defined('ISSABELPBX_IS_AUTH')) { die('No direct script access allowed'); }
if (!isset($_SESSION['AMP_user']) || !is_object($_SESSION['AMP_user']) ||
    !$_SESSION['AMP_user']->checkSection('callflowhooks')) {
    echo 'Acceso denegado';
    return;
}
try {
    if (!isset($_SESSION['callflowhooks_csrf'])) {
        $strong = false;
        $random = openssl_random_pseudo_bytes(32, $strong);
        if (!$random || !$strong) throw new Exception('No se pudo crear token del formulario');
        $_SESSION['callflowhooks_csrf'] = bin2hex($random);
    }
    $configuration = callflowhooks_backend(array('action'=>'describe'));
    if ($_SERVER['REQUEST_METHOD'] === 'POST') {
        if (!isset($_POST['csrf_token']) || !is_string($_POST['csrf_token']) ||
            $_POST['csrf_token'] !== $_SESSION['callflowhooks_csrf']) throw new Exception('Formulario vencido; recargar');
        if (isset($_POST['synchronize'])) {
            foreach ($configuration['profiles'] as $item) callflowhooks_register($item['identifier']);
            needreload();
            echo '<p>Destinos sincronizados. Aplicar configuración.</p>';
        } else {
            $extension = null;
            foreach ($configuration['extensions'] as $item) {
                if (isset($_POST['extension']) && $item['identifier'] === $_POST['extension']) $extension = $item;
            }
            if (!$extension) throw new Exception('Extensión desconocida');
            $profile = callflowhooks_post_fields($configuration['core_fields'], $_POST);
            $profile['identifier'] = isset($_POST['identifier']) ? $_POST['identifier'] : '';
            $profile['extension'] = $extension['identifier'];
            $profile['settings'] = callflowhooks_post_fields($extension['fields'], isset($_POST['settings']) && is_array($_POST['settings']) ? $_POST['settings'] : array());
            $configuration = callflowhooks_save($profile, isset($_POST['configuration_version']) ? $_POST['configuration_version'] : '');
            echo '<p>Perfil guardado. Seleccionar su destino en el IVR y aplicar configuración.</p>';
        }
    }
    echo '<h2>CallFlow Hooks</h2><p>Perfiles de handlers desde IVR</p><ul>';
    $selected = null;
    foreach ($configuration['profiles'] as $profile) {
        echo '<li><a href="config.php?display=callflowhooks&amp;profile='.rawurlencode($profile['identifier']).'">'.callflowhooks_escape($profile['identifier']).'</a> — '.callflowhooks_escape($profile['custom_destination']).'</li>';
        if (isset($_GET['profile']) && $_GET['profile'] === $profile['identifier']) $selected = $profile;
    }
    echo '</ul><p><a href="config.php?display=callflowhooks">Nuevo perfil</a></p>';
    $extensionId = $selected ? $selected['extension'] : (isset($_GET['extension']) ? $_GET['extension'] : $configuration['extensions'][0]['identifier']);
    $extension = null;
    echo '<p><label>Extensión <select onchange="window.location.href=\'config.php?display=callflowhooks&amp;extension=\'+encodeURIComponent(this.value)">';
    foreach ($configuration['extensions'] as $item) {
        if ($item['identifier'] === $extensionId) $extension = $item;
        echo '<option value="'.callflowhooks_escape($item['identifier']).'"'.($item['identifier'] === $extensionId ? ' selected' : '').'>'.callflowhooks_escape($item['title']).'</option>';
    }
    echo '</select></label></p>';
    if (!$extension) throw new Exception('Extensión desconocida');
    echo '<form method="post" action="config.php?display=callflowhooks">';
    foreach (array('csrf_token'=>$_SESSION['callflowhooks_csrf'], 'configuration_version'=>$configuration['configuration_version'], 'extension'=>$extensionId) as $name=>$value) {
        echo '<input type="hidden" name="'.$name.'" value="'.callflowhooks_escape($value).'">';
    }
    echo '<p><label>Identificador <input name="identifier" value="'.callflowhooks_escape($selected ? $selected['identifier'] : '').'"'.($selected ? ' readonly' : '').'></label></p>';
    foreach ($configuration['core_fields'] as $name=>$field) {
        callflowhooks_field($name, $field, $selected ? $selected[$name] : (isset($field['default']) ? $field['default'] : ''));
    }
    foreach ($extension['fields'] as $name=>$field) {
        callflowhooks_field('settings['.$name.']', $field, $selected ? $selected['settings'][$name] : (isset($field['default']) ? $field['default'] : ''));
    }
    echo '<p><button type="submit">Guardar perfil</button> <button name="synchronize" value="1" type="submit">Sincronizar destinos de .conf</button></p></form>';
} catch (Exception $error) {
    echo '<p role="alert">'.callflowhooks_escape($error->getMessage()).'</p>';
}
