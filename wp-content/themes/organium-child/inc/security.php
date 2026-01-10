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
 * Block user enumeration
 * Redirects ?author=N requests to homepage
 */
add_action('template_redirect', 'nraizes_block_user_enumeration', 5);
function nraizes_block_user_enumeration() {
    if (is_admin()) return;

    $author_id = isset($_GET['author']) ? $_GET['author'] : false;

    if ($author_id && !is_array($author_id) && preg_match('/^\d+$/', $author_id)) {
        wp_redirect(home_url(), 301);
        exit;
    }
}

/**
 * Add security headers
 */
add_action('send_headers', 'nraizes_security_headers');
function nraizes_security_headers() {
    if (!is_admin()) {
        header('X-Content-Type-Options: nosniff');
        header('X-Frame-Options: SAMEORIGIN');
        header('X-XSS-Protection: 1; mode=block');
        header('Referrer-Policy: strict-origin-when-cross-origin');
    }
}

/**
 * Remove WordPress version from head
 */
remove_action('wp_head', 'wp_generator');
