<?php
/**
 * Security Enhancements
 * 
 * @package Organium-Child
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

/**
 * Disable XML-RPC to prevent brute force attacks
 */
add_filter('xmlrpc_enabled', '__return_false');

/**
 * Remove WordPress version from head and feeds
 */
function nraizes_remove_wp_version() {
    return '';
}
add_filter('the_generator', 'nraizes_remove_wp_version');

/**
 * Disable file editor in dashboard
 *
 * Prevents editing of theme/plugin files from the admin dashboard
 * (defense in depth in case of admin account compromise).
 */
if (!defined('DISALLOW_FILE_EDIT')) {
    define('DISALLOW_FILE_EDIT', true);
}

/**
 * Block user enumeration scans
 *
 * Redirects ?author=N queries to home to prevent enumerating usernames.
 */
function nraizes_block_user_enumeration() {
    if (!is_admin() && isset($_SERVER['QUERY_STRING']) && preg_match('/(?:^|[?&])author=\d+/', $_SERVER['QUERY_STRING'])) {
        wp_redirect(home_url(), 301);
        exit;
    }
}
add_action('init', 'nraizes_block_user_enumeration');

/**
 * Add HTTP security headers
 */
function nraizes_security_headers() {
    if (!headers_sent()) {
        header('X-Content-Type-Options: nosniff');
        header('X-Frame-Options: SAMEORIGIN');
        header('Referrer-Policy: strict-origin-when-cross-origin');
    }
}
add_action('send_headers', 'nraizes_security_headers');
