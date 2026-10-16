<?php
// Loaded by the Issabel framework; direct requests must never bootstrap PBX.
if (!isset($GLOBALS['pACL']) || !is_object($GLOBALS['pACL'])) {
    die('Acceso denegado');
}

function _moduleContent(&$smarty, $module_name) {
    global $pACL;
    if ($module_name !== 'callflowhooks' || !isset($_SESSION['issabel_user'], $_SESSION['issabel_pass']) ||
        !$pACL->authenticateUser($_SESSION['issabel_user'], $_SESSION['issabel_pass']) ||
        !$pACL->isUserAuthorized($_SESSION['issabel_user'], 'access', 'callflowhooks')) {
        return 'Acceso denegado';
    }
    require_once dirname(__FILE__).'/libs/pbx.php';
    try {
        callflowhooks_load_pbx();
    } catch (Exception $error) {
        return '<p role="alert">No se pudo cargar el puente IssabelPBX. Revisar instalación y permisos.</p>';
    }
    if (!defined('CFH_NATIVE_AUTHORIZED')) define('CFH_NATIVE_AUTHORIZED', true);
    $callflowhooks_form_url = 'index.php?menu=callflowhooks';
    ob_start();
    include (defined('CFH_PBX_MODULE_DIRECTORY') ? CFH_PBX_MODULE_DIRECTORY : '/var/www/html/admin/modules/callflowhooks').'/page.callflowhooks.php';
    return ob_get_clean();
}
