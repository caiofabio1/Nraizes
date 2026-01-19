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
 * Block User Enumeration via Author Archives
 *
 * Prevents attackers from enumerating users by scanning ?author=ID or ?author_name=admin.
 * Redirects to homepage if an author archive is requested.
 *
 * Priority 5 is used to run before redirect_canonical (priority 10) which would
 * otherwise redirect ?author=1 to /author/name/ revealing the username.
 */
add_action('template_redirect', 'nraizes_block_user_enumeration', 5);
function nraizes_block_user_enumeration() {
    // Check for ?author=N enumeration
    $author_id = isset($_GET['author']) ? $_GET['author'] : false;
    if ($author_id && is_numeric($author_id)) {
        wp_safe_redirect(home_url());
        exit;
    }

    // Check for ?author_name=admin enumeration
    $author_name = isset($_GET['author_name']) ? $_GET['author_name'] : false;
    if ($author_name && is_string($author_name)) {
        wp_safe_redirect(home_url());
        exit;
    }
}
