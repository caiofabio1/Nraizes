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
add_action('send_headers', 'nraizes_security_headers');
function nraizes_security_headers() {
    if (headers_sent()) {
        return;
    }

    // Prevent MIME type sniffing
    header('X-Content-Type-Options: nosniff');

    // Prevent clickjacking
    header('X-Frame-Options: SAMEORIGIN');

    // Enable XSS filtering in browser
    header('X-XSS-Protection: 1; mode=block');

    // Control referrer information
    header('Referrer-Policy: strict-origin-when-cross-origin');

    // Restrict browser features (Camera, Mic, Geolocation)
    header('Permissions-Policy: geolocation=(), camera=(), microphone=()');

    // Remove PHP version info (if exposed by server config)
    if (function_exists('header_remove')) {
        header_remove('X-Powered-By');
    }
}
