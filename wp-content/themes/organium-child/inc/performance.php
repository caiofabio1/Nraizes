<?php
/**
 * Performance Optimizations
 * 
 * @package Organium-Child
 */

/**
 * Enable native lazy loading for images
 */
add_filter('wp_lazy_loading_enabled', '__return_true');

/**
 * Add loading="lazy" to WooCommerce product images
 */
add_filter('woocommerce_product_get_image', 'nraizes_lazy_load_product_images', 10, 1);
function nraizes_lazy_load_product_images($image) {
    if (strpos($image, 'loading=') === false) {
        $image = str_replace('<img ', '<img loading="lazy" ', $image);
    }
    return $image;
}

/**
 * Preconnect to external resources for faster loading
 */
add_action('wp_head', 'nraizes_preconnect_hints', 1);
function nraizes_preconnect_hints() {
    ?>
    <link rel="preconnect" href="https://fonts.googleapis.com" crossorigin>
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link rel="dns-prefetch" href="https://www.googletagmanager.com">
    <link rel="dns-prefetch" href="https://www.google-analytics.com">
    <?php
}

/**
 * Optimize WooCommerce queries - disable unnecessary features
 */
add_action('wp', 'nraizes_optimize_woocommerce');
function nraizes_optimize_woocommerce() {
    // Disable WooCommerce cart fragments on non-cart pages for faster loading
    if (!is_cart() && !is_checkout()) {
        wp_dequeue_script('wc-cart-fragments');
    }
}

/**
 * Defer non-critical JavaScript
 */
add_filter('script_loader_tag', 'nraizes_defer_scripts', 10, 3);
function nraizes_defer_scripts($tag, $handle, $src) {
    // Scripts that should be deferred
    $defer_scripts = array('comment-reply', 'wp-embed');
    
    if (in_array($handle, $defer_scripts)) {
        return str_replace(' src=', ' defer src=', $tag);
    }
    
    return $tag;
}
