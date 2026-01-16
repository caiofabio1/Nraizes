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
    if ( ! is_admin() ) {
        // Anti-clickjacking
        header( 'X-Frame-Options: SAMEORIGIN' );

        // Block MIME sniffing
        header( 'X-Content-Type-Options: nosniff' );

        // XSS Protection (legacy browsers)
        header( 'X-XSS-Protection: 1; mode=block' );

        // Referrer Policy
        header( 'Referrer-Policy: strict-origin-when-cross-origin' );

        // Permissions Policy (disable unused features)
        header( 'Permissions-Policy: geolocation=(), camera=(), microphone=()' );

        // HSTS (Strict-Transport-Security) - only over SSL
        if ( is_ssl() ) {
            header( 'Strict-Transport-Security: max-age=604800; includeSubDomains' ); // 1 week
        }
    }
}
add_action( 'send_headers', 'nraizes_security_headers' );
