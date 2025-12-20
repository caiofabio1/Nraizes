<?php
/**
 * Organium Child Theme Functions
 * 
 * @package Organium-Child
 * @version 2.0.0 (DEBUG MODE)
 */

// DEBUG: Enable error reporting
if (!defined('WP_DEBUG')) {
    error_reporting(E_ALL);
    ini_set('display_errors', 1);
}

// Load modular components - MINIMAL for debugging
require_once get_stylesheet_directory() . '/inc/setup.php';
require_once get_stylesheet_directory() . '/inc/security.php';

// TEMPORARILY DISABLED FOR DEBUG - uncomment one by one to find the issue
// require_once get_stylesheet_directory() . '/inc/seo.php';
// require_once get_stylesheet_directory() . '/inc/checkout.php';
// require_once get_stylesheet_directory() . '/inc/cro.php';
// require_once get_stylesheet_directory() . '/inc/mobile.php';
// require_once get_stylesheet_directory() . '/inc/performance.php';
// require_once get_stylesheet_directory() . '/inc/analytics.php';
// require_once get_stylesheet_directory() . '/inc/cache.php';
