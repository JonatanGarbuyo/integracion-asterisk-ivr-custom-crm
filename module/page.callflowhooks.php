<?php
if (!defined('ISSABELPBX_IS_AUTH')) { die('No direct script access allowed'); }
if (!defined('CFH_NATIVE_AUTHORIZED') && (!isset($_SESSION['AMP_user']) || !is_object($_SESSION['AMP_user']) ||
    !$_SESSION['AMP_user']->checkSection('callflowhooks'))) {
    echo 'Acceso denegado';
    return;
}
// Issabel 4 embeds PBX through the framework dispatcher; Issabel 5 uses a PBX frame.
$callflowhooks_embedded = !defined('CFH_NATIVE_AUTHORIZED') &&
    ((isset($_GET['menu']) && $_GET['menu'] === 'pbxadmin') ||
     (isset($_POST['menu']) && $_POST['menu'] === 'pbxadmin') ||
     (isset($_SERVER['SCRIPT_NAME']) && $_SERVER['SCRIPT_NAME'] === '/index.php'));
if ($callflowhooks_embedded || (!defined('CFH_NATIVE_AUTHORIZED') && isset($_SESSION['issabel_user']))) {
    global $pACL;
    // A framework session can retain AMP admin even when opened without the wrapper.
    // Never use that inherited identity to bypass Issabel privileges.
    if (!isset($_SESSION['issabel_user']) || !isset($pACL) || !is_object($pACL) ||
        !method_exists($pACL, 'hasModulePrivilege') ||
        !$pACL->hasModulePrivilege($_SESSION['issabel_user'], 'pbxadmin', 'callflowhooks')) {
        echo 'Acceso denegado. Abrir CallFlow Hooks desde Configuración PBX de Issabel.';
        return;
    }
}
$callflowhooks_form_url = defined('CFH_NATIVE_AUTHORIZED') ? 'index.php?menu=callflowhooks' :
    ($callflowhooks_embedded ? 'index.php?menu=pbxadmin&display=callflowhooks&type=setup' : 'config.php?display=callflowhooks&type=setup');
