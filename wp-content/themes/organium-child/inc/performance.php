<?php
/**
 * Performance Optimizations - Enhanced for Mobile PageSpeed
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
    // Homepage/shop LCP - only preload on shop page (not front page which uses Elementor)
    if (is_shop() && !is_front_page()) {
        $args = array(
            'post_type' => 'product',
            'posts_per_page' => 1,
            'post_status' => 'publish',
            'orderby' => 'menu_order',
            'order' => 'ASC',
        );
        $products = get_posts($args);
        if (!empty($products)) {
            $image_id = get_post_thumbnail_id($products[0]->ID);
            if ($image_id) {
                $image_src = wp_get_attachment_image_src($image_id, 'woocommerce_thumbnail');
                if ($image_src) {
                    echo '<link rel="preload" as="image" href="' . esc_url($image_src[0]) . '" fetchpriority="high">';
                }
            }
        }
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
function nraizes_shop_first_images($image, $product = null, $size = '', $attr = array(), $placeholder = true) {
    global $woocommerce_loop;
    $loop_index = isset($woocommerce_loop['loop']) ? $woocommerce_loop['loop'] : 0;
    
    // First row of products - above fold, no lazy loading
    if ($loop_index <= 4) {
        $image = str_replace(' loading="lazy"', '', $image);
        if (strpos($image, 'fetchpriority') === false) {
            $image = str_replace('<img ', '<img fetchpriority="high" ', $image);
        }
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
        'gtm4wp', 'google_gtagjs', 'google-recaptcha',
        'directorist-main-script', 'directorist-select2',
        'sbi-scripts', 'instagram-feed', 'prettyPhoto',
        'yith-wcwl-main', 'jquery-selectBox'
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
    if (in_array($handle, $defer) || strpos($handle, 'elementor') !== false || strpos($handle, 'directorist') !== false) {
        return str_replace(' src=', ' defer src=', $tag);
    }
    
    return $tag;
}

/**
 * Remove unnecessary scripts and styles on specific pages
 */
add_action('wp_enqueue_scripts', 'nraizes_remove_unnecessary_scripts', 999);
function nraizes_remove_unnecessary_scripts() {
    // Remove Gutenberg block CSS if not using blocks
    if (!is_singular()) {
        wp_dequeue_style('wp-block-library');
        wp_dequeue_style('wp-block-library-theme');
        wp_dequeue_style('wc-blocks-style');
    }
    
    // Remove cart fragments from non-cart pages (big TBT reducer)
    if (!is_cart() && !is_checkout() && !is_woocommerce()) {
        wp_dequeue_script('wc-cart-fragments');
    }
    
    // Remove comment-reply JS if not needed
    if (!is_singular() || !comments_open()) {
        wp_dequeue_script('comment-reply');
    }
    
    // Remove emoji scripts (saves ~20KB)
    remove_action('wp_head', 'print_emoji_detection_script', 7);
    remove_action('wp_print_styles', 'print_emoji_styles');
    
    // Remove oEmbed
    remove_action('wp_head', 'wp_oembed_add_discovery_links');
    remove_action('wp_head', 'wp_oembed_add_host_js');
    
    // Remove Directorist CSS/JS on non-directory pages
    if (!is_post_type_archive('at_biz_dir') && !is_singular('at_biz_dir')) {
        wp_dequeue_style('directorist-main-style');
        wp_dequeue_style('directorist-select2-style');
        wp_dequeue_style('directorist-ez-media-uploader-style');
        wp_dequeue_style('directorist-swiper-style');
        wp_dequeue_style('directorist-sweetalert-style');
        wp_dequeue_style('directorist-openstreet-map-leaflet');
        wp_dequeue_style('directorist-openstreet-map-openstreet');
        wp_dequeue_style('directorist-account-button-style');
        wp_dequeue_style('directorist-blocks-common');
        wp_dequeue_script('directorist-main-script');
        wp_dequeue_script('directorist-select2');
    }
    
    // Remove prettyPhoto on non-product pages (WooCommerce lightbox)
    if (!is_product()) {
        wp_dequeue_style('woocommerce_prettyPhoto_css');
        wp_dequeue_script('prettyPhoto');
        wp_dequeue_script('prettyPhoto-init');
    }
}

