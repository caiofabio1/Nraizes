<?php
/**
 * Organium Child Theme Functions
 * 
 * @package Organium-Child
 * @version 1.1.0
 */

add_action( 'wp_enqueue_scripts', 'enqueue_theme_styles' );
function enqueue_theme_styles() {
    if (class_exists('WooCommerce')) {
        wp_enqueue_style( 'child-style', get_stylesheet_directory_uri() . '/style.css', array('organium-theme', 'organium-style', 'organium-woocommerce') );
    } else {
        wp_enqueue_style( 'child-style', get_stylesheet_directory_uri() . '/style.css', array('organium-theme', 'organium-style') );
    }
}

// ============================================
// Adicione suas customizações abaixo
// ============================================

/**
 * MELHORIA 1: Simplificar campos do checkout
 * Remove campos desnecessários para reduzir fricção
 */
add_filter('woocommerce_checkout_fields', 'nraizes_simplify_checkout');
function nraizes_simplify_checkout($fields) {
    // Remove campos que raramente são usados
    unset($fields['billing']['billing_company']);
    unset($fields['billing']['billing_address_2']);
    unset($fields['shipping']['shipping_company']);
    unset($fields['shipping']['shipping_address_2']);
    return $fields;
}

/**
 * MELHORIA 2: Badges de confiança no checkout
 * Aumenta a confiança do cliente antes do pagamento
 */
add_action('woocommerce_review_order_before_payment', 'nraizes_add_trust_badges');
function nraizes_add_trust_badges() {
    ?>
    <div class="nraizes-trust-badges" style="text-align:center; margin:15px 0; padding:15px; background:#f9f9f9; border-radius:8px; border:1px solid #e5e5e5;">
        <span style="margin:0 12px; display:inline-block;">🔒 Pagamento Seguro</span>
        <span style="margin:0 12px; display:inline-block;">🚚 Entrega Rastreável</span>
        <span style="margin:0 12px; display:inline-block;">✅ Satisfação Garantida</span>
    </div>
    <?php
}

/**
 * MELHORIA 3: Segurança - Desabilitar XML-RPC
 * Previne ataques de força bruta via xmlrpc.php
 */
add_filter('xmlrpc_enabled', '__return_false');
