<?php
/**
 * Plugin Name:       NRaizes - Botão Flutuante Loja
 * Plugin URI:        https://nraizes.com.br/
 * Description:       Botão flutuante (sticky) no canto inferior da tela para navegação rápida até a loja WooCommerce.
 * Version:           1.0.0
 * Requires at least: 6.0
 * Requires PHP:      7.4
 * Author:            NRaizes
 * Author URI:        https://nraizes.com.br/
 * License:           GPL-2.0-or-later
 * License URI:       https://www.gnu.org/licenses/gpl-2.0.html
 * Text Domain:       nraizes-floating-shop
 * WC requires at least: 7.0
 * WC tested up to:   9.5
 *
 * @package NRaizes\FloatingShop
 */

defined( 'ABSPATH' ) || exit;

define( 'NRAIZES_FS_VERSION', '1.0.0' );
define( 'NRAIZES_FS_URL', plugin_dir_url( __FILE__ ) );

/**
 * HPOS compatibility.
 */
add_action( 'before_woocommerce_init', function () {
    if ( class_exists( \Automattic\WooCommerce\Utilities\FeaturesUtil::class ) ) {
        \Automattic\WooCommerce\Utilities\FeaturesUtil::declare_compatibility(
            'custom_order_tables',
            __FILE__,
            true
        );
    }
} );

/**
 * Inicializa o plugin.
 */
add_action( 'wp', 'nraizes_fs_init' );

function nraizes_fs_init() {
    // Não exibe na própria loja, no carrinho, no checkout ou no admin.
    if ( is_admin() ) {
        return;
    }

    $hide_on_shop = apply_filters( 'nraizes_fs_hide_on_shop', true );

    if ( $hide_on_shop && function_exists( 'is_shop' ) && ( is_shop() || is_cart() || is_checkout() ) ) {
        return;
    }

    add_action( 'wp_footer', 'nraizes_fs_render_button' );
    add_action( 'wp_enqueue_scripts', 'nraizes_fs_enqueue_assets' );
}

/**
 * Renderiza o botão flutuante.
 */
function nraizes_fs_render_button() {
    $shop_url = function_exists( 'wc_get_page_permalink' )
        ? wc_get_page_permalink( 'shop' )
        : home_url( '/loja/' );

    $label = apply_filters(
        'nraizes_fs_button_label',
        __( 'Ver Produtos', 'nraizes-floating-shop' )
    );

    ?>
    <a href="<?php echo esc_url( $shop_url ); ?>"
       class="nraizes-fab"
       id="nraizes-fab"
       aria-label="<?php echo esc_attr( $label ); ?>"
       role="link">
        <svg class="nraizes-fab__icon" width="22" height="22" viewBox="0 0 24 24"
             fill="none" stroke="currentColor" stroke-width="2"
             stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"/>
            <line x1="3" y1="6" x2="21" y2="6"/>
            <path d="M16 10a4 4 0 0 1-8 0"/>
        </svg>
        <span class="nraizes-fab__text"><?php echo esc_html( $label ); ?></span>
    </a>
    <?php
}

/**
 * Enfileira estilos.
 */
function nraizes_fs_enqueue_assets() {
    wp_enqueue_style(
        'nraizes-floating-shop',
        NRAIZES_FS_URL . 'assets/css/floating-shop.css',
        array(),
        NRAIZES_FS_VERSION
    );
}

/**
 * Link de configurações / filtros na lista de plugins.
 */
add_filter( 'plugin_action_links_' . plugin_basename( __FILE__ ), function ( $links ) {
    $links[] = sprintf(
        '<span title="%s">%s</span>',
        esc_attr__( 'Personalize via filtros: nraizes_fs_button_label, nraizes_fs_hide_on_shop', 'nraizes-floating-shop' ),
        __( 'Via filtros PHP', 'nraizes-floating-shop' )
    );
    return $links;
} );
