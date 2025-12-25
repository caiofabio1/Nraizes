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
 * Hide WordPress Version
 * Prevents attackers from easily identifying vulnerable versions
 */
remove_action('wp_head', 'wp_generator');
add_filter('the_generator', '__return_empty_string');

/**
 * Disable User Enumeration via REST API
 * Prevents /wp-json/wp/v2/users from leaking usernames
 */
add_filter('rest_endpoints', 'nraizes_disable_user_endpoints');
function nraizes_disable_user_endpoints($endpoints) {
    if (isset($endpoints['/wp/v2/users']) && !is_user_logged_in()) {
        unset($endpoints['/wp/v2/users']);
    }
    if (isset($endpoints['/wp/v2/users/(?P<id>[\d]+)']) && !is_user_logged_in()) {
        unset($endpoints['/wp/v2/users/(?P<id>[\d]+)']);
    }
    return $endpoints;
}

/**
 * Generic Login Errors
 * Prevents username enumeration via login error messages
 */
add_filter('login_errors', function() {
    return 'Erro no login. Verifique suas credenciais.';
});

/**
 * HTTP Security Headers
 * Adds defense-in-depth headers
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
