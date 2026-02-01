<?php
/**
 * Performance Optimizations - Enhanced for PageSpeed
 * 
 * @package Organium-Child
 * @version 2.0.0 - Aggressive optimizations for mobile performance
 */

// ============================================
// LCP OPTIMIZATION (20.5s -> 2.5s target)
// ============================================

/**
 * Preload LCP image on product pages
 */
add_action('wp_head', 'nraizes_preload_lcp_image', 1);
function nraizes_preload_lcp_image() {
    if (is_product()) {
        global $post;
        $image_id = get_post_thumbnail_id($post->ID);
        if ($image_id) {
            $image_src = wp_get_attachment_image_src($image_id, 'woocommerce_single');
            if ($image_src) {
                echo '<link rel="preload" as="image" href="' . esc_url($image_src[0]) . '" fetchpriority="high">';
            }
        }
    }
    // Homepage/shop LCP - first product or banner
    if (is_shop() || is_front_page()) {
        ?>
        <link rel="preload" as="image" href="<?php echo esc_url(get_stylesheet_directory_uri()); ?>/assets/hero-banner.webp" fetchpriority="high">
        <?php
    }
}

/**
 * Add fetchpriority="high" to LCP images
 */
add_filter('wp_get_attachment_image_attributes', 'nraizes_lcp_fetchpriority', 10, 3);
function nraizes_lcp_fetchpriority($attr, $attachment, $size) {
    // Remove lazy loading from above-the-fold images
    if (is_product() && in_the_loop() && $size === 'woocommerce_single') {
        unset($attr['loading']);
        $attr['fetchpriority'] = 'high';
        $attr['decoding'] = 'sync';
    }
    return $attr;
}

/**
 * Remove lazy loading from first 4 products in shop loop
 */
add_filter('woocommerce_product_get_image', 'nraizes_shop_first_images', 10, 5);
function nraizes_shop_first_images($image, $product, $size, $attr, $placeholder) {
    global $woocommerce_loop;
    $loop_index = isset($woocommerce_loop['loop']) ? $woocommerce_loop['loop'] : 0;
    
    // First row of products - above fold, no lazy loading
    if ($loop_index <= 4) {
        $image = str_replace(' loading="lazy"', '', $image);
        $image = str_replace('<img ', '<img fetchpriority="high" ', $image);
    }
    return $image;
}

// ============================================
// TBT OPTIMIZATION (760ms -> 200ms target)
// ============================================

/**
 * Defer ALL non-critical scripts
 */
add_filter('script_loader_tag', 'nraizes_defer_all_scripts', 10, 3);
function nraizes_defer_all_scripts($tag, $handle, $src) {
    // Critical scripts that should NOT be deferred
    $critical = array('jquery-core', 'jquery');
    
    // Scripts to explicitly defer
    $defer = array(
        'comment-reply', 'wp-embed', 'contact-form-7',
        'wc-add-to-cart', 'wc-cart-fragments', 'wc-single-product',
        'wc-checkout', 'selectWoo', 'woocommerce', 'js-cookie',
        'gtm4wp', 'google_gtagjs', 'google-recaptcha'
    );
    
    // Skip if already has defer/async
    if (strpos($tag, 'defer') !== false || strpos($tag, 'async') !== false) {
        return $tag;
    }
    
    // Don't defer critical scripts
    if (in_array($handle, $critical)) {
        return $tag;
    }
    
    // Defer known heavy scripts
    if (in_array($handle, $defer) || strpos($handle, 'elementor') !== false) {
        return str_replace(' src=', ' defer src=', $tag);
    }
    
    return $tag;
}

/**
 * Remove unnecessary scripts on specific pages
 */
add_action('wp_enqueue_scripts', 'nraizes_remove_unnecessary_scripts', 999);
function nraizes_remove_unnecessary_scripts() {
    // Remove Gutenberg block CSS if not using blocks
    if (!is_singular()) {
        wp_dequeue_style('wp-block-library');
        wp_dequeue_style('wp-block-library-theme');
        wp_dequeue_style('wc-blocks-style');
        wp_dequeue_style('global-styles');
    }
    
    // Remove cart fragments from non-cart pages (big TBT reducer)
    if (!is_cart() && !is_checkout() && !is_woocommerce()) {
        wp_dequeue_script('wc-cart-fragments');
    }
    
    // Remove comment-reply JS if not needed
    if (!is_singular() || !comments_open()) {
        wp_dequeue_script('comment-reply');
    }
    
    // Remove emoji scripts
    remove_action('wp_head', 'print_emoji_detection_script', 7);
    remove_action('wp_print_styles', 'print_emoji_styles');
    
    // Remove oEmbed
    remove_action('wp_head', 'wp_oembed_add_discovery_links');
    remove_action('wp_head', 'wp_oembed_add_host_js');
}

