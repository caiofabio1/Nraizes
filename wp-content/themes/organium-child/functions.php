<?php
/**
 * Organium Child Theme
 * 
 * Módulos vitais apenas — sem alterações visuais.
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

// ============================================
// Módulos vitais (carregamento seguro)
// ============================================

$nraizes_modules = array(
    'security.php',            // XML-RPC desabilitado
    'performance.php',         // Core Web Vitals (preload, defer, cleanup)
    'analytics_unified.php',   // GA4 + GTM (rastreamento de vendas)
    'seo.php',                 // Robots.txt, feeds (complementar ao Yoast)
);

foreach ( $nraizes_modules as $module ) {
    $path = get_stylesheet_directory() . '/inc/' . $module;
    if ( file_exists( $path ) ) {
        require_once $path;
    }
}
