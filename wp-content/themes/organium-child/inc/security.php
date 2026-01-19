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
 * Add security headers to response
 */
add_action('send_headers', 'nraizes_security_headers');
function nraizes_security_headers() {
    if (!is_admin()) {
        // Protect against clickjacking
        header('X-Frame-Options: SAMEORIGIN');

        // Protect against MIME sniffing
        header('X-Content-Type-Options: nosniff');

        // Enable XSS protection
        header('X-XSS-Protection: 1; mode=block');

        // Control referrer information
        header('Referrer-Policy: strict-origin-when-cross-origin');

        // Disable unnecessary browser features
        header('Permissions-Policy: camera=(), microphone=(), geolocation=(), payment=()');

        // HSTS (Strict-Transport-Security) - enforce HTTPS
        if (is_ssl()) {
            header('Strict-Transport-Security: max-age=604800; includeSubDomains'); // 1 week
        }
    }
}
