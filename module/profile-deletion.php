<?php
if (!defined('ISSABELPBX_IS_AUTH')) { die('No direct script access allowed'); }

function callflowhooks_profile_destination($identifier) {
    if (!is_string($identifier) || !preg_match('/^[a-z][a-z0-9_-]{0,39}$/D', $identifier)) {
        throw new callflowhooks_backend_error('Invalid profile identifier.');
    }
    return 'callflow-profile-'.$identifier.',s,1';
}

function callflowhooks_profile_lookup($identifier, $configuration) {
    if (!isset($configuration['profiles']) || !is_array($configuration['profiles'])) {
        throw new callflowhooks_backend_error('Profile not found.');
    }
    foreach ($configuration['profiles'] as $profile) {
        if (isset($profile['identifier']) && $profile['identifier'] === $identifier) return $profile;
    }
    throw new callflowhooks_backend_error('Profile not found.');
}

function callflowhooks_collect_profile_usage($identifier, $configuration) {
    global $active_modules;
    $destination = callflowhooks_profile_destination($identifier);
    callflowhooks_profile_lookup($identifier, $configuration);
    $failure = 'Destination usage cannot be checked; profile deletion is unavailable.';
    if (!function_exists('framework_check_destination_usage') || !is_array($active_modules) || !$active_modules) {
        throw new callflowhooks_backend_error($failure);
    }
    try { $native = framework_check_destination_usage(array($destination)); }
    catch (Exception $error) { throw new callflowhooks_backend_error($failure); }
    catch (Throwable $error) { throw new callflowhooks_backend_error($failure); }
    if (!is_array($native)) throw new callflowhooks_backend_error($failure);
    $usage = array();
    foreach ($native as $module=>$items) {
        if (!is_string($module) || !is_array($items)) throw new callflowhooks_backend_error($failure);
        foreach ($items as $item) {
            if (!is_array($item) || !isset($item['dest'], $item['description']) ||
                !is_string($item['dest']) || !is_string($item['description']) ||
                $item['dest'] !== $destination ||
                (isset($item['edit_url']) && !is_string($item['edit_url']))) {
                throw new callflowhooks_backend_error($failure);
            }
            $usage[] = array('dest'=>$item['dest'], 'description'=>$item['description'],
                             'edit_url'=>isset($item['edit_url']) ? $item['edit_url'] : '');
        }
    }
    // Include manually edited profiles even if the PBX bridge is not present in
    // active_modules. Runtime validation currently rejects profile-to-profile
    // routes; this scan also protects future extensions of that contract.
    foreach ($configuration['profiles'] as $profile) {
        foreach (array('next_destination', 'fallback_destination') as $field) {
            if (!isset($profile[$field]) || $profile[$field] !== $destination) continue;
            $name = isset($profile['display_name']) ? $profile['display_name'] : $profile['identifier'];
            $label = isset($configuration['core_fields'][$field]['label']) ?
                $configuration['core_fields'][$field]['label'] : $field;
            $usage[] = array('dest'=>$destination, 'description'=>'CallFlow Hooks: '.$name.' / '.callflowhooks_text($label),
                            'edit_url'=>'config.php?display=callflowhooks&profile='.rawurlencode($profile['identifier']));
        }
    }
    // Some distributions also expose our direct scan through the registry.
    $unique = array();
    foreach ($usage as $item) $unique[serialize($item)] = $item;
    return array_values($unique);
}

function callflowhooks_profile_usage($identifier) {
    callflowhooks_profile_destination($identifier);
    return callflowhooks_collect_profile_usage($identifier, callflowhooks_backend(array('action'=>'describe')));
}

function callflowhooks_legacy_profile_destination($destination) {
    $failure = 'Custom Destinations is unavailable; the profile was not deleted.';
    if (!function_exists('customappsreg_customdests_get')) throw new callflowhooks_backend_error($failure);
    try { $row = customappsreg_customdests_get($destination); }
    catch (Exception $error) { throw new callflowhooks_backend_error($failure); }
    catch (Throwable $error) { throw new callflowhooks_backend_error($failure); }
    // PEAR DB getRow returns null for no match; historical boundaries use [].
    if ($row === null || $row === array()) return null;
    if (!is_array($row)) throw new callflowhooks_backend_error($failure);
    if (!is_array($row) || !isset($row['custom_dest'], $row['notes']) ||
        $row['custom_dest'] !== $destination || $row['notes'] !== 'Managed by CallFlow Hooks') {
        throw new callflowhooks_backend_error('The profile destination is owned by another configuration.');
    }
    return $row;
}

function callflowhooks_delete($identifier, $version) {
    $destination = callflowhooks_profile_destination($identifier);
    if (!function_exists('needreload')) {
        throw new callflowhooks_backend_error('Custom Destinations is unavailable; the profile was not deleted.');
    }
    $configuration = callflowhooks_backend(array('action'=>'describe'));
    callflowhooks_profile_lookup($identifier, $configuration);
    if (!is_string($version) || !isset($configuration['configuration_version']) ||
        $version !== $configuration['configuration_version']) {
        throw new callflowhooks_backend_error('Configuration changed; reload before deleting the profile.');
    }
    // Recheck server-side on POST: a prior confirmation page cannot authorize
    // deletion after another PBX object starts using this destination.
    if (callflowhooks_collect_profile_usage($identifier, $configuration)) {
        throw new callflowhooks_backend_error('This profile is still used by other PBX objects.');
    }
    $row = callflowhooks_legacy_profile_destination($destination);
    if ($row !== null) {
        $failure = 'The profile destination could not be removed; the profile was not deleted.';
        if (!function_exists('customappsreg_customdests_delete')) throw new callflowhooks_backend_error($failure);
        try {
            // Native delete returns void, so its result cannot establish success.
            customappsreg_customdests_delete($destination);
            if (callflowhooks_legacy_profile_destination($destination) !== null) {
                throw new callflowhooks_backend_error($failure);
            }
        } catch (Exception $error) { throw new callflowhooks_backend_error($failure); }
        catch (Throwable $error) { throw new callflowhooks_backend_error($failure); }
    }
    // Cleanup precedes the atomic/versioned .conf deletion. If it rejects a
    // concurrent edit or fails, the profile and its native destination provider
    // remain intact; only a redundant managed legacy registry row may be gone.
    // There is no unsafe rollback from redacted form data or a claimed DB/file
    // transaction spanning Issabel and the local configuration.
    $result = callflowhooks_backend(array('action'=>'delete', 'identifier'=>$identifier, 'expected_version'=>$version));
    if (!isset($result['profiles']) || !is_array($result['profiles'])) {
        throw new callflowhooks_backend_error('The profile deletion result could not be verified.');
    }
    foreach ($result['profiles'] as $profile) {
        if (isset($profile['identifier']) && $profile['identifier'] === $identifier) {
            throw new callflowhooks_backend_error('The profile deletion result could not be verified.');
        }
    }
    needreload();
    return $result;
}
