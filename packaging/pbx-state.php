<?php
// CLI probe: stdout contains only nonsecret diagnostics, never PBX credentials.
if (PHP_SAPI !== 'cli') die('CLI only');
$mode = isset($argv[1]) ? $argv[1] : '';
$root = isset($argv[2]) ? rtrim($argv[2], '/') : '';
ob_start();
try {
    if (in_array($mode, array('framework', 'retire-native'))) {
        $base = $root.'/var/www/html';
        require_once $base.'/libs/misc.lib.php';
        require $base.'/configs/default.conf.php';
        require_once $base.'/libs/paloSantoDB.class.php';
        require_once $base.'/libs/paloSantoMenu.class.php';
        require_once $base.'/libs/paloSantoACL.class.php';
        $menuDB = new paloDB($arrConf['issabel_dsn']['menu']);
        $aclDB = new paloDB($arrConf['issabel_dsn']['acl']);
        $menu = new paloMenu($menuDB);
        $acl = new paloACL($aclDB);
        if ($mode === 'retire-native') {
            // deleteMenu() also removes ancestors if this is their last child.
            // Retire only this addon's old leaf, leaving PBX and its privileges intact.
            $children = $menuDB->getFirstRowQuery('SELECT COUNT(*) AS N FROM menu WHERE IdParent = ?', true, array('callflowhooks'));
            if (!is_array($children) || $children['N'] != 0) throw new Exception('Unexpected child menus');
            if (!$menuDB->genQuery('DELETE FROM menu WHERE id = ?', array('callflowhooks'))) throw new Exception('Menu retirement failed');
            $resource = $acl->getIdResource('callflowhooks');
            if ($resource !== false && !$acl->deleteIdResource($resource)) throw new Exception('ACL retirement failed');
        }
        $result = array('menu'=>(bool)$menu->existeMenu('callflowhooks'),
                        'acl'=>$acl->getIdResource('callflowhooks') !== false);
        if ($mode === 'retire-native') $result = array('ok'=>!$result['menu'] && !$result['acl']);
    } else {
        $bootstrap_settings = array('issabelpbx_auth'=>false, 'skip_astman'=>$mode !== 'reload', 'issabelpbx_error_handler'=>false);
        // References require every module's destination callbacks, not only ours.
        $restrict_mods = in_array($mode, array('references', 'reload')) ? false :
            (in_array($mode, array('synchronize', 'configuration')) ? array('customappsreg'=>true, 'callflowhooks'=>true) : true);
        if (in_array($mode, array('synchronize', 'configuration', 'references'))) {
            define('CFH_CONFIGURATION_FILE', $root.'/etc/asterisk/callflow-hooks/profiles.conf');
            define('CFH_CORE_DIRECTORY', $root.'/usr/share/callflow-hooks');
        }
        $loaded = false;
        foreach (array('/etc/issabelpbx.conf', '/etc/asterisk/issabelpbx.conf', '/etc/freepbx.conf', '/etc/asterisk/freepbx.conf') as $path) {
            if (is_readable($root.$path)) { require $root.$path; $loaded = true; break; }
        }
        if (!$loaded) throw new Exception('PBX absent');
        $result = array('user'=>$amp_conf['AMPASTERISKUSER'], 'group'=>$amp_conf['AMPASTERISKGROUP'],
                        'web_user'=>isset($amp_conf['AMPASTERISKWEBUSER']) ? $amp_conf['AMPASTERISKWEBUSER'] : $amp_conf['AMPASTERISKUSER'],
                        'php_ok'=>PHP_VERSION_ID >= 50400 && function_exists('openssl_random_pseudo_bytes') && function_exists('proc_open'));
        if (in_array($mode, array('synchronize', 'configuration'))) {
            $configuration = callflowhooks_backend(array('action'=>'describe'));
            foreach ($configuration['profiles'] as $profile) {
                if ($mode === 'synchronize') callflowhooks_register($profile['identifier']);
                $destination = customappsreg_customdests_get('callflow-profile-'.$profile['identifier'].',s,1');
                if ($destination && $destination['notes'] !== 'Managed by CallFlow Hooks') throw new Exception('Destination occupied');
                if (!$destination && !callflowhooks_getdestinfo($profile['custom_destination'])) throw new Exception('Destination absent');
            }
            if ($mode === 'synchronize') needreload();
            $result = array('ok'=>true);
        }
        if ($mode === 'references') {
            $destinations = array();
            $configuration = callflowhooks_backend(array('action'=>'describe'));
            foreach ($configuration['profiles'] as $profile) $destinations[] = $profile['custom_destination'];
            foreach (customappsreg_customdests_list() as $item) {
                if ($item['notes'] === 'Managed by CallFlow Hooks' && preg_match('/^callflow-profile-[a-z][a-z0-9_-]{0,39},s,1$/D', $item['custom_dest'])) $destinations[] = $item['custom_dest'];
            }
            $result['references'] = $destinations ? (bool)framework_check_destination_usage(array_values(array_unique($destinations))) : false;
        }
        if ($mode === 'reload') {
            $reload = do_reload();
            if (empty($reload['status'])) throw new Exception('Reload failed');
            $result = array('ok'=>true);
        }
    }
    ob_end_clean();
    echo json_encode($result)."\n";
} catch (Exception $error) {
    ob_end_clean();
    fwrite(STDERR, "No se pudo comprobar Issabel/PBX\n");
    exit(1);
}