if (defined('CFH_NATIVE_AUTHORIZED')) {
    echo '<p>Administrar junto a los IVR en <a href="/index.php?menu=pbxadmin&amp;display=callflowhooks&amp;type=setup">PBX Configuration → Inbound Call Control → CallFlow Hooks</a>.</p>';
}
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
            callflowhooks_resolve_selectors($submitted, $_POST);
            $updating = false;
            foreach ($configuration['profiles'] as $item) {
                if ($item['identifier'] === $submitted['identifier']) $updating = true;
            }
            $configuration = callflowhooks_save($submitted, isset($_POST['configuration_version']) ? $_POST['configuration_version'] : '');
            unset($_SESSION['callflowhooks_draft']);
            $selectedId = $submitted['identifier'];
            echo '<p role="status">'.($updating ? 'Perfil actualizado.' : 'Perfil guardado. En el IVR, seleccionar Custom Destinations → CallFlow Hooks: '.callflowhooks_escape($selectedId).'.').' Pulsar Aplicar cambios en Configuración PBX para regenerar el dialplan.</p>';
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
foreach ($configuration['profiles'] as $profile) {
    if ($selectedId === $profile['identifier']) { $selected = $profile; $editing = true; }
}
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
$showProfileForm = isset($_GET['new']) || isset($_GET['extension']) || $selected !== null || empty($configuration['profiles']);
$newUrl = callflowhooks_escape($callflowhooks_form_url.'&new=1');
echo '<div class="rnav"><ul><li><a href="'.$newUrl.'"'.(!$selected && $showProfileForm ? ' id="current"' : '').'>Nuevo perfil</a></li>';
foreach ($configuration['profiles'] as $profile) {
    echo '<li><a href="'.callflowhooks_escape($callflowhooks_form_url.'&profile='.rawurlencode($profile['identifier'])).'"'.($selected && $selected['identifier'] === $profile['identifier'] ? ' id="current"' : '').'>'.callflowhooks_escape($profile['identifier']).'</a></li>';
}
echo '</ul></div>';
if (!$showProfileForm) {
    echo '<h2>CallFlow Hooks</h2><p>Perfiles de handlers desde IVR</p><p><a href="'.$newUrl.'" class="ui-button ui-widget ui-state-default ui-corner-all">Agregar un nuevo perfil</a></p>';
    echo '<form method="post" action="'.callflowhooks_escape($callflowhooks_form_url).'">';
    callflowhooks_form_hidden($configuration, $callflowhooks_embedded);
    echo '<button name="synchronize" value="1" type="submit" formnovalidate>Sincronizar destinos de .conf</button></form>';
    return;
}
$extensionId = $selected ? $selected['extension'] : (isset($_GET['extension']) && is_string($_GET['extension']) ? $_GET['extension'] : $configuration['extensions'][0]['identifier']);
$extension = null;
foreach ($configuration['extensions'] as $item) {
    if ($item['identifier'] === $extensionId) $extension = $item;
}
if (!$extension) {
    echo '<p role="alert">Seleccionar una extensión instalada.</p><a href="'.$newUrl.'">Nuevo perfil</a>';
    return;
}
echo '<form class="popover-form" method="post" action="'.callflowhooks_escape($callflowhooks_form_url).'">';
callflowhooks_form_hidden($configuration, $callflowhooks_embedded);
echo '<input type="hidden" name="extension" value="'.callflowhooks_escape($extensionId).'">';
echo '<table><tr><td colspan="2"><h2 id="title">'.($editing ? 'Editar perfil: '.callflowhooks_escape($selected['identifier']) : 'Nuevo perfil').'</h2></td></tr>';
callflowhooks_section('Perfil');
echo '<tr><td><label for="callflowhooks-extension">Extensión del handler</label></td><td>';
if ($editing || $draft) {
    echo callflowhooks_escape($extension['title']);
} else {
    $extensionUrl = json_encode($callflowhooks_form_url.'&extension=');
    echo '<select id="callflowhooks-extension" onchange="'.callflowhooks_escape('window.location.href='.$extensionUrl.'+encodeURIComponent(this.value)').'">';
    foreach ($configuration['extensions'] as $item) {
        echo '<option value="'.callflowhooks_escape($item['identifier']).'"'.($item['identifier'] === $extensionId ? ' selected' : '').'>'.callflowhooks_escape($item['title']).'</option>';
    }
    echo '</select>';
}
echo '</td></tr><tr><td><label for="callflowhooks-identifier">Identificador</label><span class="help">?<span>Ejemplo: prueba. Usar una letra minúscula inicial, letras minúsculas, dígitos, guion o guion bajo. El identificador del destino se conserva al editar.</span></span></td><td><input name="identifier" value="'.callflowhooks_escape($selected ? $selected['identifier'] : '').'" id="callflowhooks-identifier" maxlength="40" required'.($editing ? ' readonly' : '').'>';
if (isset($fields['identifier'])) echo '<p role="alert">Identificador: '.callflowhooks_escape($fields['identifier']).'</p>';
echo '</td></tr>';
foreach ($configuration['core_fields'] as $name=>$field) {
    if ($name === 'next_destination') callflowhooks_section('Enrutamiento y ejecución');
    if ($name === 'input_source') callflowhooks_section('Entrada del handler');
    $renderer = in_array($name, array('next_destination', 'fallback_destination'), true) ? 'callflowhooks_destination_field' :
        ($name === 'input_prompt' ? 'callflowhooks_recording_field' : 'callflowhooks_field');
    $renderer($name, $field, $selected ? $selected[$name] : (isset($field['default']) ? $field['default'] : ''), isset($fields[$name]) ? $fields[$name] : '');
}
callflowhooks_section('Opciones de '.$extension['title']);
foreach ($extension['fields'] as $name=>$field) {
    $key = 'settings.'.$name;
    callflowhooks_field('settings['.$name.']', $field, $selected ? $selected['settings'][$name] : (isset($field['default']) ? $field['default'] : ''), isset($fields[$key]) ? $fields[$key] : '');
}
echo '<tr><td colspan="2"><h6><button type="submit">Guardar perfil</button> <button name="synchronize" value="1" type="submit" formnovalidate>Sincronizar destinos de .conf</button>';
if ($draft) echo ' <button name="discard_draft" value="1" type="submit" formnovalidate>Descartar borrador</button>';
echo '</h6></td></tr></table></form>';

callflowhooks_selector_script();
