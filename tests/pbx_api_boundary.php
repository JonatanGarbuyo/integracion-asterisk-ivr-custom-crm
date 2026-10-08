<?php
/* IssabelPBX API boundary; the addon's bootstrap and PHP probes execute normally. */
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
