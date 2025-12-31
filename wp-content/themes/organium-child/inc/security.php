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
 * Remove WordPress version from head
 * Reduces information leakage about the specific version running
 */
remove_action('wp_head', 'wp_generator');

/**
 * Add HTTP Security Headers
 * Implements defense-in-depth via response headers
 */
add_action('send_headers', 'nraizes_security_headers');
function nraizes_security_headers() {
    // Prevent MIME-type sniffing
    header('X-Content-Type-Options: nosniff');

    // Prevent clickjacking by not allowing the site to be embedded in frames on other domains
    header('X-Frame-Options: SAMEORIGIN');

    // Enable browser's built-in XSS protection (for older browsers)
    header('X-XSS-Protection: 1; mode=block');

    // Control how much referrer information is sent with requests
    header('Referrer-Policy: strict-origin-when-cross-origin');

    // Restrict access to sensitive browser features
    header('Permissions-Policy: geolocation=(), microphone=(), camera=()');
}
