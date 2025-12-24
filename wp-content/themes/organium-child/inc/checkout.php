<?php
/**
 * Checkout Improvements
 * 
 * @package Organium-Child
 */

/**
 * Simplify checkout fields and optimize order
 */
add_filter('woocommerce_checkout_fields', 'nraizes_simplify_checkout');
function nraizes_simplify_checkout($fields) {
    unset($fields['billing']['billing_company']);
    unset($fields['billing']['billing_address_2']);
    unset($fields['shipping']['shipping_company']);
    unset($fields['shipping']['shipping_address_2']);

    // Move email to top for better capture
    if (isset($fields['billing']['billing_email'])) {
        $fields['billing']['billing_email']['priority'] = 1;
    }

    return $fields;
}

/**
 * Trust badges before payment and in cart
 */
add_action('woocommerce_review_order_before_payment', 'nraizes_add_trust_badges');
add_action('woocommerce_proceed_to_checkout', 'nraizes_add_trust_badges', 20);

function nraizes_add_trust_badges() {
    ?>
    <div class="nraizes-trust-badges">
        <span>🔒 Pagamento Seguro</span>
        <span>🚚 Entrega Rastreável</span>
        <span>✅ Satisfação Garantida</span>
    </div>
    <?php
}

/**
 * Auto-select Free Shipping if available
 */
add_action( 'woocommerce_before_cart', 'nraizes_auto_select_free_shipping' );
function nraizes_auto_select_free_shipping() {
    if ( ! WC()->cart || WC()->cart->is_empty() ) {
        return;
    }

    // Iterate through packages stored in session which contain calculated rates
    $packages = WC()->shipping->get_packages();
    if ( empty( $packages ) ) {
        return;
    }

    foreach ( $packages as $i => $package ) {
        if ( ! isset( $package['rates'] ) ) {
            continue;
        }

        foreach ( $package['rates'] as $rate_id => $rate ) {
            if ( 'free_shipping' === $rate->method_id ) {
                $chosen_methods = WC()->session->get( 'chosen_shipping_methods' );
                if ( isset( $chosen_methods[ $i ] ) && $chosen_methods[ $i ] !== $rate_id ) {
                    $chosen_methods[ $i ] = $rate_id;
                    WC()->session->set( 'chosen_shipping_methods', $chosen_methods );
                }
                break;
            }
        }
    }
}

/**
 * Free shipping progress bar
 */
add_action('woocommerce_before_cart', 'nraizes_free_shipping_bar');
add_action('woocommerce_before_checkout_form', 'nraizes_free_shipping_bar');

function nraizes_free_shipping_bar() {
    echo nraizes_get_free_shipping_html();
}

function nraizes_get_free_shipping_html() {
    if ( ! WC()->cart ) {
        return '';
    }

    $min_amount = 500;
    // Use get_cart_contents_total for a reliable numeric subtotal
    $current = (float) WC()->cart->get_cart_contents_total();
    $remaining = $min_amount - $current;
    
    ob_start();
    ?>
    <div id="nraizes-free-shipping-bar-wrapper">
        <?php if ($remaining > 0) :
            $percent = ($current / $min_amount) * 100;
            ?>
            <div class="nraizes-shipping-bar nraizes-shipping-bar--progress">
                <p>
                    🚚 Faltam <strong>R$ <?php echo number_format($remaining, 2, ',', '.'); ?></strong> para <strong>FRETE GRÁTIS!</strong>
                </p>
                <div class="nraizes-shipping-bar__track">
                    <div class="nraizes-shipping-bar__fill" style="width:<?php echo min($percent, 100); ?>%;"></div>
                </div>
            </div>
        <?php else : ?>
            <div class="nraizes-shipping-bar nraizes-shipping-bar--complete">
                <p>🎉 Parabéns! Você ganhou <strong>FRETE GRÁTIS!</strong></p>
            </div>
        <?php endif; ?>
    </div>
    <?php
    return ob_get_clean();
}

/**
 * Update free shipping bar via AJAX
 */
add_filter( 'woocommerce_add_to_cart_fragments', 'nraizes_refresh_free_shipping_bar_fragment' );
add_filter( 'woocommerce_update_order_review_fragments', 'nraizes_refresh_free_shipping_bar_fragment' );

function nraizes_refresh_free_shipping_bar_fragment( $fragments ) {
    $fragments['#nraizes-free-shipping-bar-wrapper'] = nraizes_get_free_shipping_html();
    return $fragments;
}