/**
 * Delay non-essential JS execution until user interaction
 */
add_action('wp_footer', 'nraizes_delay_scripts_until_interaction', 999);
function nraizes_delay_scripts_until_interaction() {
    ?>
    <script>
    (function() {
        var triggered = false;
        function go() {
            if (triggered) return;
            triggered = true;
            document.dispatchEvent(new CustomEvent('nraizes:interaction'));
        }
        ['scroll', 'click', 'touchstart', 'mousemove', 'keydown'].forEach(function(e) {
            window.addEventListener(e, go, {once: true, passive: true});
        });
        setTimeout(go, 5000);
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
 * Inline critical CSS for above-the-fold content + CLS prevention
 */
add_action('wp_head', 'nraizes_critical_css', 2);
function nraizes_critical_css() {
    ?>
    <style id="critical-css">
        /* Critical path CSS - inline for FCP */
        *{box-sizing:border-box;-webkit-box-sizing:border-box}
        body{margin:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Oxygen,Ubuntu,Cantarell,"Helvetica Neue",sans-serif;line-height:1.6;overflow-x:hidden}
        img{max-width:100%;height:auto;display:block}
        .site-header{background:#fff;position:-webkit-sticky;position:sticky;top:0;z-index:999}
        .woocommerce-products-header{padding:1rem}
        .products{display:-webkit-box;display:-ms-flexbox;display:flex;-ms-flex-wrap:wrap;flex-wrap:wrap;gap:1rem}
        @supports(display:grid){.products{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:1rem}}
        .products li.product{-webkit-box-flex:0;-ms-flex:0 0 calc(25% - 1rem);flex:0 0 calc(25% - 1rem)}

        /* CLS Prevention - Reserve space */
        .woocommerce-product-gallery{min-height:300px}
        .products .product img{-o-object-fit:cover;object-fit:cover;width:100%;height:auto}
        @supports(aspect-ratio:1/1){
            .woocommerce-product-gallery,.woocommerce-product-gallery__image{aspect-ratio:1/1;min-height:auto}
            .products .product img{aspect-ratio:1/1}
        }
        .site-header,.organium_header{min-height:60px}
        .widget_shopping_cart{min-height:40px}

        /* Mobile: 2 columns, prevent overflow */
        @media(max-width:767px){
            .products{display:-webkit-box!important;display:-ms-flexbox!important;display:flex!important;-ms-flex-wrap:wrap!important;flex-wrap:wrap!important;gap:10px}
            @supports(display:grid){.products{display:grid!important;grid-template-columns:repeat(2,1fr)!important;gap:10px}}
            .products li.product{-webkit-box-flex:0;-ms-flex:0 0 calc(50% - 5px);flex:0 0 calc(50% - 5px)}
            .woocommerce-product-gallery{min-height:auto}
            @supports(aspect-ratio:1/1){.woocommerce-product-gallery{aspect-ratio:auto}}
            .site-header,.organium_header{min-height:auto}
        }
        @media(max-width:374px){
            @supports(display:grid){.products{grid-template-columns:1fr!important}}
            .products li.product{-webkit-box-flex:0;-ms-flex:0 0 100%;flex:0 0 100%}
        }

        /* Font swap to prevent FOIT */
        @font-face{font-display:swap}
    </style>
    <?php
}

// ============================================
// RESOURCE HINTS
// ============================================

/**
 * Enable native lazy loading for images
 */
add_filter('wp_lazy_loading_enabled', '__return_true');

/**
 * Preconnect to external resources
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

// ============================================
// WOOCOMMERCE OPTIMIZATION
// ============================================

/**
 * Optimize WooCommerce - disable cart fragments on non-cart pages
 */
add_action('wp', 'nraizes_optimize_woocommerce');
function nraizes_optimize_woocommerce() {
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

// ============================================
// SECURITY + MISC
// ============================================

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
