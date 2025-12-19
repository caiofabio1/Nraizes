<?php
/**
 * Google Analytics 4 E-commerce Tracking
 * 
 * @package Organium-Child
 */

define('NRAIZES_GA4_ID', 'G-448522931');

/**
 * Load gtag.js
 */
add_action('wp_head', 'nraizes_ga4_script', 1);
function nraizes_ga4_script() {
    ?>
    <!-- Google Analytics 4 -->
    <script async src="https://www.googletagmanager.com/gtag/js?id=<?php echo NRAIZES_GA4_ID; ?>"></script>
    <script>
        window.dataLayer = window.dataLayer || [];
        function gtag(){dataLayer.push(arguments);}
        gtag('js', new Date());
        gtag('config', '<?php echo NRAIZES_GA4_ID; ?>');
    </script>
    <?php
}

/**
 * Track view_item event on product pages
 */
add_action('woocommerce_after_single_product', 'nraizes_ga4_view_item');
function nraizes_ga4_view_item() {
    global $product;
    
    $categories = get_the_terms($product->get_id(), 'product_cat');
    $category_name = !empty($categories) ? $categories[0]->name : '';
    ?>
    <script>
        gtag('event', 'view_item', {
            currency: 'BRL',
            value: <?php echo $product->get_price(); ?>,
            items: [{
                item_id: '<?php echo esc_js($product->get_sku() ?: $product->get_id()); ?>',
                item_name: '<?php echo esc_js($product->get_name()); ?>',
                item_category: '<?php echo esc_js($category_name); ?>',
                price: <?php echo $product->get_price(); ?>,
                quantity: 1
            }]
        });
    </script>
    <?php
}

/**
 * Track add_to_cart event via JavaScript
 */
add_action('wp_footer', 'nraizes_ga4_add_to_cart_js');
function nraizes_ga4_add_to_cart_js() {
    if (!is_product() && !is_shop() && !is_product_category()) return;
    ?>
    <script>
        jQuery(document).ready(function($) {
            // Track add to cart clicks
            $(document.body).on('added_to_cart', function(event, fragments, cart_hash, $button) {
                var $productRow = $button.closest('.product, .cart');
                var productName = $productRow.find('.woocommerce-loop-product__title, .product_title').text() || 'Product';
                var productPrice = $productRow.find('.price .amount').first().text().replace(/[^\d,\.]/g, '').replace(',', '.') || 0;
                
                gtag('event', 'add_to_cart', {
                    currency: 'BRL',
                    value: parseFloat(productPrice),
                    items: [{
                        item_name: productName.trim(),
                        price: parseFloat(productPrice),
                        quantity: 1
                    }]
                });
            });
        });
    </script>
    <?php
}

/**
 * Track begin_checkout event
 */
add_action('woocommerce_before_checkout_form', 'nraizes_ga4_begin_checkout');
function nraizes_ga4_begin_checkout() {
    $cart = WC()->cart;
    $items = array();
    
    foreach ($cart->get_cart() as $item) {
        $product = $item['data'];
        $items[] = array(
            'item_id' => $product->get_sku() ?: $product->get_id(),
            'item_name' => $product->get_name(),
            'price' => $product->get_price(),
            'quantity' => $item['quantity']
        );
    }
    ?>
    <script>
        gtag('event', 'begin_checkout', {
            currency: 'BRL',
            value: <?php echo $cart->get_total('edit'); ?>,
            items: <?php echo wp_json_encode($items); ?>
        });
    </script>
    <?php
}

/**
 * Track purchase event on thank you page
 */
add_action('woocommerce_thankyou', 'nraizes_ga4_purchase', 10, 1);
function nraizes_ga4_purchase($order_id) {
    if (!$order_id) return;
    
    // Only track once
    if (get_post_meta($order_id, '_ga4_tracked', true)) return;
    
    $order = wc_get_order($order_id);
    $items = array();
    
    foreach ($order->get_items() as $item) {
        $product = $item->get_product();
        $items[] = array(
            'item_id' => $product ? ($product->get_sku() ?: $product->get_id()) : $item->get_product_id(),
            'item_name' => $item->get_name(),
            'price' => $order->get_item_total($item, false),
            'quantity' => $item->get_quantity()
        );
    }
    ?>
    <script>
        gtag('event', 'purchase', {
            transaction_id: '<?php echo esc_js($order_id); ?>',
            currency: 'BRL',
            value: <?php echo $order->get_total(); ?>,
            tax: <?php echo $order->get_total_tax(); ?>,
            shipping: <?php echo $order->get_shipping_total(); ?>,
            items: <?php echo wp_json_encode($items); ?>
        });
    </script>
    <?php
    
    // Mark as tracked
    update_post_meta($order_id, '_ga4_tracked', true);
}
