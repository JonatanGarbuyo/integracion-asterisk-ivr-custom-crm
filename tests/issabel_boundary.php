<?php
/* Issabel/Custom Destinations boundary double, not a substitute for PBX validation. */
$request = json_decode(file_get_contents('php://stdin'), true);
if (empty($request['bootstrap'])) define('ISSABELPBX_IS_AUTH', true);
define('CFH_CONFIGURATION_FILE', getenv('CFH_TEST_CONFIG'));
define('CFH_PYTHON_BINARY', getenv('CFH_TEST_PYTHON'));
define('CFH_PBX_MODULE_DIRECTORY', dirname(__DIR__).'/module');
if (getenv('CFH_TEST_CORE')) define('CFH_CORE_DIRECTORY', getenv('CFH_TEST_CORE'));
class BoundaryUser {
    function checkSection($section) { return !isset($GLOBALS['request']['denied']); }
}
$_SESSION = array('AMP_user' => new BoundaryUser(), 'callflowhooks_csrf' => 'test-token');
$sessionFile = CFH_CONFIGURATION_FILE.'.session';
if (file_exists($sessionFile)) {
    $draft = json_decode(file_get_contents($sessionFile), true);
    if (is_array($draft)) $_SESSION['callflowhooks_draft'] = $draft;
}
$_SERVER['REQUEST_METHOD'] = $request['action'] === 'save' ? 'POST' : 'GET';
$_POST = isset($request['post']) ? $request['post'] : array();
$_SERVER['SCRIPT_NAME'] = '/admin/config.php';
$_GET = array();
if (isset($request['get'])) $_GET = $request['get'];
$registry = CFH_CONFIGURATION_FILE.'.registry';
$destinations = file_exists($registry) ? json_decode(file_get_contents($registry), true) : array();
$reloads = 0;
if (!empty($request['pbx_widgets'])) require dirname(__FILE__).'/pbx_selectors_boundary.php';
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
    if (isset($request['surface']) && in_array($request['surface'], array('embedded', 'framework_direct'), true)) {
        class EmbeddedBoundaryACL {
            function hasModulePrivilege($user, $module, $section) {
                return $user === 'administrator' && $module === 'pbxadmin' && $section === 'callflowhooks' && empty($GLOBALS['request']['framework_denied']);
            }
        }
        $pACL = new EmbeddedBoundaryACL();
        $_SESSION['issabel_user'] = 'administrator';
        if ($request['surface'] === 'embedded') {
            $_SERVER['SCRIPT_NAME'] = '/index.php';
            if (empty($request['post_dispatch'])) $_GET['menu'] = 'pbxadmin';
        }
        if (!empty($request['missing_framework_acl'])) unset($pACL);
    }
    ob_start();
    include dirname(__DIR__).'/module/page.callflowhooks.php';
    $html = ob_get_clean();
}
if (function_exists('callflowhooks_get_config')) callflowhooks_get_config('asterisk');
file_put_contents($registry, json_encode($destinations));
file_put_contents($sessionFile, json_encode(isset($_SESSION['callflowhooks_draft']) ? $_SESSION['callflowhooks_draft'] : null));
echo json_encode(array('html'=>$html, 'destinations'=>$destinations, 'reloads'=>$reloads,
                      'dialplan'=>implode("\n", $ext->lines)));
