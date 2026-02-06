<?php
/**
 * Organium Child Theme
 */

// Enqueue child style após parent
add_action( 'wp_enqueue_scripts', 'organium_child_enqueue' );
function organium_child_enqueue() {
    wp_enqueue_style(
        'organium-child-style',
        get_stylesheet_uri(),
        array( 'organium-style' ),
        wp_get_theme()->get( 'Version' )
    );
}

// Loja: 3 colunas (mesmo que o tema pai)
add_filter( 'loop_shop_columns', function() { return 3; } );

// ============================================
// Módulos (descomente um por um para testar)
// ============================================
require_once get_stylesheet_directory() . '/inc/security.php';
require_once get_stylesheet_directory() . '/inc/performance.php';
// require_once get_stylesheet_directory() . '/inc/analytics_unified.php';
// require_once get_stylesheet_directory() . '/inc/seo.php';
