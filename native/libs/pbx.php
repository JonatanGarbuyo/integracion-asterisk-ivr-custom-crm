<?php
if (!isset($GLOBALS['pACL']) || !is_object($GLOBALS['pACL'])) die('Acceso denegado');

function callflowhooks_load_pbx() {
    // Match the official Issabel wrapper's bootstrap scope. Load only our bridge
    // and Custom Destinations; keep the outer framework session and ACL intact.
    global $amp_conf, $db, $astman, $issabelpbx_conf, $bootstrap_settings;
    global $restrict_mods, $active_modules, $dirname;
    if (!function_exists('customappsreg_customdests_get')) {
        $bootstrap_settings = array('issabelpbx_auth'=>false, 'skip_astman'=>true,
                                    'issabelpbx_error_handler'=>false);
        $restrict_mods = array('customappsreg'=>true, 'callflowhooks'=>true);
        $loaded = false;
        $paths = defined('CFH_PBX_CONFIGURATION_FILE') ? array(CFH_PBX_CONFIGURATION_FILE) :
                 array('/etc/issabelpbx.conf', '/etc/asterisk/issabelpbx.conf', '/etc/freepbx.conf', '/etc/asterisk/freepbx.conf');
        foreach ($paths as $path) {
            if (is_readable($path)) { require_once $path; $loaded = true; break; }
        }
        if (!$loaded) throw new Exception('Configuración PBX ausente');
    }
    if (!function_exists('customappsreg_customdests_get') || !function_exists('needreload')) {
        throw new Exception('Activar Custom Destinations');
    }
    require_once (defined('CFH_PBX_MODULE_DIRECTORY') ? CFH_PBX_MODULE_DIRECTORY : '/var/www/html/admin/modules/callflowhooks').'/functions.inc.php';
}
