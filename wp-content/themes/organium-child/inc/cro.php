<?php
/**
 * CRO - Cross-sells and Sales Enhancements
 * 
 * @package Organium-Child
 */

/**
 * Cross-sells configuration
 */
add_filter('woocommerce_cross_sells_total', function() { return 4; });
add_filter('woocommerce_cross_sells_columns', function() { return 4; });

/**
 * Garantir que cross-sells sejam exibidos no carrinho
 * Usa múltiplos métodos para garantir compatibilidade com Elementor
 */
add_action('woocommerce_cart_collaterals', 'woocommerce_cross_sell_display', 15);
add_action('woocommerce_after_cart', 'nraizes_inject_crosssells_fallback', 10);

/**
 * Fallback: Injetar cross-sells se o tema não renderizar
 */
function nraizes_inject_crosssells_fallback() {
    // Verificar se já foi renderizado
    if (did_action('woocommerce_cross_sell_display') > 0) {
        return;
    }
    
    // Obter produtos do carrinho
    $cart_items = WC()->cart->get_cart();
    $cross_sell_ids = array();
    
    foreach ($cart_items as $cart_item) {
        $product = $cart_item['data'];
        $product_cross_sells = $product->get_cross_sell_ids();
        $cross_sell_ids = array_merge($cross_sell_ids, $product_cross_sells);
    }
    
    // Se não há cross-sells configurados, usar produtos da mesma categoria
    if (empty($cross_sell_ids)) {
        foreach ($cart_items as $cart_item) {
            $product_id = $cart_item['product_id'];
            $category_products = nraizes_get_same_category_products($product_id);
            $cross_sell_ids = array_merge($cross_sell_ids, $category_products);
        }
    }
    
    // Remover duplicatas e produtos já no carrinho
    $cart_product_ids = array_map(function($item) { return $item['product_id']; }, $cart_items);
    $cross_sell_ids = array_diff(array_unique($cross_sell_ids), $cart_product_ids);
    
    if (empty($cross_sell_ids)) return;
    
    // Limitar a 4 produtos
    $cross_sell_ids = array_slice($cross_sell_ids, 0, 4);
    
    // Renderizar seção
    echo '<div class="nraizes-cart-crosssells" style="margin-top: 2rem;">';
    echo '<h2>Você também pode gostar</h2>';
    echo '<ul class="products columns-4">';
    
    foreach ($cross_sell_ids as $product_id) {
        $product = wc_get_product($product_id);
        if (!$product) continue;
        
        echo '<li class="product">';
        echo '<a href="' . esc_url($product->get_permalink()) . '">';
        echo $product->get_image('woocommerce_thumbnail');
        echo '<h2 class="woocommerce-loop-product__title">' . esc_html($product->get_name()) . '</h2>';
        echo '<span class="price">' . $product->get_price_html() . '</span>';
        echo '</a>';
        echo '</li>';
    }
    
    echo '</ul>';
    echo '</div>';
}

/**
 * Adicionar seção de produtos relacionados na página do produto
 */
add_action('woocommerce_after_single_product_summary', 'nraizes_smart_related_products', 15);
function nraizes_smart_related_products() {
    global $product;
    
    if (!$product) return;
    
    $related_ids = nraizes_get_frequently_bought_together($product->get_id());
    
    if (empty($related_ids)) {
        $related_ids = nraizes_get_same_category_products($product->get_id());
    }
    
    if (empty($related_ids)) return;
    
    $args = array(
        'post_type'      => 'product',
        'posts_per_page' => 4,
        'post__in'       => $related_ids,
        'orderby'        => 'post__in',
    );
    
    $products = new WP_Query($args);
    
    if (!$products->have_posts()) return;
    
    echo '<section class="related products nraizes-smart-related">';
    echo '<h2>Clientes também compraram</h2>';
    
    woocommerce_product_loop_start();
    
    while ($products->have_posts()) {
        $products->the_post();
        wc_get_template_part('content', 'product');
    }
    
    woocommerce_product_loop_end();
    
    echo '</section>';
    
    wp_reset_postdata();
}

