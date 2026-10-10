<?php
// Simulates only the external distribution bootstrap contract, not our loader.
if (!empty($GLOBALS['request']['bootstrap_failure'])) throw new Exception('database-private-password');
if ($bootstrap_settings['issabelpbx_auth'] !== false || $bootstrap_settings['skip_astman'] !== true ||
    !isset($restrict_mods['customappsreg'], $restrict_mods['callflowhooks'])) {
    throw new Exception('Bootstrap settings rejected by boundary');
}
$db = new stdClass();
$amp_conf = array('AMPASTERISKUSER'=>'asterisk', 'AMPASTERISKGROUP'=>'asterisk');
define('ISSABELPBX_IS_AUTH', true);
require_once dirname(__FILE__).'/pbx_api_boundary.php';
