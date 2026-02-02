<?php
/**
 * Mobile Enhancements
 * 
 * @package Organium-Child
 * @version 2.0.0
 */

// ============================================
// VIEWPORT FIX - Allow pinch-to-zoom (Accessibility)
// ============================================

/**
 * Fix viewport meta: remove maximum-scale=1 to allow zoom
 * The Organium theme sets maximum-scale=1 which blocks pinch-to-zoom
 * This is a WCAG 2.1 Level AA violation (Success Criterion 1.4.4)
 */
add_action('wp_head', 'nraizes_fix_viewport_meta', 1);
function nraizes_fix_viewport_meta() {
    ?>
    <script>
    (function() {
        var viewport = document.querySelector('meta[name="viewport"]');
        if (viewport) {
            var content = viewport.getAttribute('content');
            content = content.replace(/,?\s*maximum-scale\s*=\s*[^,]*/gi, '');
            content = content.replace(/,?\s*user-scalable\s*=\s*no/gi, '');
            viewport.setAttribute('content', content.replace(/^,\s*/, ''));
        }
    })();
    </script>
    <?php
}

// ============================================
// MOBILE NAVIGATION
// ============================================

/**
 * Improve mobile menu touch targets and accessibility
 */
add_action('wp_footer', 'nraizes_mobile_menu_enhancements');
function nraizes_mobile_menu_enhancements() {
    if (!wp_is_mobile()) return;
    ?>
    <script>
    document.addEventListener('DOMContentLoaded', function() {
        // Ensure mobile menu items have proper touch target sizes
        var menuLinks = document.querySelectorAll('.mobile-menu a, .organium_mobile_menu a, nav.mobile-nav a');
        menuLinks.forEach(function(link) {
            link.style.minHeight = '48px';
            link.style.display = 'flex';
            link.style.alignItems = 'center';
            link.style.padding = '12px 16px';
        });
        
        // Close mobile menu on backdrop click
        var menuOverlay = document.querySelector('.mobile-menu-overlay, .organium_mobile_overlay');
        if (menuOverlay) {
            menuOverlay.addEventListener('click', function() {
                var closeBtn = document.querySelector('.mobile-menu-close, .organium_mobile_menu_close');
                if (closeBtn) closeBtn.click();
            });
        }
    });
    </script>
    <?php
}

// ============================================
// STICKY ADD-TO-CART ON MOBILE
// ============================================

/**
 * Add sticky add-to-cart bar on product pages for mobile
 */
add_action('wp_footer', 'nraizes_sticky_add_to_cart');
function nraizes_sticky_add_to_cart() {
    if (!is_product()) return;
    
    global $product;
    if (!$product) return;
    
    $price = $product->get_price_html();
    $name = $product->get_name();
    ?>
    <div id="nraizes-sticky-cart" class="nraizes-sticky-cart" style="display:none;">
        <div class="nraizes-sticky-cart__info">
            <span class="nraizes-sticky-cart__name"><?php echo esc_html(wp_trim_words($name, 5)); ?></span>
            <span class="nraizes-sticky-cart__price"><?php echo $price; ?></span>
        </div>
        <button class="nraizes-sticky-cart__btn" onclick="document.querySelector('.single_add_to_cart_button')?.click()">
            Comprar
        </button>
    </div>
    <script>
    (function() {
        var stickyCart = document.getElementById('nraizes-sticky-cart');
        var addToCartBtn = document.querySelector('.single_add_to_cart_button');
        if (!stickyCart || !addToCartBtn) return;
        
        // Only show on mobile
        if (window.innerWidth > 767) return;
        
        var observer = new IntersectionObserver(function(entries) {
            entries.forEach(function(entry) {
                stickyCart.style.display = entry.isIntersecting ? 'none' : 'flex';
            });
        }, { threshold: 0 });
        
        observer.observe(addToCartBtn);
    })();
    </script>
    <?php
}

// ============================================
// SEO FIXES
// ============================================

/**
 * Fix shop page title: Replace old brand name "Mivegan" with "Novas Raizes"
 */
