<?php
/**
 * Security Enhancements
 * 
 * @package Organium-Child
 */

/**
 * Disable XML-RPC to prevent brute force attacks
 */
add_filter('xmlrpc_enabled', '__return_false');

/**
 * Block User Enumeration
 * Prevents /?author=1 scans and WP JSON API user listing
 */
function organium_child_block_user_enumeration($endpoints) {
    if (!is_user_logged_in()) {
        if (isset($endpoints['/wp/v2/users'])) {
            unset($endpoints['/wp/v2/users']);
        }
        if (isset($endpoints['/wp/v2/users/(?P<id>[\d]+)'])) {
            unset($endpoints['/wp/v2/users/(?P<id>[\d]+)']);
        }
    }
    return $endpoints;
}
add_filter('rest_endpoints', 'organium_child_block_user_enumeration');

function organium_child_block_author_query($query_vars) {
    if (isset($query_vars['author']) && !empty($query_vars['author']) && !is_admin() && !is_user_logged_in()) {
        wp_safe_redirect(home_url());
        exit;
    }
    return $query_vars;
}
add_filter('request', 'organium_child_block_author_query');

/**
 * Remove WP Version
 * Obfuscation to make targeted attacks slightly harder
 */
remove_action('wp_head', 'wp_generator');
add_filter('the_generator', '__return_empty_string');
