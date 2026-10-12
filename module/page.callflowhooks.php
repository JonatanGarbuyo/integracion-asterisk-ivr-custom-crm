<?php
if (!defined('ISSABELPBX_IS_AUTH')) { die('No direct script access allowed'); }
if (!defined('CFH_NATIVE_AUTHORIZED') && (!isset($_SESSION['AMP_user']) || !is_object($_SESSION['AMP_user']) ||
    !$_SESSION['AMP_user']->checkSection('callflowhooks'))) {
    echo callflowhooks_escape(callflowhooks_text('Access denied'));
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
        echo callflowhooks_escape(callflowhooks_text('Access denied. Open CallFlow Hooks through Issabel PBX Configuration.'));
        return;
    }
}
$callflowhooks_form_url = defined('CFH_NATIVE_AUTHORIZED') ? 'index.php?menu=callflowhooks' :
    ($callflowhooks_embedded ? 'index.php?menu=pbxadmin&display=callflowhooks&type=setup' : 'config.php?display=callflowhooks&type=setup');
if (defined('CFH_NATIVE_AUTHORIZED')) {
    echo '<p>'.callflowhooks_escape(callflowhooks_text('Manage profiles together with IVRs in PBX Configuration.')).' <a href="/index.php?menu=pbxadmin&amp;display=callflowhooks&amp;type=setup">PBX Configuration → Inbound Call Control → CallFlow Hooks</a>.</p>';
}
try {
    if (!isset($_SESSION['callflowhooks_csrf'])) {
        $strong = false;
        $random = openssl_random_pseudo_bytes(32, $strong);
        if (!$random || !$strong) throw new callflowhooks_backend_error(callflowhooks_text('Could not create the form token.'));
        $_SESSION['callflowhooks_csrf'] = bin2hex($random);
    }
    $configuration = callflowhooks_backend(array('action'=>'describe'));
} catch (Exception $error) {
    $message = $error instanceof callflowhooks_backend_error ? $error->getMessage() : callflowhooks_text('Could not load the configuration.');
    echo '<p role="alert">'.callflowhooks_escape(callflowhooks_text($message)).'</p><p><a href="'.$callflowhooks_form_url.('">'.callflowhooks_escape(callflowhooks_text('Retry')).'</a></p>');
    return;
}
$selectedId = isset($_GET['profile']) && is_string($_GET['profile']) ? $_GET['profile'] : null;
$showDraft = !isset($_GET['new']) && !isset($_GET['extension']);
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $submitted = null;
    $extension = null;
    try {
        if (!isset($_POST['csrf_token']) || !is_string($_POST['csrf_token']) ||
            $_POST['csrf_token'] !== $_SESSION['callflowhooks_csrf']) throw new callflowhooks_backend_error(callflowhooks_text('The form has expired. Reload the page.'));
        if (isset($_POST['discard_draft'])) {
            unset($_SESSION['callflowhooks_draft']);
            $selectedId = isset($_POST['identifier']) && is_string($_POST['identifier']) ? $_POST['identifier'] : null;
            echo ('<p>'.callflowhooks_escape(callflowhooks_text('Draft discarded. Saved configuration is preserved.')).'</p>');
        } elseif (isset($_POST['delete_profile'])) {
            $selectedId = isset($_POST['identifier']) && is_string($_POST['identifier']) ? $_POST['identifier'] : null;
            $showDraft = false;
            if (!isset($_POST['confirm_delete']) || $_POST['confirm_delete'] !== '1') throw new callflowhooks_backend_error('Confirm profile deletion before continuing.');
            $deleteId = isset($_POST['identifier']) && is_string($_POST['identifier']) ? $_POST['identifier'] : '';
            $configuration = callflowhooks_delete($deleteId, isset($_POST['configuration_version']) ? $_POST['configuration_version'] : '');
            if (isset($_SESSION['callflowhooks_draft']['profile']['identifier']) && $_SESSION['callflowhooks_draft']['profile']['identifier'] === $deleteId) unset($_SESSION['callflowhooks_draft']);
            $selectedId = null;
            $showDraft = false;
            echo '<p role="status">'.callflowhooks_escape(callflowhooks_text('Profile deleted.')).'</p>';
        } elseif (isset($_POST['synchronize'])) {
            foreach ($configuration['profiles'] as $item) callflowhooks_register($item['identifier']);
            needreload();
            echo ('<p>'.callflowhooks_escape(callflowhooks_text('Destinations synchronized.')).'</p>');
        } else {
            foreach ($configuration['extensions'] as $item) {
                if (isset($_POST['extension']) && $item['identifier'] === $_POST['extension']) $extension = $item;
            }
            if (!$extension) throw new callflowhooks_backend_error(callflowhooks_text('Select an installed handler extension.'));
            $submitted = callflowhooks_post_fields($configuration['core_fields'], $_POST);
            $submitted['identifier'] = isset($_POST['identifier']) ? $_POST['identifier'] : '';
            $submitted['extension'] = $extension['identifier'];
            $submitted['settings'] = callflowhooks_post_fields($extension['fields'], isset($_POST['settings']) && is_array($_POST['settings']) ? $_POST['settings'] : array());
            if (!isset($_POST['display_name']) || !is_string($_POST['display_name']) || trim($_POST['display_name']) === '') throw new callflowhooks_backend_error('Required field.', array('display_name'=>'Required field.'));
            callflowhooks_resolve_selectors($submitted, $_POST);
            callflowhooks_post_seconds($submitted, $_POST, $configuration['core_fields']);
            $updating = false;
            foreach ($configuration['profiles'] as $item) {
                if ($item['identifier'] === $submitted['identifier']) $updating = true;
            }
            $configuration = callflowhooks_save($submitted, isset($_POST['configuration_version']) ? $_POST['configuration_version'] : '');
            unset($_SESSION['callflowhooks_draft']);
            $selectedId = $submitted['identifier'];
            echo '<p role="status">'.callflowhooks_escape($updating ? callflowhooks_text('Profile updated.') : sprintf(callflowhooks_text('Profile saved. In the IVR, select CallFlow Hooks → %s.'),$submitted['display_name'] ? $submitted['display_name'] : $selectedId)).'</p>';
        }
    } catch (Exception $error) {
        $message = $error instanceof callflowhooks_backend_error ? $error->getMessage() : callflowhooks_text('Could not complete the PBX operation. Check the server log.');
        if ($submitted !== null && $extension !== null) {
            $draft = callflowhooks_public_draft($submitted, $configuration['core_fields'], $extension);
            $draft['seconds'] = array();
            foreach (array('execution_budget_ms', 'input_timeout_ms') as $timeField) if (isset($_POST[str_replace('_ms', '_seconds', $timeField)])) $draft['seconds'][$timeField] = callflowhooks_draft_value($_POST[str_replace('_ms', '_seconds', $timeField)]);
            $draft['error'] = $message;
            $draft['fields'] = $error instanceof callflowhooks_backend_error ? $error->fields : array();
            $_SESSION['callflowhooks_draft'] = $draft;
            $selectedId = $draft['profile']['identifier'];
            $showDraft = true;
        } else echo '<p role="alert">'.callflowhooks_escape(callflowhooks_text($message)).'</p>';
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
    echo '<p role="alert">'.callflowhooks_escape(callflowhooks_text($draft['error'])).('</p><p>'.callflowhooks_escape(callflowhooks_text('Draft recovered. Correct the fields and save again.')).'</p>');
    if ($draft['secret_retry']) echo ('<p>'.callflowhooks_escape(callflowhooks_text('Re-enter any credentials you changed; they are not retained in the draft.')).'</p>');
} else $draft = null;
$showProfileForm = isset($_GET['new']) || isset($_GET['extension']) || $selected !== null || empty($configuration['profiles']);
$newUrl = callflowhooks_escape($callflowhooks_form_url.'&new=1');
echo '<div class="rnav"><ul><li><a href="'.$newUrl.'"'.(!$selected && $showProfileForm ? ' id="current"' : '').('>'.callflowhooks_escape(callflowhooks_text('New Profile')).'</a></li>');
foreach ($configuration['profiles'] as $profile) {
    echo '<li><a href="'.callflowhooks_escape($callflowhooks_form_url.'&profile='.rawurlencode($profile['identifier'])).'"'.($selected && $selected['identifier'] === $profile['identifier'] ? ' id="current"' : '').'>'.callflowhooks_escape($profile['display_name']).'</a></li>';
}
echo '</ul></div>';
if (!$showProfileForm) {
    echo ('<h2>CallFlow Hooks</h2><p>'.callflowhooks_escape(callflowhooks_text('IVR handler profiles')).'</p><p><a href="').$newUrl.('" class="ui-button ui-widget ui-state-default ui-corner-all">'.callflowhooks_escape(callflowhooks_text('Add a new profile')).'</a></p>');
    echo '<form method="post" action="'.callflowhooks_escape($callflowhooks_form_url).'">';
    callflowhooks_form_hidden($configuration, $callflowhooks_embedded);
    echo ('<button name="synchronize" value="1" type="submit" formnovalidate>'.callflowhooks_escape(callflowhooks_text('Synchronize destinations from .conf')).'</button></form>');
    return;
}
$extensionId = $selected ? $selected['extension'] : (isset($_GET['extension']) && is_string($_GET['extension']) ? $_GET['extension'] : $configuration['extensions'][0]['identifier']);
$extension = null;
foreach ($configuration['extensions'] as $item) {
    if ($item['identifier'] === $extensionId) $extension = $item;
}
if (!$extension) {
    echo ('<p role="alert">'.callflowhooks_escape(callflowhooks_text('Select an installed handler extension.')).'</p><a href="').$newUrl.('">'.callflowhooks_escape(callflowhooks_text('New Profile')).'</a>');
    return;
}
try { $profileIdentifier = $selected ? $selected['identifier'] : callflowhooks_new_identifier(); }
catch (Exception $error) { echo '<p role="alert">'.callflowhooks_escape(callflowhooks_text('Could not create the profile. Reload the page.')).'</p>'; return; }
$usage = null;
if ($editing) {
    try { $usage = callflowhooks_profile_usage($selected['identifier']); }
    catch (Exception $error) { $usage = null; }
}
echo '<table><tr><td colspan="2"><h2 id="title">'.($editing ? callflowhooks_escape(sprintf(callflowhooks_text('Edit Profile: %s'), (isset($selected['display_name']) && $selected['display_name'] !== '' ? $selected['display_name'] : $selected['identifier']))) : callflowhooks_escape(callflowhooks_text('New Profile'))).'</h2></td></tr>';
if ($editing) {
    echo '<tr><td colspan="2">';
    if ($usage === null) echo '<p role="alert">'.callflowhooks_escape(callflowhooks_text('Destination usage could not be verified. Deletion is disabled.')).'</p>';
    else {
        echo callflowhooks_escape(sprintf(callflowhooks_text('Used as Destination by %s Object(s)'),count($usage)));
        if ($usage) {
            echo '<span class="help">?<span>'.callflowhooks_escape(callflowhooks_text('References must be removed before deleting this profile.')).'<ul>';
            foreach ($usage as $reference) {
                $description = html_entity_decode($reference['description'], ENT_QUOTES, 'UTF-8');
                $url = isset($reference['edit_url']) ? $reference['edit_url'] : '';
                echo '<li>';
                if (is_string($url) && preg_match('~^(?:config\.php|index\.php)\?[^\x00-\x20\x7f]*$~D', $url) && strpos($url, '\\') === false) echo '<a href="'.callflowhooks_escape($url).'">'.callflowhooks_escape($description).'</a>';
                else echo callflowhooks_escape($description);
                echo '</li>';
            }
            echo '</ul></span></span>';
        }
    }
    echo '</td></tr><tr><td colspan="2">';
    $deleteLabel = callflowhooks_escape(callflowhooks_text('Delete Profile'));
    $deleteIcon = '<img width="16" height="16" src="/admin/images/core_delete.png" alt="'.$deleteLabel.'"> ';
    echo '<form id="callflowhooks-delete-confirmation" method="post" action="'.callflowhooks_escape($callflowhooks_form_url).'">';
    callflowhooks_form_hidden($configuration, $callflowhooks_embedded);
    echo '<input type="hidden" name="identifier" value="'.callflowhooks_escape($selected['identifier']).'">';
    echo '<p><label><input type="checkbox" name="confirm_delete" value="1" required'.($usage === null || $usage ? ' disabled' : '').'> '.callflowhooks_escape(callflowhooks_text('Confirm deletion of this profile. This removes its configuration and credentials.')).'</label></p>';
    echo '<button name="delete_profile" value="1" type="submit"'.($usage === null || $usage ? ' disabled' : '').'>'.$deleteIcon.$deleteLabel.'</button></form>';
    echo '</td></tr>';
}
echo '<tr><td colspan="2"><hr></td></tr></table>';
echo '<form class="popover-form" method="post" action="'.callflowhooks_escape($callflowhooks_form_url).'">';
callflowhooks_form_hidden($configuration, $callflowhooks_embedded);
echo '<input type="hidden" name="extension" value="'.callflowhooks_escape($extensionId).'"><input type="hidden" name="identifier" value="'.callflowhooks_escape($profileIdentifier).'">';
echo '<table>';
callflowhooks_section(callflowhooks_text('Profile'));
echo ('<tr><td><label for="callflowhooks-extension">'.callflowhooks_escape(callflowhooks_text('Handler Extension')).'</label></td><td>');
if ($editing || $draft) {
    echo callflowhooks_escape(callflowhooks_text($extension['title']));
} else {
    $extensionUrl = json_encode($callflowhooks_form_url.'&extension=');
    echo '<select id="callflowhooks-extension" onchange="'.callflowhooks_escape('window.location.href='.$extensionUrl.'+encodeURIComponent(this.value)').'">';
    foreach ($configuration['extensions'] as $item) {
        echo '<option value="'.callflowhooks_escape($item['identifier']).'"'.($item['identifier'] === $extensionId ? ' selected' : '').'>'.callflowhooks_escape(callflowhooks_text($item['title'])).'</option>';
    }
    echo '</select>';
}
echo '</td></tr>';
if (isset($fields['identifier'])) echo '<tr><td colspan="2"><p role="alert">'.callflowhooks_escape(callflowhooks_text($fields['identifier'])).'</p></td></tr>';
foreach ($configuration['core_fields'] as $name=>$field) {
    if ($name === 'display_name') { $field['label'] = 'Name'; $field['required'] = true; $field['help'] = 'Name shown in profile lists and IVR destinations. Renaming preserves existing call references.'; }
    if ($name === 'next_destination') callflowhooks_section(callflowhooks_text('Routing and Execution'));
    if ($name === 'input_source') callflowhooks_section(callflowhooks_text('Handler Input'));
    $renderer = in_array($name, array('next_destination', 'fallback_destination'), true) ? 'callflowhooks_destination_field' :
        ($name === 'input_prompt' ? 'callflowhooks_recording_field' : 'callflowhooks_field');
    if (in_array($name, array('execution_budget_ms', 'input_timeout_ms'), true)) {
        callflowhooks_seconds_field($name, $field, $selected && isset($selected[$name]) ? $selected[$name] : $field['default'], isset($fields[$name]) ? $fields[$name] : '', $draft && isset($draft['seconds'][$name]) ? $draft['seconds'][$name] : null);
        continue;
    }
    $renderer($name, $field, $selected && isset($selected[$name]) ? $selected[$name] : (isset($field['default']) ? $field['default'] : ''), isset($fields[$name]) ? $fields[$name] : '');
}
callflowhooks_section(sprintf(callflowhooks_text('Handler Options: %s'),callflowhooks_text($extension['title'])));
foreach ($extension['fields'] as $name=>$field) {
    if ($extension['identifier'] === 'example' && $name === 'greeting') { $field['label'] = 'Example handler message'; $field['help'] = 'Text returned in the call context by the example handler. It does not play audio or generate speech.'; }
    $key = 'settings.'.$name;
    callflowhooks_field('settings['.$name.']', $field, $selected ? $selected['settings'][$name] : (isset($field['default']) ? $field['default'] : ''), isset($fields[$key]) ? $fields[$key] : '');
}
echo ('<tr><td colspan="2"><h6><button type="submit">'.callflowhooks_escape(callflowhooks_text('Save Profile')).'</button> <button name="synchronize" value="1" type="submit" formnovalidate>'.callflowhooks_escape(callflowhooks_text('Synchronize destinations from .conf')).'</button>');
if ($draft) echo (' <button name="discard_draft" value="1" type="submit" formnovalidate>'.callflowhooks_escape(callflowhooks_text('Discard Draft')).'</button>');
echo '</h6></td></tr></table></form>';
