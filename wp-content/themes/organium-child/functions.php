<?php
/**
 * Organium Child Theme Functions
 * 
 * @package Organium-Child
 * @version 1.1.0
 */

add_action( 'wp_enqueue_scripts', 'enqueue_theme_styles' );
function enqueue_theme_styles() {
    $css_version = filemtime( get_stylesheet_directory() . '/style.css' );
    if (class_exists('WooCommerce')) {
        wp_enqueue_style( 'child-style', get_stylesheet_directory_uri() . '/style.css', array('organium-theme', 'organium-style', 'organium-woocommerce'), $css_version );
    } else {
        wp_enqueue_style( 'child-style', get_stylesheet_directory_uri() . '/style.css', array('organium-theme', 'organium-style'), $css_version );
    }
}

// ============================================
// Carregar módulos de otimização
// ============================================

// Segurança e Performance
require_once get_stylesheet_directory() . '/inc/security.php';
require_once get_stylesheet_directory() . '/inc/performance.php';
require_once get_stylesheet_directory() . '/inc/cache.php';

// SEO (complementar ao Yoast)
require_once get_stylesheet_directory() . '/inc/seo.php';

// Checkout e Conversão
require_once get_stylesheet_directory() . '/inc/checkout.php';
require_once get_stylesheet_directory() . '/inc/cro.php';

// Mobile UX Enhancements
require_once get_stylesheet_directory() . '/inc/mobile.php';

// Analytics: Implementação unificada para corrigir problema de atribuição
require_once get_stylesheet_directory() . '/inc/analytics_unified.php';

// Consulta de Produtos (GEO-optimized) - Shortcode [nraizes_consulta]
require_once get_stylesheet_directory() . '/inc/consulta-produtos.php';

// ============================================
// Adicione suas customizações abaixo
// ============================================

// Ferramentas de Admin (disponível em Ferramentas > Novas Raízes)
if (is_admin()) {
    require_once get_stylesheet_directory() . '/inc/admin-tools.php';
}
