<?php
/* Issabel API boundary; configuration operations execute the real Python core. */
$request = json_decode(file_get_contents('php://stdin'), true);
define('ISSABELPBX_IS_AUTH', true);
define('CFH_CONFIGURATION_FILE', getenv('CFH_TEST_CONFIG'));
define('CFH_PYTHON_BINARY', getenv('CFH_TEST_PYTHON'));
$GLOBALS['reloads'] = 0;
if (empty($request['missing_active_modules'])) {
    $active_modules = array('ivr'=>array(), 'callflowhooks'=>array(), 'customappsreg'=>array());
}
$destination = 'callflow-profile-welcome,s,1';
$GLOBALS['rows'] = array('unrelated,s,1'=>array('custom_dest'=>'unrelated,s,1', 'description'=>'Unrelated', 'notes'=>'Foreign'));
if (isset($request['row'])) $GLOBALS['rows'][$destination] = $request['row'];
if (empty($request['missing_usage'])) {
    function framework_check_destination_usage($destinations) {
        global $request;
        if (!empty($request['usage_error'])) throw new Exception('private-database-password');
        return isset($request['usage']) ? $request['usage'] : array();
    }
}
if (empty($request['missing_registry'])) {
    function customappsreg_customdests_get($destination) {
        global $request;
        if (!empty($request['registry_error'])) throw new Exception('private-database-password');
        if (!empty($request['registry_malformed'])) return false;
        return isset($GLOBALS['rows'][$destination]) ? $GLOBALS['rows'][$destination] : null;
    }
    function customappsreg_customdests_delete($destination) {
        global $request;
        if (!empty($request['cleanup_error'])) throw new Exception('private-database-password');
        if (!empty($request['cleanup_noop'])) return;
        unset($GLOBALS['rows'][$destination]);
        if (!empty($request['concurrent_edit'])) {
            $before = callflowhooks_backend(array('action'=>'describe'));
            $profile = $before['profiles'][0];
            unset($profile['configured_secrets'], $profile['custom_destination']);
            $profile['display_name'] = 'Concurrent edit';
            callflowhooks_backend(array('action'=>'save', 'profile'=>$profile, 'expected_version'=>$before['configuration_version']));
        }
    }
}
function needreload() { $GLOBALS['reloads']++; }
require_once dirname(__FILE__).'/../module/functions.inc.php';
require_once dirname(__FILE__).'/../module/profile-deletion.php';
try {
    $identifier = isset($request['identifier']) ? $request['identifier'] : 'welcome';
    $result = $request['action'] === 'usage' ? callflowhooks_profile_usage($identifier) :
        callflowhooks_delete($identifier, isset($request['version']) ? $request['version'] : null);
    $response = array('ok'=>true, 'result'=>$result);
} catch (Exception $error) {
    $response = array('ok'=>false, 'error'=>$error->getMessage());
}
$response['rows'] = $GLOBALS['rows'];
$response['reloads'] = $GLOBALS['reloads'];
echo json_encode($response);
