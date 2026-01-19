<?php
/**
 * Security Enhancements
 * 
 * @package Organium-Child
 */

// Prevent direct access
if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

/**
 * Disable XML-RPC to prevent brute force attacks
 */
add_filter('xmlrpc_enabled', '__return_false');

/**
 * 1. Hide WordPress Version
 * Reduces information leakage to scanners
 */
remove_action('wp_head', 'wp_generator');

/**
 * 2. Block User Enumeration
 * Prevents scanning for usernames via /?author=N
 *
 * Priority 5 to run before redirect_canonical (priority 10)
 */
add_action('template_redirect', 'organium_child_block_user_enumeration', 5);
function organium_child_block_user_enumeration() {
    if (is_author() && isset($_GET['author'])) {
        wp_redirect(home_url());
        exit;
    }
}

/**
 * 3. Disable File Editor (Theme/Plugin)
 * Hardening against compromised admin accounts
 */
if (!defined('DISALLOW_FILE_EDIT')) {
    define('DISALLOW_FILE_EDIT', true);
}

/**
 * 4. Add Security Headers
 * Defense in depth against XSS, Clickjacking, MIME sniffing
 */
add_action('send_headers', 'organium_child_security_headers');
function organium_child_security_headers() {
    if (!is_admin()) {
        header('X-Frame-Options: SAMEORIGIN');
        header('X-Content-Type-Options: nosniff');
        header('Referrer-Policy: strict-origin-when-cross-origin');
    }
}
