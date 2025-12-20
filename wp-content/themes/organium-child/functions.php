<?php
/**
 * Organium Child Theme Functions
 * 
 * @package Organium-Child
 * @version 2.1.0
 */

// Load modular components
require_once get_stylesheet_directory() . '/inc/setup.php';
require_once get_stylesheet_directory() . '/inc/security.php';
require_once get_stylesheet_directory() . '/inc/seo.php';
require_once get_stylesheet_directory() . '/inc/checkout.php';
require_once get_stylesheet_directory() . '/inc/cro.php';
require_once get_stylesheet_directory() . '/inc/mobile.php';
require_once get_stylesheet_directory() . '/inc/performance.php';
require_once get_stylesheet_directory() . '/inc/analytics.php';

// DISABLED: Query cache causing category page issues
// require_once get_stylesheet_directory() . '/inc/cache.php';

// TEMPORARY: Category description updater - DELETE after running once
add_action('admin_init', function() {
    if (isset($_GET['nraizes_update_categories']) && current_user_can('manage_options')) {
        define('NRAIZES_UPDATE_CATEGORIES', true);
        require_once get_stylesheet_directory() . '/update-categories.php';
        exit;
    }
});
