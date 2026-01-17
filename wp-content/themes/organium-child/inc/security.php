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
 * Add security headers to HTTP response
 */
add_action('send_headers', 'nraizes_security_headers');
function nraizes_security_headers() {
    if (headers_sent()) {
        return;
    }

    $headers = array(
        'X-Frame-Options: SAMEORIGIN',
        'X-Content-Type-Options: nosniff',
        'X-XSS-Protection: 1; mode=block',
        'Referrer-Policy: strict-origin-when-cross-origin',
        'Permissions-Policy: camera=(), microphone=()'
    );

    foreach ($headers as $header) {
        header($header);
    }

    // Strict-Transport-Security only on HTTPS (1 week, no subdomains)
    if (is_ssl()) {
        header('Strict-Transport-Security: max-age=604800');
    }
}
