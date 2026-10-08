<?php
/* Issabel/Custom Destinations boundary double, not a substitute for PBX validation. */
$request = json_decode(file_get_contents('php://stdin'), true);
define('ISSABELPBX_IS_AUTH', true);
define('CFH_CONFIGURATION_FILE', getenv('CFH_TEST_CONFIG'));
define('CFH_PYTHON_BINARY', getenv('CFH_TEST_PYTHON'));
class BoundaryUser {
    function checkSection($section) { return !isset($GLOBALS['request']['denied']); }
}
$_SESSION = array('AMP_user' => new BoundaryUser(), 'callflowhooks_csrf' => 'test-token');
$_SERVER['REQUEST_METHOD'] = $request['action'] === 'save' ? 'POST' : 'GET';
$_POST = isset($request['post']) ? $request['post'] : array();
$_GET = array();
$registry = CFH_CONFIGURATION_FILE.'.registry';
$destinations = file_exists($registry) ? json_decode(file_get_contents($registry), true) : array();
$reloads = 0;
function customappsreg_customdests_get($dest) {
    return isset($GLOBALS['destinations'][$dest]) ? $GLOBALS['destinations'][$dest] : array();
}
function customappsreg_customdests_add($dest, $description, $notes) {
    if (isset($GLOBALS['destinations'][$dest])) return false;
    $GLOBALS['destinations'][$dest] = array('custom_dest'=>$dest, 'description'=>$description, 'notes'=>$notes);
    return true;
}
function customappsreg_customdests_delete($dest) { unset($GLOBALS['destinations'][$dest]); }
function needreload() { $GLOBALS['reloads']++; }
class BoundaryDialplan {
    public $lines = array();
    function add($context, $extension, $label, $instruction) {
        $this->lines[] = $context.': '.$instruction->output();
    }
}
$ext = new BoundaryDialplan();
require dirname(__DIR__).'/module/functions.inc.php';
ob_start();
include dirname(__DIR__).'/module/page.callflowhooks.php';
$html = ob_get_clean();
callflowhooks_get_config('asterisk');
file_put_contents($registry, json_encode($destinations));
echo json_encode(array('html'=>$html, 'destinations'=>$destinations, 'reloads'=>$reloads,
                      'dialplan'=>implode("\n", $ext->lines)));
