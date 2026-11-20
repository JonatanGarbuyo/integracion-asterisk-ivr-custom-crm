<?php
if (!defined('ISSABELPBX_IS_AUTH')) { die('No direct script access allowed'); }
// Remove IVR references first. Keep profiles and credentials for a reinstall.
// No generated dialplan or unrelated Custom Destination is edited here.
foreach (customappsreg_customdests_list() as $destination) {
    if ($destination['notes'] === 'Managed by CallFlow Hooks' &&
        preg_match('/^callflow-profile-[a-z][a-z0-9_-]{0,39},s,1$/D', $destination['custom_dest'])) {
        customappsreg_customdests_delete($destination['custom_dest']);
    }
}
needreload();
