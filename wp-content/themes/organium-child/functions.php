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

// Loja: 3 colunas (mesmo que o tema pai) — prioridade 999 para sobrescrever
add_filter( 'loop_shop_columns', function() { return 3; }, 999 );

// ============================================
// Copiar Customizer do tema pai (roda uma vez)
// ============================================
add_action( 'after_switch_theme', 'nraizes_copy_parent_customizer' );
function nraizes_copy_parent_customizer() {
    $parent_mods = get_option( 'theme_mods_organium' );
    if ( $parent_mods && is_array( $parent_mods ) ) {
        $child_slug = get_option( 'stylesheet' );
        $child_mods = get_option( 'theme_mods_' . $child_slug );
        // Só copia se o child ainda não tem configurações
        if ( ! $child_mods || ! is_array( $child_mods ) || count( $child_mods ) < 3 ) {
            update_option( 'theme_mods_' . $child_slug, $parent_mods );
        }
    }
}
// Forçar cópia do Customizer do pai (roda uma vez, depois remover)
if ( get_option( 'stylesheet' ) === 'organium-child' && ! get_option( 'nraizes_mods_copied' ) ) {
    $parent_mods = get_option( 'theme_mods_organium' );
    if ( $parent_mods && is_array( $parent_mods ) ) {
        update_option( 'theme_mods_organium-child', $parent_mods );
        update_option( 'nraizes_mods_copied', true );
    }
}

// ============================================
// Módulos ativos
// ============================================
require_once get_stylesheet_directory() . '/inc/security.php';
require_once get_stylesheet_directory() . '/inc/performance.php';
require_once get_stylesheet_directory() . '/inc/yoast-config.php';

// ============================================
// Módulos desabilitados (Yoast SEO Premium assume)
// ============================================
// require_once get_stylesheet_directory() . '/inc/seo.php';           // Substituído por yoast-config.php
// require_once get_stylesheet_directory() . '/inc/analytics_unified.php'; // Configurar via GTM/Site Kit