/**
 * Delay non-essential JS execution until user interaction
 */
add_action('wp_footer', 'nraizes_delay_scripts_until_interaction', 999);
function nraizes_delay_scripts_until_interaction() {
    ?>
    <script>
    (function() {
        var userInteracted = false;
        var delayedScripts = [];
        
        function triggerDelayed() {
            if (userInteracted) return;
            userInteracted = true;
            
            // Load deferred analytics/tracking
            if (typeof gtag === 'undefined' && window.gtagConfig) {
                var s = document.createElement('script');
                s.src = 'https://www.googletagmanager.com/gtag/js?id=' + window.gtagConfig;
                document.head.appendChild(s);
            }
        }
        
        ['scroll', 'click', 'touchstart', 'mousemove', 'keydown'].forEach(function(e) {
            window.addEventListener(e, triggerDelayed, {once: true, passive: true});
        });
        
        // Fallback: load after 5 seconds anyway
        setTimeout(triggerDelayed, 5000);
    })();
    </script>
    <?php
}

// ============================================
// CLS OPTIMIZATION (0.289 -> 0.1 target)
// ============================================

/**
 * Add explicit dimensions to product images
 */
add_filter('woocommerce_get_image_size_single', 'nraizes_explicit_image_dimensions');
function nraizes_explicit_image_dimensions($size) {
    $size['width'] = 600;
    $size['height'] = 600;
    $size['crop'] = 1;
    return $size;
}

/**
 * Reserve space for ad containers and dynamic content
 */
add_action('wp_head', 'nraizes_cls_prevention_styles', 5);
function nraizes_cls_prevention_styles() {
    ?>
    <style id="cls-prevention">
        /* Reserve space for product images */
        .woocommerce-product-gallery { min-height: 400px; aspect-ratio: 1/1; }
        .woocommerce-product-gallery__image { aspect-ratio: 1/1; }
        
        /* Reserve space for product thumbnails */
        .products .product img { aspect-ratio: 1/1; object-fit: cover; }
        
        /* Prevent header shift */
        .site-header { min-height: 80px; }
        
        /* Reserve space for cart widget */
        .widget_shopping_cart { min-height: 50px; }
        
        /* Font loading optimization */
        body { font-display: swap; }
    </style>
    <?php
}

/**
 * Inline critical CSS for above-the-fold content
 */
add_action('wp_head', 'nraizes_critical_css', 2);
function nraizes_critical_css() {
    ?>
    <style id="critical-css">
        /* Critical path CSS - inline for FCP */
        *{box-sizing:border-box}
        body{margin:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;line-height:1.6}
        img{max-width:100%;height:auto}
        .site-header{background:#fff;position:sticky;top:0;z-index:999}
        .woocommerce-products-header{padding:1rem}
        .products{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:1rem}
    </style>
    <?php
}

// ============================================
// ADDITIONAL OPTIMIZATIONS
// ============================================

/**
 * Enable native lazy loading for images
 */
add_filter('wp_lazy_loading_enabled', '__return_true');

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
 * Remove jQuery Migrate (not needed for modern themes)
 */
add_action('wp_default_scripts', 'nraizes_remove_jquery_migrate');
function nraizes_remove_jquery_migrate($scripts) {
    if (!is_admin() && isset($scripts->registered['jquery'])) {
        $script = $scripts->registered['jquery'];
        if ($script->deps) {
            $script->deps = array_diff($script->deps, array('jquery-migrate'));
        }
    }
}

/**
 * Disable XML-RPC (security + performance)
 */
add_filter('xmlrpc_enabled', '__return_false');

/**
 * Remove WordPress version from head
 */
remove_action('wp_head', 'wp_generator');

/**
 * Disable self-pingback
 */
add_action('pre_ping', 'nraizes_disable_self_pingback');
function nraizes_disable_self_pingback(&$links) {
    $home = get_option('home');
    foreach ($links as $l => $link) {
        if (strpos($link, $home) === 0) {
            unset($links[$l]);
        }
    }
}
