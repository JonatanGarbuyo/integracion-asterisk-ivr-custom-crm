<?php
if (!defined('ISSABELPBX_IS_AUTH')) { die('No direct script access allowed'); }
function callflowhooks_message_id($text) {
    static $legacy = null;
    if ($legacy === null) $legacy = require dirname(__FILE__).'/i18n/messages.php';
    if (isset($legacy[$text])) return $legacy[$text];
    if (preg_match('/^Ingresar texto de hasta ([0-9]+) caracteres\.$/D', $text, $parts)) return sprintf('Enter text up to %s characters.', $parts[1]);
    if (preg_match('/^Ingresar un número entero entre (-?[0-9]+) y (-?[0-9]+)\.$/D', $text, $parts)) return sprintf('Enter an integer between %s and %s.', $parts[1], $parts[2]);
    return $text;
}
function callflowhooks_text($text) {
    $msgid = callflowhooks_message_id($text);
    $patterns = array('/^Enter text up to ([0-9]+) characters\.$/D'=>'Enter text up to %s characters.', '/^Enter an integer between (-?[0-9]+) and (-?[0-9]+)\.$/D'=>'Enter an integer between %s and %s.', '/^Enter seconds between ([0-9.]+) and ([0-9.]+), with up to three decimal places\.$/D'=>'Enter seconds between %s and %s, with up to three decimal places.');
    foreach ($patterns as $pattern=>$template) if (preg_match($pattern, $msgid, $parts)) {
        array_shift($parts);
        return vsprintf(callflowhooks_text($template), $parts);
    }
    if (class_exists('modgettext') && is_callable(array('modgettext', '_'))) return modgettext::_($msgid, 'callflowhooks');
    // PBX selects the locale. Never set a locale or language cookie here.
    if (function_exists('dgettext')) {
        bindtextdomain('callflowhooks', dirname(__FILE__).'/i18n');
        bind_textdomain_codeset('callflowhooks', 'UTF-8');
        return dgettext('callflowhooks', $msgid);
    }
    return $msgid;
}
