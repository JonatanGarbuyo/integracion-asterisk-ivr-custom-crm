<?php
if (!defined('ISSABELPBX_IS_AUTH')) { die('No direct script access allowed'); }
$directory = '/etc/asterisk/callflow-hooks';
if (!is_dir($directory) && !mkdir($directory, 0700, true)) throw new Exception('No se pudo crear el directorio de configuración');
if (!chmod($directory, 0700)) throw new Exception('No se pudieron establecer permisos');
$configuration = $directory.'/profiles.conf';
if (!file_exists($configuration)) {
    $stream = fopen($configuration, 'x');
    if (!$stream) throw new Exception('No se pudo crear la configuración');
    fclose($stream);
}
chmod($configuration, 0600);
chmod(dirname(__FILE__).'/backend/entry.py', 0755);
// Module Administration normally runs as the PBX service user. Root installs
// must explicitly assign that same owner before using the web form (lab guide).
require_once dirname(__FILE__).'/functions.inc.php';
$configuration = callflowhooks_backend(array('action'=>'describe'));
foreach ($configuration['profiles'] as $profile) callflowhooks_register($profile['identifier']);
needreload();
