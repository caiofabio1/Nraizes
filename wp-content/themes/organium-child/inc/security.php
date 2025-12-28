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
 * Add HTTP security headers
 *
 * Implements "Defense in Depth" by adding standard security headers
 * to protect against XSS, clickjacking, and MIME sniffing.
 */
add_action('send_headers', 'nraizes_security_headers');
function nraizes_security_headers() {
    if (headers_sent()) {
        return;
    }

    // Prevent MIME sniffing
    header('X-Content-Type-Options: nosniff');

    // Prevent Clickjacking (allow from same origin)
    header('X-Frame-Options: SAMEORIGIN');

    // Legacy XSS Protection
    header('X-XSS-Protection: 1; mode=block');

    // Referrer Policy - protect privacy while allowing analytics
    header('Referrer-Policy: strict-origin-when-cross-origin');

    // HSTS - Strict Transport Security (1 year)
    // Uncomment when SSL is verified to avoid lockout
    // header('Strict-Transport-Security: max-age=31536000; includeSubDomains');
}
