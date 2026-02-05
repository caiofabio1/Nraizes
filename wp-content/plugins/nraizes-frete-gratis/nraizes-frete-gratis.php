<?php
/**
 * Plugin Name:       NRaizes - Frete Grátis Condicional
 * Plugin URI:        https://nfrfruits.com/
 * Description:       Método de envio WooCommerce que oferece frete grátis a partir de um valor mínimo configurável, com barra de progresso no carrinho e checkout.
 * Version:           1.0.0
 * Requires at least: 6.0
 * Requires PHP:      7.4
 * Author:            NRaizes
 * Author URI:        https://nfrfruits.com/
 * License:           GPL-2.0-or-later
 * License URI:       https://www.gnu.org/licenses/gpl-2.0.html
 * Text Domain:       nraizes-frete-gratis
 * Domain Path:       /languages
 * WC requires at least: 7.0
 * WC tested up to:   9.5
 *
 * @package NRaizes\FreteGratis
 */

defined( 'ABSPATH' ) || exit;

define( 'NRAIZES_FG_VERSION', '1.0.0' );
define( 'NRAIZES_FG_FILE', __FILE__ );
define( 'NRAIZES_FG_PATH', plugin_dir_path( __FILE__ ) );
define( 'NRAIZES_FG_URL', plugin_dir_url( __FILE__ ) );

/**
 * Declara compatibilidade com HPOS (High-Performance Order Storage).
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
 * Verifica dependência do WooCommerce.
 */
function nraizes_fg_check_woocommerce() {
    if ( ! class_exists( 'WooCommerce' ) ) {
        add_action( 'admin_notices', function () {
            printf(
                '<div class="notice notice-error"><p><strong>%s</strong> %s</p></div>',
                esc_html__( 'NRaizes Frete Grátis:', 'nraizes-frete-gratis' ),
                esc_html__( 'Este plugin requer o WooCommerce ativo.', 'nraizes-frete-gratis' )
            );
        } );
        return false;
    }
    return true;
}

/**
 * Inicializa o plugin após o WooCommerce carregar.
 */
add_action( 'woocommerce_shipping_init', 'nraizes_fg_shipping_init' );

function nraizes_fg_shipping_init() {
    require_once NRAIZES_FG_PATH . 'includes/class-wc-shipping-nraizes-free.php';
}

/**
 * Registra o método de envio no WooCommerce.
 */
add_filter( 'woocommerce_shipping_methods', 'nraizes_fg_add_shipping_method' );

function nraizes_fg_add_shipping_method( $methods ) {
    $methods['nraizes_free_shipping'] = 'WC_Shipping_NRaizes_Free';
    return $methods;
}

/**
 * Carrega componentes do frontend (barra de progresso).
 */
add_action( 'plugins_loaded', 'nraizes_fg_load_frontend' );

function nraizes_fg_load_frontend() {
    if ( ! nraizes_fg_check_woocommerce() ) {
        return;
    }
    require_once NRAIZES_FG_PATH . 'includes/class-nraizes-fg-progress-bar.php';
    NRaizes_FG_Progress_Bar::init();
}

/**
 * Link de configurações na lista de plugins.
 */
add_filter( 'plugin_action_links_' . plugin_basename( __FILE__ ), 'nraizes_fg_action_links' );

function nraizes_fg_action_links( $links ) {
    $settings_url = admin_url( 'admin.php?page=wc-settings&tab=shipping' );
    $settings     = sprintf(
        '<a href="%s">%s</a>',
        esc_url( $settings_url ),
        esc_html__( 'Configurações', 'nraizes-frete-gratis' )
    );
    array_unshift( $links, $settings );
    return $links;
}

/**
 * Carrega traduções.
 */
add_action( 'init', function () {
    load_plugin_textdomain(
        'nraizes-frete-gratis',
        false,
        dirname( plugin_basename( __FILE__ ) ) . '/languages'
    );
} );
