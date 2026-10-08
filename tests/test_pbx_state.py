"""Real PHP diagnostic/synchronization process; only distribution APIs are doubles."""
import json
import os
import pathlib
import shutil
import subprocess
import unittest

from boundary_support import AdminBoundary, ROOT


@unittest.skipUnless(shutil.which('php'), 'PHP required in CI')
class PbxState(AdminBoundary, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.root = pathlib.Path(self.directory.name)
        self.config = self.root/'etc/asterisk/callflow-hooks/profiles.conf'
        self.config.parent.mkdir(parents=True)
        self.core = self.root/'usr/share/callflow-hooks'
        self.core.mkdir(parents=True)
        shutil.copytree(str(ROOT/'module/backend'), str(self.core/'backend'))
        shutil.copytree(str(ROOT/'module/extensions'), str(self.core/'extensions'))
        self.destinations = self.root/'destinations.json'
        self.destinations.write_text('{}')
        bootstrap = self.root/'etc/issabelpbx.conf'
        bootstrap.write_text('''<?php
if ($bootstrap_settings['issabelpbx_auth'] !== false ||
    $bootstrap_settings['skip_astman'] !== ($mode !== 'reload')) throw new Exception('Invalid bootstrap');
if (in_array($mode, array('references','reload')) && $restrict_mods !== false) throw new Exception('Missing modules');
if (in_array($mode, array('synchronize','configuration')) &&
    !isset($restrict_mods['customappsreg'], $restrict_mods['callflowhooks'])) throw new Exception('Missing bridge');
$amp_conf = array('AMPASTERISKUSER'=>'asterisk','AMPASTERISKGROUP'=>'asterisk');
define('ISSABELPBX_IS_AUTH', true);
$boundaryDestinations = json_decode(file_get_contents(getenv('PROBE_DESTINATIONS')), true);
function customappsreg_customdests_get($dest) { global $boundaryDestinations; return isset($boundaryDestinations[$dest]) ? $boundaryDestinations[$dest] : array(); }
function customappsreg_customdests_add($dest, $description, $notes) {
    global $boundaryDestinations; $boundaryDestinations[$dest] = array('custom_dest'=>$dest,'notes'=>$notes);
    file_put_contents(getenv('PROBE_DESTINATIONS'), json_encode($boundaryDestinations)); return true;
}
function customappsreg_customdests_list() { global $boundaryDestinations; return $boundaryDestinations; }
function framework_check_destination_usage($items) { return getenv('PROBE_REFERENCES') ? array('ivr') : array(); }
function needreload() { file_put_contents(getenv('PROBE_RELOAD'), 'pending'); }
function do_reload() { return array('status'=>!getenv('PROBE_RELOAD_FAIL')); }
require getenv('PROBE_BRIDGE');
echo 'database-password-must-not-leak';
''')
        base = self.root/'var/www/html'
        (base/'libs').mkdir(parents=True)
        (base/'configs').mkdir()
        (base/'configs/default.conf.php').write_text("<?php $arrConf = array('issabel_dsn'=>array('menu'=>'menu','acl'=>'acl'));")
        (base/'libs/misc.lib.php').write_text('<?php')
        for filename, source in {
            'paloSantoDB.class.php': 'class paloDB { function __construct($dsn) {} }',
            'paloSantoMenu.class.php': 'class paloMenu { function __construct($db) {} function existeMenu($id) { return $id === "callflowhooks"; } }',
            'paloSantoACL.class.php': 'class paloACL { function __construct($db) {} function getIdResource($id) { return $id === "callflowhooks" ? 12 : false; } }'
        }.items():
            (base/'libs'/filename).write_text('<?php '+source)
        self.environment = dict(os.environ, PROBE_DESTINATIONS=str(self.destinations),
                                PROBE_RELOAD=str(self.root/'reload'),
                                PROBE_BRIDGE=str(ROOT/'module/functions.inc.php'))

    def probe(self, mode, **environment):
        return subprocess.run(['php', str(ROOT/'packaging/pbx-state.php'), mode, str(self.root)],
                              env=dict(self.environment, **environment), stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, universal_newlines=True, timeout=8)

    def test_synchronize_repairs_missing_destinations_and_rejects_invalid_configuration(self):
        self.assertTrue(self.request('save', profile=self.profile(), expected_version=self.request('describe')['configuration_version'])['ok'])
        result = self.probe('configuration')
        self.assertNotEqual(result.returncode, 0, 'Missing destination must fail verification')
        result = self.probe('synchronize')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {'ok': True})
        self.assertTrue((self.root/'reload').exists())
        original = self.config.read_bytes()
        self.assertEqual(self.probe('synchronize').returncode, 0)
        self.assertEqual(self.config.read_bytes(), original)
        self.assertEqual(self.probe('configuration').returncode, 0)
        destinations = json.loads(self.destinations.read_text())
        self.assertEqual(destinations['callflow-profile-welcome,s,1']['notes'], 'Managed by CallFlow Hooks')
        self.config.write_text('[invalid]\nsecret=never-print\n')
        result = self.probe('synchronize')
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('never-print', result.stdout+result.stderr)

    def test_configuration_rejects_foreign_destination_without_overwriting_it(self):
        self.request('save', profile=self.profile(), expected_version=self.request('describe')['configuration_version'])
        self.destinations.write_text(json.dumps({'callflow-profile-welcome,s,1': {'notes':'other owner'}}))
        original = self.destinations.read_bytes()
        for mode in ['synchronize','configuration']:
            self.assertNotEqual(self.probe(mode).returncode, 0)
        self.assertEqual(self.destinations.read_bytes(), original)

    def test_framework_preflight_references_and_reload_use_real_probe(self):
        result = self.probe('preflight')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['user'], 'asterisk')
        self.assertNotIn('database-password', result.stdout+result.stderr)
        self.assertEqual(json.loads(self.probe('framework').stdout), {'menu':True,'acl':True})
        self.request('save', profile=self.profile(), expected_version=self.request('describe')['configuration_version'])
        self.assertEqual(self.probe('synchronize').returncode, 0)
        self.assertTrue(json.loads(self.probe('references', PROBE_REFERENCES='1').stdout)['references'])
        self.assertFalse(json.loads(self.probe('references').stdout)['references'])
        self.assertEqual(json.loads(self.probe('reload').stdout), {'ok':True})
        self.assertNotEqual(self.probe('reload', PROBE_RELOAD_FAIL='1').returncode, 0)
