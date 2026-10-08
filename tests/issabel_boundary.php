<?php
/* Issabel/Custom Destinations boundary double, not a substitute for PBX validation. */
$request = json_decode(file_get_contents('php://stdin'), true);
if (empty($request['bootstrap'])) define('ISSABELPBX_IS_AUTH', true);
define('CFH_CONFIGURATION_FILE', getenv('CFH_TEST_CONFIG'));
define('CFH_PYTHON_BINARY', getenv('CFH_TEST_PYTHON'));
define('CFH_PBX_MODULE_DIRECTORY', dirname(__DIR__).'/module');
class BoundaryUser {
    function checkSection($section) { return !isset($GLOBALS['request']['denied']); }
}
$_SESSION = array('AMP_user' => new BoundaryUser(), 'callflowhooks_csrf' => 'test-token');
$_SERVER['REQUEST_METHOD'] = $request['action'] === 'save' ? 'POST' : 'GET';
$_POST = isset($request['post']) ? $request['post'] : array();
$_GET = array();
if (isset($request['get'])) $_GET = $request['get'];
$registry = CFH_CONFIGURATION_FILE.'.registry';
$destinations = file_exists($registry) ? json_decode(file_get_contents($registry), true) : array();
$reloads = 0;
if (empty($request['bootstrap'])) require dirname(__FILE__).'/pbx_api_boundary.php';
else define('CFH_PBX_CONFIGURATION_FILE', dirname(__FILE__).'/pbx_bootstrap_boundary.php');
class BoundaryDialplan {
    public $lines = array();
    function add($context, $extension, $label, $instruction) {
        $this->lines[] = $context.': '.$instruction->output();
    }
}
$ext = new BoundaryDialplan();
if (empty($request['bootstrap'])) require dirname(__DIR__).'/module/functions.inc.php';
if (isset($request['surface']) && $request['surface'] === 'native') {
    class BoundaryACL {
        function authenticateUser($user, $password) { return $password === 'session-password'; }
        function isUserAuthorized($user, $action, $resource) {
            return $action === 'access' && $resource === 'callflowhooks' && empty($GLOBALS['request']['denied']);
        }
    }
    $pACL = new BoundaryACL();
    $_SESSION['issabel_user'] = 'administrator';
    $_SESSION['issabel_pass'] = isset($request['invalid_session']) ? 'bad' : 'session-password';
    $smarty = null;
    require dirname(__DIR__).'/native/index.php';
    $html = _moduleContent($smarty, 'callflowhooks');
} else {
    ob_start();
    include dirname(__DIR__).'/module/page.callflowhooks.php';
    $html = ob_get_clean();
}
if (function_exists('callflowhooks_get_config')) callflowhooks_get_config('asterisk');
file_put_contents($registry, json_encode($destinations));
echo json_encode(array('html'=>$html, 'destinations'=>$destinations, 'reloads'=>$reloads,
                      'dialplan'=>implode("\n", $ext->lines)));
