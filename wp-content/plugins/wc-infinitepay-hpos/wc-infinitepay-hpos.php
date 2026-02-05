<?php
/**
 * Plugin Name:       WooCommerce InfinitePay (HPOS)
 * Plugin URI:        https://nraizes.com.br/
 * Description:       Gateway InfinitePay via API oficial com checkout link, webhook REST seguro, verificação inteligente e compatibilidade HPOS.
 * Version:           4.0.0
 * Requires at least: 6.0
 * Requires PHP:      7.4
 * Author:            NRaizes
 * Author URI:        https://nraizes.com.br/
 * License:           GPL-2.0-or-later
 * License URI:       https://www.gnu.org/licenses/gpl-2.0.html
 * Text Domain:       wc-infinitepay-hpos
 * Domain Path:       /languages
 * WC requires at least: 7.0
 * WC tested up to:   9.5
 *
 * @package NRaizes\InfinitePay
 */

defined( 'ABSPATH' ) || exit;

define( 'NRAIZES_IP_VERSION', '4.0.0' );
define( 'NRAIZES_IP_FILE', __FILE__ );
define( 'NRAIZES_IP_PATH', plugin_dir_path( __FILE__ ) );

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
 * Inicializa o gateway após o WooCommerce carregar.
 */
add_action( 'plugins_loaded', 'nraizes_ip_init', 0 );

function nraizes_ip_init() {
    if ( ! class_exists( 'WooCommerce' ) || ! class_exists( 'WC_Payment_Gateway' ) ) {
        add_action( 'admin_notices', function () {
            printf(
                '<div class="notice notice-error"><p><strong>%s</strong> %s</p></div>',
                esc_html__( 'InfinitePay:', 'wc-infinitepay-hpos' ),
                esc_html__( 'Este plugin requer o WooCommerce ativo.', 'wc-infinitepay-hpos' )
            );
        } );
        return;
    }

    require_once NRAIZES_IP_PATH . 'includes/class-wc-gateway-infinitepay.php';
    require_once NRAIZES_IP_PATH . 'includes/class-infinitepay-webhook.php';

    // Registra o gateway.
    add_filter( 'woocommerce_payment_gateways', function ( $methods ) {
        $methods[] = 'WC_Gateway_InfinitePay_HPOS';
        return $methods;
    } );

    // Registra endpoint REST do webhook.
    add_action( 'rest_api_init', array( 'InfinitePay_Webhook', 'register_routes' ) );
}

/**
 * Link de configurações na lista de plugins.
 */
add_filter( 'plugin_action_links_' . plugin_basename( __FILE__ ), function ( $links ) {
    $url = admin_url( 'admin.php?page=wc-settings&tab=checkout&section=infinitepay_hpos' );
    array_unshift( $links, sprintf( '<a href="%s">%s</a>', esc_url( $url ), __( 'Configurações', 'wc-infinitepay-hpos' ) ) );
    return $links;
} );
