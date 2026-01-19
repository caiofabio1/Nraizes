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
 * Prevents scanning for users using /?author=N
 */
function organium_child_block_user_enumeration() {
    if ( is_admin() ) return;

    $author_by_id = ( isset( $_GET['author'] ) && is_numeric( $_GET['author'] ) );

    if ( $author_by_id ) {
        wp_redirect( home_url(), 301 );
        exit;
    }
}
add_action( 'template_redirect', 'organium_child_block_user_enumeration', 5 );

/**
 * Add HTTP Security Headers
 */
function organium_child_add_security_headers() {
    if ( is_admin() ) return;

    // Protect against MIME type confusion attacks
    header( 'X-Content-Type-Options: nosniff' );

    // Protect against Clickjacking
    header( 'X-Frame-Options: SAMEORIGIN' );

    // Protect against XSS (for older browsers)
    header( 'X-XSS-Protection: 1; mode=block' );

    // Control referrer information
    header( 'Referrer-Policy: strict-origin-when-cross-origin' );

    // Enforce HSTS (Strict-Transport-Security) - 1 year
    if ( is_ssl() ) {
        header( 'Strict-Transport-Security: max-age=31536000; includeSubDomains' );
    }
}
add_action( 'send_headers', 'organium_child_add_security_headers' );

/**
 * Remove WordPress Version Generator
 *
 * Hides the WP version from the page source to make automated targeting harder.
 */
remove_action('wp_head', 'wp_generator');
