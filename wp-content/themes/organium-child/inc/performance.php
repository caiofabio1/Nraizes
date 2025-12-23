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

/**
 * Disable WordPress Emojis
 * Removes the extra JavaScript and CSS added by WordPress for emoji support
 */
add_action('init', 'nraizes_disable_emojis');
function nraizes_disable_emojis() {
    remove_action('wp_head', 'print_emoji_detection_script', 7);
    remove_action('admin_print_scripts', 'print_emoji_detection_script');
    remove_action('wp_print_styles', 'print_emoji_styles');
    remove_action('admin_print_styles', 'print_emoji_styles');
    remove_filter('the_content_feed', 'wp_staticize_emoji');
    remove_filter('comment_text_rss', 'wp_staticize_emoji');
    remove_filter('wp_mail', 'wp_staticize_emoji_for_email');
    add_filter('tiny_mce_plugins', 'nraizes_disable_emojis_tinymce');
    add_filter('wp_resource_hints', 'nraizes_disable_emojis_remove_dns_prefetch', 10, 2);
}

function nraizes_disable_emojis_tinymce($plugins) {
    if (is_array($plugins)) {
        return array_diff($plugins, array('wpemoji'));
    }
    return array();
}

function nraizes_disable_emojis_remove_dns_prefetch($urls, $relation_type) {
    if ('dns-prefetch' == $relation_type) {
        $emoji_svg_url = 'https://s.w.org/images/core/emoji/';
        foreach ($urls as $key => $url) {
            if (strpos($url, $emoji_svg_url) !== false) {
                unset($urls[$key]);
            }
        }
    }
    return $urls;
}
