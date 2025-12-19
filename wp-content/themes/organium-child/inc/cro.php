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
    $terms = get_the_terms($product_id, 'product_cat');
    
    if (empty($terms) || is_wp_error($terms)) {
        return array();
    }
    
    $category_ids = wp_list_pluck($terms, 'term_id');
    
    $args = array(
        'post_type'      => 'product',
        'posts_per_page' => 8,
        'post_status'    => 'publish',
        'post__not_in'   => array($product_id),
        'orderby'        => 'rand',
        'tax_query'      => array(
            array(
                'taxonomy' => 'product_cat',
                'field'    => 'term_id',
                'terms'    => $category_ids,
            ),
        ),
    );
    
    $products = get_posts($args);
    return !empty($products) ? wp_list_pluck($products, 'ID') : array();
}
