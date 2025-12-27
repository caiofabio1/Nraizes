<?php
/**
 * Security Enhancements
 * 
 * @package Organium-Child
 */

// Prevent direct access
if (!defined('ABSPATH')) {
    exit;
}

/**
 * Disable XML-RPC to prevent brute force attacks
 */
add_filter('xmlrpc_enabled', '__return_false');

/**
 * Security Headers
 * Adds basic security headers to responses to protect against common attacks.
 */
add_action('send_headers', 'nraizes_add_security_headers');
function nraizes_add_security_headers() {
    if (!is_admin()) {
        // Prevent clickjacking
        header('X-Frame-Options: SAMEORIGIN');

        // Enforce XSS filtering
        header('X-XSS-Protection: 1; mode=block');

        // Prevent MIME type sniffing
        header('X-Content-Type-Options: nosniff');

        // Referrer Policy
        header('Referrer-Policy: strict-origin-when-cross-origin');

        // Strict Transport Security (HSTS) - 1 year
        // Only enabled if SSL is detected to prevent lockout
        if (is_ssl()) {
            header('Strict-Transport-Security: max-age=31536000; includeSubDomains');
        }
    }
}
