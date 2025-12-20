<?php
/**
 * WooCommerce Query Cache Optimization
 * 
 * @package Organium-Child
 */

// ============================================
// PRODUCT CATEGORY CACHE
// ============================================

/**
 * Cache products by category query
 * TTL: 15 minutes
 */
add_filter('woocommerce_product_query', 'nraizes_cache_category_query', 10, 2);
function nraizes_cache_category_query($q, $query)
{
    // Only cache on category pages
    if (!is_product_category())
        return $q;

    $term = get_queried_object();
    if (!$term || !isset($term->term_id))
        return $q;

    $paged = $q->get('paged') ?: 1;
    $cache_key = 'nraizes_cat_' . $term->term_id . '_' . $paged;
    $cached_ids = get_transient($cache_key);

    // Only use cache if it's a non-empty array
    if ($cached_ids !== false && is_array($cached_ids) && !empty($cached_ids)) {
        $q->set('post__in', $cached_ids);
        $q->set('orderby', 'post__in');
    }

    return $q;
}

/**
 * Store category query results in cache
 */
add_action('woocommerce_after_shop_loop', 'nraizes_store_category_cache');
function nraizes_store_category_cache()
{
    if (!is_product_category())
        return;

    global $wp_query;
    $term = get_queried_object();
    if (!$term)
        return;

    $paged = get_query_var('paged') ?: 1;
    $cache_key = 'nraizes_cat_' . $term->term_id . '_' . $paged;

    // Only cache if not already cached
    if (get_transient($cache_key) !== false)
        return;

    $product_ids = wp_list_pluck($wp_query->posts, 'ID');
    set_transient($cache_key, $product_ids, 15 * MINUTE_IN_SECONDS);
}

// ============================================
// MENU CACHE
// ============================================

/**
 * Cache navigation menu
 * TTL: 24 hours
 */
add_filter('pre_wp_nav_menu', 'nraizes_cache_nav_menu', 10, 2);
function nraizes_cache_nav_menu($output, $args)
{
    if (is_admin() || is_customize_preview())
        return $output;

    $menu_location = isset($args->theme_location) ? $args->theme_location : 'default';
    $cache_key = 'nraizes_menu_' . $menu_location;

    $cached = get_transient($cache_key);
    if ($cached !== false) {
        return $cached;
    }

    return $output;
}

add_filter('wp_nav_menu', 'nraizes_store_menu_cache', 10, 2);
function nraizes_store_menu_cache($nav_menu, $args)
{
    if (is_admin() || is_customize_preview())
        return $nav_menu;

    $menu_location = isset($args->theme_location) ? $args->theme_location : 'default';
    $cache_key = 'nraizes_menu_' . $menu_location;

    if (get_transient($cache_key) === false) {
        set_transient($cache_key, $nav_menu, DAY_IN_SECONDS);
    }

    return $nav_menu;
}

/**
 * Clear menu cache when menu is updated
 */
add_action('wp_update_nav_menu', 'nraizes_clear_menu_cache');
function nraizes_clear_menu_cache()
{
    global $wpdb;
    $wpdb->query("DELETE FROM {$wpdb->options} WHERE option_name LIKE '_transient_nraizes_menu_%'");
    $wpdb->query("DELETE FROM {$wpdb->options} WHERE option_name LIKE '_transient_timeout_nraizes_menu_%'");
}

// ============================================
// RELATED PRODUCTS CACHE
// ============================================

/**
 * Cache related products query
 * TTL: 1 hour
 */
add_filter('woocommerce_related_products', 'nraizes_cache_related_products', 10, 3);
function nraizes_cache_related_products($related_posts, $product_id, $args)
{
    $cache_key = 'nraizes_related_' . $product_id;

    $cached = get_transient($cache_key);
    if ($cached !== false) {
        return $cached;
    }

    // Store for next time
    set_transient($cache_key, $related_posts, HOUR_IN_SECONDS);

    return $related_posts;
}

// ============================================
// WIDGET CACHE
// ============================================

/**
 * Cache sidebar widgets
 * TTL: 1 hour
 */
add_filter('dynamic_sidebar_has_widgets', 'nraizes_maybe_serve_cached_sidebar', 10, 2);
function nraizes_maybe_serve_cached_sidebar($has_widgets, $sidebar_id)
{
    if (is_admin() || is_customize_preview())
        return $has_widgets;

    // Only cache specific sidebars
    $cacheable = array('shop-sidebar', 'product-sidebar', 'sidebar-1');
    if (!in_array($sidebar_id, $cacheable))
        return $has_widgets;

    return $has_widgets;
}

// ============================================
// CACHE INVALIDATION
// ============================================

/**
 * Clear product caches when product is updated
 */
add_action('woocommerce_update_product', 'nraizes_clear_product_caches');
add_action('woocommerce_new_product', 'nraizes_clear_product_caches');
function nraizes_clear_product_caches($product_id)
{
    // Clear related products cache
    delete_transient('nraizes_related_' . $product_id);

    // Clear frequently bought together cache
    delete_transient('nraizes_fbt_' . $product_id);

    // Clear category caches for this product's categories
    $categories = get_the_terms($product_id, 'product_cat');
    if (!empty($categories) && !is_wp_error($categories)) {
        foreach ($categories as $cat) {
            global $wpdb;
            $wpdb->query($wpdb->prepare(
                "DELETE FROM {$wpdb->options} WHERE option_name LIKE %s",
                '_transient_nraizes_cat_' . $cat->term_id . '_%'
            ));
        }
    }
}

/**
 * Clear all caches on theme/plugin update
 */
add_action('after_switch_theme', 'nraizes_clear_all_caches');
add_action('upgrader_process_complete', 'nraizes_clear_all_caches');
function nraizes_clear_all_caches()
{
    global $wpdb;
    $wpdb->query("DELETE FROM {$wpdb->options} WHERE option_name LIKE '_transient_nraizes_%'");
    $wpdb->query("DELETE FROM {$wpdb->options} WHERE option_name LIKE '_transient_timeout_nraizes_%'");
}
