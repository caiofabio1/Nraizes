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
 * Add security headers
 */
function nraizes_security_headers() {
    if (is_admin()) {
        return;
    }

    header('X-Content-Type-Options: nosniff');
    header('X-Frame-Options: SAMEORIGIN');
    header('X-XSS-Protection: 1; mode=block');
    header('Referrer-Policy: strict-origin-when-cross-origin');
    // Removed geolocation restriction to avoid breaking store locators
    header('Permissions-Policy: camera=(), microphone=()');

    if (is_ssl()) {
        // HSTS: 1 week max-age for safety, no subdomains initially
        header('Strict-Transport-Security: max-age=604800');
    }
}
add_action('send_headers', 'nraizes_security_headers');
