<?php
/**
 * Security Enhancements
 * 
 * @package Organium-Child
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

/**
 * Disable XML-RPC to prevent brute force attacks
 */
add_filter( 'xmlrpc_enabled', '__return_false' );

/**
 * Add security headers to HTTP responses
 *
 * Implements:
 * - X-Content-Type-Options: nosniff (Prevents MIME sniffing)
 * - X-Frame-Options: SAMEORIGIN (Prevents clickjacking)
 * - X-XSS-Protection: 1; mode=block (Legacy XSS protection)
 * - Referrer-Policy: strict-origin-when-cross-origin (Privacy)
 *
 * @return void
 */
function nraizes_security_headers() {
	if ( ! is_admin() ) {
		header( 'X-Content-Type-Options: nosniff' );
		header( 'X-Frame-Options: SAMEORIGIN' );
		header( 'X-XSS-Protection: 1; mode=block' );
		header( 'Referrer-Policy: strict-origin-when-cross-origin' );
	}
}
add_action( 'send_headers', 'nraizes_security_headers' );

/**
 * Remove WordPress version generator
 * Reduces fingerprinting surface
 */
remove_action( 'wp_head', 'wp_generator' );

/**
 * Block user enumeration via author archives
 *
 * Redirects ?author=N requests to homepage to prevent
 * discovering usernames via author id enumeration.
 *
 * @return void
 */
function nraizes_block_user_enumeration() {
	if ( is_admin() ) {
		return;
	}

	if ( isset( $_GET['author'] ) ) {
		$author = $_GET['author'];

		// Prevent array inputs causing PHP warnings/errors
		if ( is_array( $author ) ) {
			$author = '';
		}

		if ( is_numeric( $author ) ) {
			wp_redirect( home_url(), 301 );
			exit;
		}
	}
}
add_action( 'template_redirect', 'nraizes_block_user_enumeration', 5 );
