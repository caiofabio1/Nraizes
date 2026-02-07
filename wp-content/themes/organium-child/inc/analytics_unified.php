<?php
/**
 * GA4 E-commerce DataLayer Events
 * 
 * O GA4 e GTM já são carregados via Site Kit / GTM4WP.
 * Este arquivo NÃO carrega tags — apenas injeta eventos
 * de e-commerce no dataLayer para o funil GA4:
 * 
 *   view_item → add_to_cart → begin_checkout → purchase
 * 
 * Também rastreia: contact_whatsapp
 * 
 * @package Organium-Child
 * @version 3.0.0
 */

if (!defined('ABSPATH')) exit;

// ============================================
// 1. VIEW_ITEM - Visualização de produto
// ============================================

add_action('woocommerce_after_single_product', 'nraizes_dl_view_item', 20);
function nraizes_dl_view_item() {
    global $product;
    if (!$product || !is_a($product, 'WC_Product')) return;

    $price = $product->get_price();
    if (!$price) return;

    $cats  = get_the_terms($product->get_id(), 'product_cat');
    $cat   = (!empty($cats) && !is_wp_error($cats)) ? $cats[0]->name : '';
    ?>
    <script>
    window.dataLayer = window.dataLayer || [];
    window.dataLayer.push({ecommerce: null});
    window.dataLayer.push({
        'event': 'view_item',
        'ecommerce': {
            'currency': 'BRL',
            'value': <?php echo (float) $price; ?>,
            'items': [{
                'item_id': '<?php echo esc_js($product->get_sku() ?: $product->get_id()); ?>',
                'item_name': '<?php echo esc_js($product->get_name()); ?>',
                'item_category': '<?php echo esc_js($cat); ?>',
                'price': <?php echo (float) $price; ?>,
                'quantity': 1
            }]
        }
    });
    </script>
    <?php
}

// ============================================
// 2. ADD_TO_CART - Adição ao carrinho
// ============================================

add_action('wp_footer', 'nraizes_dl_add_to_cart', 50);
function nraizes_dl_add_to_cart() {
    // Só em páginas com botão de compra
    if (!is_product() && !is_shop() && !is_product_category() && !is_product_tag()) return;
    ?>
    <script>
    (function() {
        document.addEventListener('click', function(e) {
            var btn = e.target.closest('.add_to_cart_button, .single_add_to_cart_button');
            if (!btn) return;

            var name = '', price = 0, id = '', sku = '';

            // Página de produto individual
            var titleEl = document.querySelector('.product_title');
            var priceEl = document.querySelector('.summary .price ins .amount, .summary .price > .amount');
            
            if (titleEl && priceEl) {
                name = titleEl.textContent.trim();
                price = parseFloat(priceEl.textContent.replace(/[^\d,\.]/g, '').replace(',', '.')) || 0;
            }

            // Loop de produtos (loja/categoria)
            if (!name) {
                var card = btn.closest('.product');
                if (card) {
                    var t = card.querySelector('.woocommerce-loop-product__title');
                    var p = card.querySelector('.price ins .amount, .price > .amount');
                    name = t ? t.textContent.trim() : '';
                    price = p ? parseFloat(p.textContent.replace(/[^\d,\.]/g, '').replace(',', '.')) || 0 : 0;
                }
            }

            id = btn.getAttribute('data-product_id') || '';
            sku = btn.getAttribute('data-product_sku') || id;

            if (!name) return;

            window.dataLayer = window.dataLayer || [];
            window.dataLayer.push({ecommerce: null});
            window.dataLayer.push({
                'event': 'add_to_cart',
                'ecommerce': {
                    'currency': 'BRL',
                    'value': price,
                    'items': [{
                        'item_id': sku,
                        'item_name': name,
                        'price': price,
                        'quantity': 1
                    }]
                }
            });
        });
    })();
    </script>
    <?php
}

// ============================================
// 3. BEGIN_CHECKOUT - Início do checkout
// ============================================

add_action('woocommerce_before_checkout_form', 'nraizes_dl_begin_checkout', 5);
function nraizes_dl_begin_checkout() {
    if (!function_exists('WC') || !WC()->cart) return;

    $cart  = WC()->cart;
    $items = array();

    foreach ($cart->get_cart() as $cart_item) {
        $p = $cart_item['data'];
        if (!$p) continue;

        $cats = get_the_terms($p->get_id(), 'product_cat');
        $cat  = (!empty($cats) && !is_wp_error($cats)) ? $cats[0]->name : '';

        $items[] = array(
            'item_id'       => $p->get_sku() ?: (string) $p->get_id(),
            'item_name'     => $p->get_name(),
            'item_category' => $cat,
            'price'         => (float) $p->get_price(),
            'quantity'      => $cart_item['quantity'],
        );
    }
    ?>
    <script>
    window.dataLayer = window.dataLayer || [];
    window.dataLayer.push({ecommerce: null});
    window.dataLayer.push({
        'event': 'begin_checkout',
        'ecommerce': {
            'currency': 'BRL',
            'value': <?php echo (float) $cart->get_total('edit'); ?>,
            'items': <?php echo wp_json_encode($items); ?>
        }
    });
    </script>
    <?php
}

// ============================================
// 4. PURCHASE - Compra finalizada
// ============================================

add_action('woocommerce_thankyou', 'nraizes_dl_purchase', 5);
function nraizes_dl_purchase($order_id) {
    if (!$order_id) return;

    // Previne duplicata (recarregamento da thank-you page)
    if (get_post_meta($order_id, '_nraizes_ga4_tracked', true)) return;

    $order = wc_get_order($order_id);
    if (!$order) return;

    $items = array();
    foreach ($order->get_items() as $item) {
        $p = $item->get_product();
        if (!$p) continue;

        $cats = get_the_terms($p->get_id(), 'product_cat');
        $cat  = (!empty($cats) && !is_wp_error($cats)) ? $cats[0]->name : '';

        $items[] = array(
            'item_id'       => $p->get_sku() ?: (string) $p->get_id(),
            'item_name'     => $item->get_name(),
            'item_category' => $cat,
            'price'         => (float) $order->get_item_total($item, false),
            'quantity'      => $item->get_quantity(),
        );
    }
    ?>
    <script>
    window.dataLayer = window.dataLayer || [];
    window.dataLayer.push({ecommerce: null});
    window.dataLayer.push({
        'event': 'purchase',
        'ecommerce': {
            'transaction_id': '<?php echo esc_js($order_id); ?>',
            'currency': 'BRL',
            'value': <?php echo (float) $order->get_total(); ?>,
            'tax': <?php echo (float) $order->get_total_tax(); ?>,
            'shipping': <?php echo (float) $order->get_shipping_total(); ?>,
            'items': <?php echo wp_json_encode($items); ?>
        }
    });
    </script>
    <?php

    update_post_meta($order_id, '_nraizes_ga4_tracked', true);
}

// ============================================
// 5. WHATSAPP - Clique no WhatsApp
// ============================================

add_action('wp_footer', 'nraizes_dl_whatsapp', 50);
function nraizes_dl_whatsapp() {
    ?>
    <script>
    (function() {
        document.addEventListener('click', function(e) {
            var link = e.target.closest('a[href*="wa.me"], a[href*="whatsapp"]');
            if (!link) return;

            window.dataLayer = window.dataLayer || [];
            window.dataLayer.push({
                'event': 'contact_whatsapp',
                'link_url': link.href,
                'page_location': window.location.href
            });
        });
    })();
    </script>
    <?php
}
