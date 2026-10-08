<?php
if (!defined('ISSABELPBX_IS_AUTH')) { die('No direct script access allowed'); }
if (!defined('CFH_NATIVE_AUTHORIZED') && (!isset($_SESSION['AMP_user']) || !is_object($_SESSION['AMP_user']) ||
    !$_SESSION['AMP_user']->checkSection('callflowhooks'))) {
    echo 'Acceso denegado';
    return;
}
$callflowhooks_form_url = defined('CFH_NATIVE_AUTHORIZED') ? 'index.php?menu=callflowhooks' : 'config.php?display=callflowhooks';
$callflowhooks_pbx_configuration_url = defined('CFH_NATIVE_AUTHORIZED') ? '/index.php?menu=pbxadmin' : '/admin/';
echo '<h2>CallFlow Hooks</h2><p>Perfiles de handlers desde IVR</p>';
try {
    if (!isset($_SESSION['callflowhooks_csrf'])) {
        $strong = false;
        $random = openssl_random_pseudo_bytes(32, $strong);
        if (!$random || !$strong) throw new callflowhooks_backend_error('No se pudo crear token del formulario');
        $_SESSION['callflowhooks_csrf'] = bin2hex($random);
    }
    $configuration = callflowhooks_backend(array('action'=>'describe'));
} catch (Exception $error) {
    $message = $error instanceof callflowhooks_backend_error ? $error->getMessage() : 'No se pudo cargar la configuración.';
    echo '<p role="alert">'.callflowhooks_escape($message).'</p><p><a href="'.$callflowhooks_form_url.'">Reintentar</a></p>';
    return;
}
$selectedId = isset($_GET['profile']) && is_string($_GET['profile']) ? $_GET['profile'] : null;
$showDraft = !isset($_GET['new']) && !isset($_GET['extension']);
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $submitted = null;
    $extension = null;
    try {
        if (!isset($_POST['csrf_token']) || !is_string($_POST['csrf_token']) ||
            $_POST['csrf_token'] !== $_SESSION['callflowhooks_csrf']) throw new callflowhooks_backend_error('Formulario vencido; recargar');
        if (isset($_POST['discard_draft'])) {
            unset($_SESSION['callflowhooks_draft']);
            $selectedId = isset($_POST['identifier']) && is_string($_POST['identifier']) ? $_POST['identifier'] : null;
            echo '<p>Borrador descartado. La configuración guardada se conserva.</p>';
        } elseif (isset($_POST['synchronize'])) {
            foreach ($configuration['profiles'] as $item) callflowhooks_register($item['identifier']);
            needreload();
            echo '<p>Destinos sincronizados. Aplicar configuración.</p>';
        } else {
            foreach ($configuration['extensions'] as $item) {
                if (isset($_POST['extension']) && $item['identifier'] === $_POST['extension']) $extension = $item;
            }
            if (!$extension) throw new callflowhooks_backend_error('Seleccionar una extensión instalada.');
            $submitted = callflowhooks_post_fields($configuration['core_fields'], $_POST);
            $submitted['identifier'] = isset($_POST['identifier']) ? $_POST['identifier'] : '';
            $submitted['extension'] = $extension['identifier'];
            $submitted['settings'] = callflowhooks_post_fields($extension['fields'], isset($_POST['settings']) && is_array($_POST['settings']) ? $_POST['settings'] : array());
            $configuration = callflowhooks_save($submitted, isset($_POST['configuration_version']) ? $_POST['configuration_version'] : '');
            unset($_SESSION['callflowhooks_draft']);
            $selectedId = $submitted['identifier'];
            echo '<p>Perfil guardado. En el IVR, seleccionar Custom Destinations → CallFlow Hooks: '.callflowhooks_escape($selectedId).'. Aplicar configuración en <a href="'.$callflowhooks_pbx_configuration_url.'">Configuración PBX</a>.</p>';
        }
    } catch (Exception $error) {
        $message = $error instanceof callflowhooks_backend_error ? $error->getMessage() : 'No se pudo completar la operación PBX. Revisar el registro del servidor.';
        if ($submitted !== null && $extension !== null) {
            $draft = callflowhooks_public_draft($submitted, $configuration['core_fields'], $extension);
            $draft['error'] = $message;
            $draft['fields'] = $error instanceof callflowhooks_backend_error ? $error->fields : array();
            $_SESSION['callflowhooks_draft'] = $draft;
            $selectedId = $draft['profile']['identifier'];
            $showDraft = true;
        } else echo '<p role="alert">'.callflowhooks_escape($message).'</p>';
    }
}
$selected = null;
$editing = false;
echo '<ul>';
foreach ($configuration['profiles'] as $profile) {
    echo '<li><a href="'.$callflowhooks_form_url.'&amp;profile='.rawurlencode($profile['identifier']).'">'.callflowhooks_escape($profile['identifier']).'</a> — '.callflowhooks_escape($profile['custom_destination']).'</li>';
    if ($selectedId === $profile['identifier']) { $selected = $profile; $editing = true; }
}
echo '</ul><p><a href="'.$callflowhooks_form_url.'&amp;new=1">Nuevo perfil</a></p>';
$draft = isset($_SESSION['callflowhooks_draft']) ? $_SESSION['callflowhooks_draft'] : null;
$fields = array();
if ($showDraft && $draft && ($selectedId === null || $selectedId === $draft['profile']['identifier'])) {
    $selected = $draft['profile'];
    foreach ($configuration['profiles'] as $item) {
        if ($item['identifier'] === $selected['identifier']) $editing = true;
    }
    $fields = $draft['fields'];
    echo '<p role="alert">'.callflowhooks_escape($draft['error']).'</p><p>Borrador recuperado; corregir los campos y volver a guardar.</p>';
    if ($draft['secret_retry']) echo '<p>Volvé a ingresar las credenciales que habías cambiado; no se conservan en el borrador.</p>';
} else $draft = null;
$extensionId = $selected ? $selected['extension'] : (isset($_GET['extension']) && is_string($_GET['extension']) ? $_GET['extension'] : $configuration['extensions'][0]['identifier']);
$extension = null;
echo '<p><label>Extensión <select onchange="window.location.href=\''.$callflowhooks_form_url.'&amp;extension=\'+encodeURIComponent(this.value)">';
foreach ($configuration['extensions'] as $item) {
    if ($item['identifier'] === $extensionId) $extension = $item;
    echo '<option value="'.callflowhooks_escape($item['identifier']).'"'.($item['identifier'] === $extensionId ? ' selected' : '').'>'.callflowhooks_escape($item['title']).'</option>';
}
echo '</select></label></p>';
if (!$extension) {
    echo '<p role="alert">Seleccionar una extensión instalada.</p>';
    return;
}
echo '<form method="post" action="'.$callflowhooks_form_url.'">';
foreach (array('csrf_token'=>$_SESSION['callflowhooks_csrf'], 'configuration_version'=>$configuration['configuration_version'], 'extension'=>$extensionId) as $name=>$value) {
    echo '<input type="hidden" name="'.$name.'" value="'.callflowhooks_escape($value).'">';
}
echo '<p><label>Identificador <input name="identifier" value="'.callflowhooks_escape($selected ? $selected['identifier'] : '').'" maxlength="40" required'.($editing ? ' readonly' : '').'></label></p><p>Ejemplo: prueba. Usar letras minúsculas, dígitos, guion o guion bajo.</p>';
if (isset($fields['identifier'])) echo '<p role="alert">Identificador: '.callflowhooks_escape($fields['identifier']).'</p>';
foreach ($configuration['core_fields'] as $name=>$field) {
    callflowhooks_field($name, $field, $selected ? $selected[$name] : (isset($field['default']) ? $field['default'] : ''), isset($fields[$name]) ? $fields[$name] : '');
}
foreach ($extension['fields'] as $name=>$field) {
    $key = 'settings.'.$name;
    callflowhooks_field('settings['.$name.']', $field, $selected ? $selected['settings'][$name] : (isset($field['default']) ? $field['default'] : ''), isset($fields[$key]) ? $fields[$key] : '');
}
echo '<p><button type="submit">Guardar perfil</button> <button name="synchronize" value="1" type="submit" formnovalidate>Sincronizar destinos de .conf</button>';
if ($draft) echo ' <button name="discard_draft" value="1" type="submit" formnovalidate>Descartar borrador</button>';
echo '</p></form>';
