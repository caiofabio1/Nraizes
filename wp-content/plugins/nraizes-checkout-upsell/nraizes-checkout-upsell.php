<?php
/**
 * Plugin Name:       NRaizes - Checkout Recommendations
 * Plugin URI:        https://nraizes.com.br/
 * Description:       Recomendações inteligentes de produtos no checkout baseadas no histórico de compras da loja (frequentemente comprados juntos).
 * Version:           1.0.0
 * Requires at least: 6.0
 * Requires PHP:      7.4
 * Author:            NRaizes
 * Author URI:        https://nraizes.com.br/
 * License:           GPL-2.0-or-later
 * License URI:       https://www.gnu.org/licenses/gpl-2.0.html
 * Text Domain:       nraizes-checkout-upsell
 * Domain Path:       /languages
 * WC requires at least: 7.0
 * WC tested up to:   9.5
 *
 * @package NRaizes\CheckoutUpsell
 */

defined( 'ABSPATH' ) || exit;

define( 'NRAIZES_CU_VERSION', '1.0.0' );
define( 'NRAIZES_CU_FILE', __FILE__ );
define( 'NRAIZES_CU_PATH', plugin_dir_path( __FILE__ ) );
define( 'NRAIZES_CU_URL', plugin_dir_url( __FILE__ ) );

/**
 * Declara compatibilidade com HPOS.
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
 * Inicializa o plugin após o WooCommerce carregar.
 */
add_action( 'plugins_loaded', 'nraizes_cu_init' );

function nraizes_cu_init() {
    if ( ! class_exists( 'WooCommerce' ) ) {
        add_action( 'admin_notices', function () {
            printf(
                '<div class="notice notice-error"><p><strong>%s</strong> %s</p></div>',
                esc_html__( 'NRaizes Checkout Recommendations:', 'nraizes-checkout-upsell' ),
                esc_html__( 'Este plugin requer o WooCommerce ativo.', 'nraizes-checkout-upsell' )
            );
        } );
        return;
    }

    require_once NRAIZES_CU_PATH . 'includes/class-checkout-recommendations.php';
    require_once NRAIZES_CU_PATH . 'includes/class-checkout-upsell-ajax.php';

    NRaizes_Checkout_Recommendations::init();
    NRaizes_Checkout_Upsell_Ajax::init();
}

/**
 * Link de configurações na lista de plugins.
 */
add_filter( 'plugin_action_links_' . plugin_basename( __FILE__ ), function ( $links ) {
    $url = admin_url( 'admin.php?page=wc-settings&tab=products&section=nraizes_checkout_upsell' );
    array_unshift(
        $links,
        sprintf( '<a href="%s">%s</a>', esc_url( $url ), __( 'Configurações', 'nraizes-checkout-upsell' ) )
    );
    return $links;
} );

/**
 * Carrega traduções.
 */
add_action( 'init', function () {
    load_plugin_textdomain(
        'nraizes-checkout-upsell',
        false,
        dirname( plugin_basename( __FILE__ ) ) . '/languages'
    );
} );
