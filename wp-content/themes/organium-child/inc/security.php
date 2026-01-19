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
 * Hide WordPress Version
 */
remove_action('wp_head', 'wp_generator');

/**
 * Disable File Editing in Dashboard
 */
if (!defined('DISALLOW_FILE_EDIT')) {
    define('DISALLOW_FILE_EDIT', true);
}

/**
 * Add HTTP Security Headers
 */
add_action('send_headers', 'nraizes_security_headers');
function nraizes_security_headers() {
    if (!is_admin()) {
        header('X-Frame-Options: SAMEORIGIN');
        header('X-XSS-Protection: 1; mode=block');
        header('X-Content-Type-Options: nosniff');
        header('Referrer-Policy: strict-origin-when-cross-origin');
    }
}

/**
 * Block User Enumeration
 */
add_action('template_redirect', 'nraizes_block_user_enumeration');
function nraizes_block_user_enumeration() {
    if (is_admin()) return;

    $author_by_id = (isset($_GET['author']) && is_numeric($_GET['author']));

    if ($author_by_id) {
        wp_redirect(home_url(), 301);
        exit;
    }
}
