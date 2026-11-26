<?php
/* Shell translation seam: reads the shipped GNU catalog, not a dictionary double. */
class modgettext {
    static function _($message, $module) {
        if (!empty($GLOBALS['request']['unsafe_translation']) && $message === 'New Profile') return '<b>New Profile</b>';
        $language = isset($_COOKIE['lang']) ? $_COOKIE['lang'] : 'en_US';
        $file = dirname(__DIR__).'/module/i18n/'.$language.'/LC_MESSAGES/'.$module.'.mo';
        if (!is_file($file)) return $message;
        // With gettext/locale installed, exercise the actual native GNU binding.
        if (function_exists('dgettext') && setlocale(LC_MESSAGES, $language.'.UTF-8', $language.'.utf8')) {
            bindtextdomain($module, dirname(__DIR__).'/module/i18n');
            bind_textdomain_codeset($module, 'UTF-8');
            return dgettext($module, $message);
        }
        if (getenv('CFH_REQUIRE_GETTEXT') === '1') throw new Exception('Native gettext/locale binding required in this CI job.');
        $data = file_get_contents($file);
        $header = unpack('Vmagic/Vrevision/Vcount/Voriginal/Vtranslated', substr($data, 0, 20));
        for ($index = 0; $index < $header['count']; $index++) {
            $original = unpack('Vlength/Voffset', substr($data, $header['original'] + $index*8, 8));
            if (substr($data, $original['offset'], $original['length']) !== $message) continue;
            $translated = unpack('Vlength/Voffset', substr($data, $header['translated'] + $index*8, 8));
            return substr($data, $translated['offset'], $translated['length']);
        }
        return $message;
    }
}
