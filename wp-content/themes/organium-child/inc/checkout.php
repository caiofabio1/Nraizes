<?php
/**
 * Checkout Improvements
 * 
 * @package Organium-Child
 */

/**
 * Simplify checkout fields
 */
add_filter('woocommerce_checkout_fields', 'nraizes_simplify_checkout');
function nraizes_simplify_checkout($fields) {
    unset($fields['billing']['billing_company']);
    unset($fields['billing']['billing_address_2']);
    unset($fields['shipping']['shipping_company']);
    unset($fields['shipping']['shipping_address_2']);
    return $fields;
}

/**
 * Trust badges before payment
 */
add_action('woocommerce_review_order_before_payment', 'nraizes_add_trust_badges');
function nraizes_add_trust_badges() {
    ?>
    <div class="nraizes-trust-badges" role="complementary" aria-label="Garantias de compra">
        <span><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg> Pagamento Seguro</span>
        <span><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><rect x="1" y="3" width="15" height="13"/><polygon points="16 8 20 8 23 11 23 16 16 16 16 8"/><circle cx="5.5" cy="18.5" r="2.5"/><circle cx="18.5" cy="18.5" r="2.5"/></svg> Entrega Rastreavel</span>
        <span><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg> Satisfacao Garantida</span>
    </div>
    <?php
}

/**
 * Free shipping progress bar
 */
add_action('woocommerce_before_cart', 'nraizes_free_shipping_bar');
add_action('woocommerce_before_checkout_form', 'nraizes_free_shipping_bar');
function nraizes_free_shipping_bar() {
    $min_amount = 500;

    if ( ! WC()->cart ) {
        return;
    }

    $current   = (float) WC()->cart->get_cart_contents_total();
    $remaining = $min_amount - $current;
    $percent   = $min_amount > 0 ? min( ( $current / $min_amount ) * 100, 100 ) : 0;

    if ( $remaining > 0 ) {
        ?>
        <div class="nraizes-shipping-bar nraizes-shipping-bar--progress"
             role="region"
             aria-label="<?php esc_attr_e( 'Progresso para frete grátis', 'organium-child' ); ?>"
             aria-live="polite">
            <p id="shipping-progress-text">
                <span aria-hidden="true">🚚</span>
                Faltam <strong>R$ <?php echo esc_html( number_format( $remaining, 2, ',', '.' ) ); ?></strong>
                para <strong>FRETE GRÁTIS!</strong>
            </p>
            <div class="nraizes-shipping-bar__track"
                 role="progressbar"
                 aria-valuenow="<?php echo esc_attr( $percent ); ?>"
                 aria-valuemin="0"
                 aria-valuemax="100"
                 aria-labelledby="shipping-progress-text">
                <div class="nraizes-shipping-bar__fill" style="width:<?php echo esc_attr( $percent ); ?>%;"></div>
            </div>
        </div>
        <?php
    } else {
        ?>
        <div class="nraizes-shipping-bar nraizes-shipping-bar--complete"
             role="status"
             aria-live="polite">
            <p>
                <span aria-hidden="true">🎉</span>
                Parabéns! Você ganhou <strong>FRETE GRÁTIS!</strong>
            </p>
        </div>
        <?php
    }
}
