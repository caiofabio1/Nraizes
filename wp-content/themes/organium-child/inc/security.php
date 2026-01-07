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
 * Block user enumeration scans (e.g. /?author=1)
 */
function organium_child_block_user_enumeration() {
    if (is_admin()) {
        return;
    }

    $author_by_id = (isset($_GET['author']) && is_numeric($_GET['author']));

    if ($author_by_id) {
        wp_redirect(home_url(), 301);
        exit;
    }
}
add_action('template_redirect', 'organium_child_block_user_enumeration', 5);

/**
 * Add HTTP security headers
 */
function organium_child_add_security_headers() {
    if (is_admin()) {
        return;
    }

    header('X-Content-Type-Options: nosniff');
    header('X-Frame-Options: SAMEORIGIN');
    header('X-XSS-Protection: 1; mode=block');
    header('Referrer-Policy: strict-origin-when-cross-origin');
}
add_action('send_headers', 'organium_child_add_security_headers');

/**
 * Hide WordPress version
 */
remove_action('wp_head', 'wp_generator');
