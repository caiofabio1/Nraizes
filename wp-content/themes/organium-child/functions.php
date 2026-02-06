<?php
/**
 * Organium Child Theme Functions
 * 
 * Carrega módulos de forma segura — se um módulo falhar,
 * o site continua funcionando com o tema pai.
 * 
 * @package Organium-Child
 * @version 2.1.0
 */

// Prevent direct access
if (!defined('ABSPATH')) {
    exit;
}

/**
 * Enqueue child theme stylesheet after parent
 */
add_action('wp_enqueue_scripts', 'nraizes_enqueue_child_styles');
function nraizes_enqueue_child_styles() {
    $parent_deps = array('organium-theme', 'organium-style');
    
    if (class_exists('WooCommerce')) {
        $parent_deps[] = 'organium-woocommerce';
    }
    
    wp_enqueue_style(
        'organium-child-style',
        get_stylesheet_directory_uri() . '/style.css',
        $parent_deps,
        filemtime(get_stylesheet_directory() . '/style.css')
    );
}

/**
 * Carrega um módulo de forma segura.
 * Se der erro, loga mas não quebra o site.
 */
function nraizes_load_module($file, $label = '') {
    $path = get_stylesheet_directory() . '/inc/' . $file;
    
    if (!file_exists($path)) {
        error_log("[NRaizes] Módulo não encontrado: {$file}");
        return false;
    }
    
    try {
        require_once $path;
        return true;
    } catch (\Throwable $e) {
        error_log("[NRaizes] Erro ao carregar {$file}: " . $e->getMessage());
        return false;
    }
}

// ============================================
// Carregar módulos (ordem importa)
// ============================================

// 1. Performance e Cache (sempre)
nraizes_load_module('performance.php');
nraizes_load_module('cache.php');

// 2. SEO (complementar ao Yoast)
nraizes_load_module('seo.php');

// 3. WooCommerce (só se WooCommerce estiver ativo)
if (class_exists('WooCommerce')) {
    nraizes_load_module('checkout.php');
    nraizes_load_module('cro.php');
}

// 4. Mobile UX
nraizes_load_module('mobile.php');

// 5. Analytics unificado (substitui analytics.php antigo)
nraizes_load_module('analytics_unified.php');

// 6. Consulta de Produtos - Shortcode [nraizes_consulta]
nraizes_load_module('consulta-produtos.php');

// 7. Admin tools (só no painel)
if (is_admin()) {
    nraizes_load_module('admin-tools.php');
}
