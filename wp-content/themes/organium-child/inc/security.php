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
 *
 * Prevents attackers from fishing for usernames by requesting /?author=n
 * Runs at priority 5 to intercept before redirect_canonical (priority 10)
 */
add_action('template_redirect', 'organium_child_block_user_enumeration', 5);
function organium_child_block_user_enumeration() {
    if (is_admin()) {
        return;
    }

    // Block ?author=n style requests
    if (isset($_GET['author']) && is_numeric($_GET['author'])) {
        wp_redirect(home_url());
        exit;
    }
}

/**
 * Add Security Headers
 */
add_action('send_headers', 'organium_child_security_headers');
function organium_child_security_headers() {
    if (!is_admin()) {
        header('X-Content-Type-Options: nosniff');
        header('X-Frame-Options: SAMEORIGIN');
        header('X-XSS-Protection: 1; mode=block');
        header('Referrer-Policy: strict-origin-when-cross-origin');
    }
}