/**
 * Smart cross-sells based on purchase history
 */
add_filter('woocommerce_product_crosssell_ids', 'nraizes_smart_crosssells', 10, 2);
function nraizes_smart_crosssells($crosssell_ids, $product) {
    if (!empty($crosssell_ids)) {
        return $crosssell_ids;
    }
    
    $product_id = $product->get_id();
    $frequently_bought = nraizes_get_frequently_bought_together($product_id);
    
    if (!empty($frequently_bought)) {
        return array_slice($frequently_bought, 0, 8);
    }
    
    return nraizes_get_same_category_products($product_id);
}

/**
 * Get frequently bought together products from order history
 */
function nraizes_get_frequently_bought_together($product_id) {
    global $wpdb;
    
    $cache_key = 'nraizes_fbt_' . $product_id;
    $cached = get_transient($cache_key);
    if ($cached !== false) {
        return $cached;
    }
    
    $order_ids = $wpdb->get_col($wpdb->prepare("
        SELECT DISTINCT order_id 
        FROM {$wpdb->prefix}woocommerce_order_items oi
        INNER JOIN {$wpdb->prefix}woocommerce_order_itemmeta oim 
            ON oi.order_item_id = oim.order_item_id
        WHERE oim.meta_key = '_product_id' 
        AND oim.meta_value = %d
        LIMIT 100
    ", $product_id));
    
    if (empty($order_ids)) {
        set_transient($cache_key, array(), DAY_IN_SECONDS);
        return array();
    }
    
    $placeholders = implode(',', array_fill(0, count($order_ids), '%d'));
    $query = $wpdb->prepare("
        SELECT oim.meta_value as product_id, COUNT(*) as frequency
        FROM {$wpdb->prefix}woocommerce_order_items oi
        INNER JOIN {$wpdb->prefix}woocommerce_order_itemmeta oim 
            ON oi.order_item_id = oim.order_item_id
        WHERE oi.order_id IN ($placeholders)
        AND oim.meta_key = '_product_id'
        AND oim.meta_value != %d
        GROUP BY oim.meta_value
        ORDER BY frequency DESC
        LIMIT 8
    ", array_merge($order_ids, array($product_id)));
    
    $results = $wpdb->get_results($query);
    
    $product_ids = array();
    foreach ($results as $row) {
        if (get_post_status($row->product_id) === 'publish') {
            $product_ids[] = (int)$row->product_id;
        }
    }
    
    set_transient($cache_key, $product_ids, DAY_IN_SECONDS);
    return $product_ids;
}

/**
 * Fallback: get products from same category
 */
function nraizes_get_same_category_products($product_id) {
    // Check transient cache first
    $cache_key = 'nraizes_same_cat_' . $product_id;
    $cached_ids = get_transient($cache_key);
    if ($cached_ids !== false) {
        return $cached_ids;
    }

    $terms = get_the_terms($product_id, 'product_cat');
    
    if (empty($terms) || is_wp_error($terms)) {
        return array();
    }
    
    $category_ids = wp_list_pluck($terms, 'term_id');
    
    // Fetch a pool of IDs to shuffle in PHP instead of expensive ORDER BY RAND()
    $args = array(
        'post_type'      => 'product',
        'posts_per_page' => 50, // Fetch pool of 50 products
        'post_status'    => 'publish',
        'post__not_in'   => array($product_id),
        'fields'         => 'ids', // Only fetch IDs
        'no_found_rows'  => true, // Skip pagination count
        'tax_query'      => array(
            array(
                'taxonomy' => 'product_cat',
                'field'    => 'term_id',
                'terms'    => $category_ids,
            ),
        ),
    );
    
    $product_ids = get_posts($args);

    if (empty($product_ids)) {
        set_transient($cache_key, array(), DAY_IN_SECONDS);
        return array();
    }

    shuffle($product_ids);
    $result_ids = array_slice($product_ids, 0, 8);

    set_transient($cache_key, $result_ids, DAY_IN_SECONDS);

    return $result_ids;
}