add_filter('woocommerce_page_title', 'nraizes_fix_shop_title');
function nraizes_fix_shop_title($title) {
    $title = str_replace('Mivegan', 'Novas Raizes', $title);
    return $title;
}

/**
 * Fix document title for shop page
 */
add_filter('pre_get_document_title', 'nraizes_fix_document_title', 20);
function nraizes_fix_document_title($title) {
    if (function_exists('is_shop') && is_shop()) {
        return 'Loja - Produtos Naturais e Formulas Chinesas | Novas Raizes';
    }
    return $title;
}

/**
 * Fix Yoast SEO title for shop page
 */
add_filter('wpseo_title', 'nraizes_fix_yoast_title', 20);
function nraizes_fix_yoast_title($title) {
    $title = str_replace('Mivegan', 'Novas Raizes', $title);
    return $title;
}

/**
 * Fix Yoast SEO description for shop page
 */
add_filter('wpseo_metadesc', 'nraizes_fix_yoast_desc', 20);
function nraizes_fix_yoast_desc($desc) {
    $desc = str_replace('Mivegan', 'Novas Raizes', $desc);
    return $desc;
}

// ============================================
// MOBILE-SPECIFIC WOOCOMMERCE
// ============================================

/**
 * Reduce cross-sells to 2 columns on mobile
 */
add_filter('woocommerce_cross_sells_columns', 'nraizes_mobile_cross_sells_columns');
function nraizes_mobile_cross_sells_columns($columns) {
    if (wp_is_mobile()) {
        return 2;
    }
    return $columns;
}

/**
 * Show fewer products per page on mobile for faster loading
 */
add_filter('loop_shop_per_page', 'nraizes_mobile_products_per_page');
function nraizes_mobile_products_per_page($cols) {
    if (wp_is_mobile()) {
        return 12; // Less products, faster load
    }
    return $cols;
}

/**
 * Optimize WooCommerce gallery for mobile - disable zoom, enable swipe
 */
add_action('wp_footer', 'nraizes_mobile_gallery_settings');
function nraizes_mobile_gallery_settings() {
    if (!is_product() || !wp_is_mobile()) return;
    ?>
    <script>
    document.addEventListener('DOMContentLoaded', function() {
        // Disable zoom on mobile (requires a large image download), enable swipe
        if (typeof jQuery !== 'undefined' && jQuery.fn.flexslider) {
            var gallery = jQuery('.woocommerce-product-gallery');
            if (gallery.length) {
                gallery.flexslider({
                    touch: true,
                    smoothHeight: true
                });
            }
        }
    });
    </script>
    <?php
}

// ============================================
// TOUCH TARGET FIXES
// ============================================

/**
 * Ensure all interactive elements meet 44x44px minimum (WCAG)
 * This is done via CSS in style.css, but we add inline styles as fallback
 */
add_action('wp_head', 'nraizes_touch_target_styles', 10);
function nraizes_touch_target_styles() {
    if (!wp_is_mobile()) return;
    ?>
    <style id="touch-targets">
        /* Ensure minimum 44px touch targets on mobile */
        @media (max-width: 767px) {
            .woocommerce a.remove { 
                width: 44px !important; 
                height: 44px !important; 
                line-height: 44px !important;
                font-size: 1.5em !important;
                display: flex !important;
                align-items: center;
                justify-content: center;
            }
            .woocommerce .quantity .qty {
                min-height: 44px;
                min-width: 60px;
                font-size: 16px; /* Prevents iOS zoom on focus */
            }
            input[type="text"],
            input[type="email"],
            input[type="tel"],
            input[type="number"],
            input[type="search"],
            input[type="password"],
            textarea,
            select {
                font-size: 16px !important; /* Prevents iOS zoom on input focus */
                min-height: 44px;
            }
            .woocommerce-pagination a,
            .woocommerce-pagination span {
                min-width: 44px;
                min-height: 44px;
                display: inline-flex;
                align-items: center;
                justify-content: center;
            }
        }
    </style>
    <?php
}
