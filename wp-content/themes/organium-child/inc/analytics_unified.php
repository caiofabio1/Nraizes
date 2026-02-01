<?php
/**
 * Unified Google Analytics 4 Implementation for Novas Raízes
 * 
 * This file solves the "99% direct/none" traffic attribution issue by:
 * 1. Properly handling consent mode
 * 2. Ensuring correct order of operations
 * 3. Preventing duplicate implementations
 * 4. Maintaining user privacy compliance
 * 
 * @package Organium-Child
 * @version 2.0
 */

// Prevent direct access
if (!defined('ABSPATH')) {
    exit;
}

// Configuration
define('NRAIZES_GA4_ID', 'G-448522931');
define('NRAIZES_GTM_ID', 'GTM-N8LSL5RN');

/**
 * Remove conflicting analytics implementations
 */
add_action('init', 'nraizes_remove_conflicting_analytics', 1);
function nraizes_remove_conflicting_analytics() {
    // Remove old analytics.php implementation if it exists
    remove_action('wp_head', 'nraizes_ga4_script', 1);
    
    // Remove GTM4WP container output to prevent conflicts
    // We'll use their dataLayer but manage the container ourselves
    add_filter('gtm4wp_get_the_gtm_tag', '__return_empty_string');
}

/**
 * Initialize unified analytics implementation
 */
add_action('wp_head', 'nraizes_unified_analytics', 5);
function nraizes_unified_analytics() {
    ?>
    <!-- Novas Raízes Unified Analytics -->
    <script>
        // Initialize dataLayer first (only once)
        window.dataLayer = window.dataLayer || [];
        
        // Helper function for gtag
        function gtag(){dataLayer.push(arguments);}
        
        // CRITICAL: Set default consent BEFORE loading any tags
        // This prevents the "direct/none" issue
        gtag('consent', 'default', {
            'ad_storage': 'denied',
            'ad_user_data': 'denied',
            'ad_personalization': 'denied',
            'analytics_storage': 'granted', // Allow analytics by default for Brazil
            'functionality_storage': 'granted',
            'security_storage': 'granted',
            'region': ['BR'], // Apply to Brazil
            'wait_for_update': 1500
        });
        
        // Stricter consent for EU regions (GDPR)
        gtag('consent', 'default', {
            'ad_storage': 'denied',
            'ad_user_data': 'denied', 
            'ad_personalization': 'denied',
            'analytics_storage': 'denied',
            'functionality_storage': 'denied',
            'security_storage': 'denied',
            'region': ['AT','BE','BG','CH','CY','CZ','DE','DK','EE','ES','FI','FR','GB','GR','HR','HU','IE','IS','IT','LI','LT','LU','LV','MT','NL','NO','PL','PT','RO','SE','SI','SK'],
            'wait_for_update': 1500
        });
    </script>
    
    <!-- Google Tag Manager -->
    <script async src="https://www.googletagmanager.com/gtm.js?id=<?php echo NRAIZES_GTM_ID; ?>"></script>
    <script>
        // Load GTM after consent is set
        window.dataLayer.push({
            'gtm.start': new Date().getTime(),
            'event': 'gtm.js'
        });
    </script>
    
    <!-- Google Analytics 4 -->
    <script async src="https://www.googletagmanager.com/gtag/js?id=<?php echo NRAIZES_GA4_ID; ?>"></script>
    <script>
        // Configure GA4 after consent
        gtag('js', new Date());
        
        // Configure GA4 with proper settings
        gtag('config', '<?php echo NRAIZES_GA4_ID; ?>', {
            'send_page_view': false, // We'll send this via GTM to avoid duplicates
            'cookie_flags': 'SameSite=None;Secure',
            'link_attribution': true
        });
    </script>
    
    <!-- Consent Update Handler -->
    <script>
        // Listen for consent updates from cookie banner
        window.addEventListener('CookiebotOnAccept', function() {
            gtag('consent', 'update', {
                'analytics_storage': Cookiebot.consent.statistics ? 'granted' : 'denied',
                'ad_storage': Cookiebot.consent.marketing ? 'granted' : 'denied',
                'ad_user_data': Cookiebot.consent.marketing ? 'granted' : 'denied',
                'ad_personalization': Cookiebot.consent.marketing ? 'granted' : 'denied'
            });
        });
        
        // Alternative consent update for other cookie banners
        document.addEventListener('wpconsentapi_consent_update', function(e) {
            if (e.detail && e.detail.consents) {
                gtag('consent', 'update', {
                    'analytics_storage': e.detail.consents.statistics ? 'granted' : 'denied',
                    'ad_storage': e.detail.consents.marketing ? 'granted' : 'denied',
                    'ad_user_data': e.detail.consents.marketing ? 'granted' : 'denied',
                    'ad_personalization': e.detail.consents.marketing ? 'granted' : 'denied'
                });
            }
        });
    </script>
    
    <!-- GTM noscript fallback -->
    <noscript>
        <iframe src="https://www.googletagmanager.com/ns.html?id=<?php echo NRAIZES_GTM_ID; ?>"
        height="0" width="0" style="display:none;visibility:hidden"></iframe>
    </noscript>
    <?php
}

/**
 * Enhanced E-commerce tracking functions
 * These work with both GA4 direct and GTM
 */

/**
 * Track product view
 */
add_action('woocommerce_after_single_product', 'nraizes_track_product_view', 20);
function nraizes_track_product_view() {
    global $product;
    
    if (!$product) return;
    
    $categories = get_the_terms($product->get_id(), 'product_cat');
    $category_name = !empty($categories) ? $categories[0]->name : 'Uncategorized';
    
    ?>
    <script>
        // Push to dataLayer for GTM
        window.dataLayer.push({ecommerce: null}); // Clear previous ecommerce data
        window.dataLayer.push({
            'event': 'view_item',
            'ecommerce': {
                'currency': 'BRL',
                'value': <?php echo $product->get_price(); ?>,
                'items': [{
                    'item_id': '<?php echo esc_js($product->get_sku() ?: $product->get_id()); ?>',
                    'item_name': '<?php echo esc_js($product->get_name()); ?>',
                    'item_category': '<?php echo esc_js($category_name); ?>',
                    'price': <?php echo $product->get_price(); ?>,
                    'quantity': 1
                }]
            }
        });
    </script>
    <?php
}

/**
 * Track add to cart events
 */
add_action('wp_footer', 'nraizes_track_add_to_cart');
function nraizes_track_add_to_cart() {
    if (!is_product() && !is_shop() && !is_product_category()) return;
    ?>
    <script>
        jQuery(document).ready(function($) {
            // Track add to cart
            $(document.body).on('added_to_cart', function(event, fragments, cart_hash, $button) {
                var productData = $button.data('product_data');
                
                if (!productData) {
                    // Fallback: extract from DOM
                    var $productRow = $button.closest('.product, .cart');
                    productData = {
                        name: $productRow.find('.woocommerce-loop-product__title, .product_title').text().trim() || 'Product',
                        price: parseFloat($productRow.find('.price .amount').first().text().replace(/[^\d,\.]/g, '').replace(',', '.')) || 0,
                        id: $button.data('product_id') || '',
                        sku: $button.data('product_sku') || ''
                    };
                }
                
                // Push to dataLayer
                window.dataLayer.push({ecommerce: null});
                window.dataLayer.push({
                    'event': 'add_to_cart',
                    'ecommerce': {
                        'currency': 'BRL',
                        'value': productData.price,
                        'items': [{
                            'item_id': productData.sku || productData.id,
                            'item_name': productData.name,
                            'price': productData.price,
                            'quantity': 1
                        }]
                    }
                });
            });
        });
    </script>
    <?php
}

/**
 * Track checkout begin
 */
add_action('woocommerce_before_checkout_form', 'nraizes_track_begin_checkout', 5);
function nraizes_track_begin_checkout() {
    $cart = WC()->cart;
    $items = array();
    
    foreach ($cart->get_cart() as $item) {
        $product = $item['data'];
        $categories = get_the_terms($product->get_id(), 'product_cat');
        $category_name = !empty($categories) ? $categories[0]->name : 'Uncategorized';
        
        $items[] = array(
            'item_id' => $product->get_sku() ?: $product->get_id(),
            'item_name' => $product->get_name(),
            'item_category' => $category_name,
            'price' => $product->get_price(),
            'quantity' => $item['quantity']
        );
    }
    ?>
    <script>
        window.dataLayer.push({ecommerce: null});
        window.dataLayer.push({
            'event': 'begin_checkout',
            'ecommerce': {
                'currency': 'BRL',
                'value': <?php echo $cart->get_total('edit'); ?>,
                'items': <?php echo wp_json_encode($items); ?>
            }
        });
    </script>
    <?php
}

/**
 * Track purchase completion
 */
add_action('woocommerce_thankyou', 'nraizes_track_purchase', 5);
function nraizes_track_purchase($order_id) {
    if (!$order_id) return;
    
    // Prevent duplicate tracking
    if (get_post_meta($order_id, '_ga4_tracked', true)) return;
    
    $order = wc_get_order($order_id);
    $items = array();
    
    foreach ($order->get_items() as $item) {
        $product = $item->get_product();
        if ($product) {
            $categories = get_the_terms($product->get_id(), 'product_cat');
            $category_name = !empty($categories) ? $categories[0]->name : 'Uncategorized';
            
            $items[] = array(
                'item_id' => $product->get_sku() ?: $product->get_id(),
                'item_name' => $item->get_name(),
                'item_category' => $category_name,
                'price' => $order->get_item_total($item, false),
                'quantity' => $item->get_quantity()
            );
        }
    }
    ?>
    <script>
        window.dataLayer.push({ecommerce: null});
        window.dataLayer.push({
            'event': 'purchase',
            'ecommerce': {
                'transaction_id': '<?php echo esc_js($order_id); ?>',
                'currency': 'BRL',
                'value': <?php echo $order->get_total(); ?>,
                'tax': <?php echo $order->get_total_tax(); ?>,
                'shipping': <?php echo $order->get_shipping_total(); ?>,
                'items': <?php echo wp_json_encode($items); ?>
            }
        });
    </script>
    <?php
    
    // Mark as tracked
    update_post_meta($order_id, '_ga4_tracked', true);
}

/**
 * Track custom events (WhatsApp, scroll depth, etc.)
 */
add_action('wp_footer', 'nraizes_track_custom_events', 100);
function nraizes_track_custom_events() {
    ?>
    <script>
        // Track WhatsApp clicks
        jQuery(document).ready(function($) {
            $('a[href*="wa.me"], a[href*="whatsapp"], .whatsapp-button, [class*="whatsapp"]').on('click', function() {
                window.dataLayer.push({
                    'event': 'contact_whatsapp',
                    'page_location': window.location.href,
                    'link_url': $(this).attr('href') || 'unknown'
                });
            });
        });
        
        // Track scroll depth on content pages
        <?php if (is_product() || is_singular('post')) : ?>
        (function() {
            var scrollMarkers = [25, 50, 75, 90, 100];
            var markersSent = {};
            var maxScroll = 0;
            
            function trackScroll() {
                var scrollPercent = Math.round((window.scrollY / (document.documentElement.scrollHeight - window.innerHeight)) * 100);
                
                if (scrollPercent > maxScroll) {
                    maxScroll = scrollPercent;
                    
                    scrollMarkers.forEach(function(marker) {
                        if (maxScroll >= marker && !markersSent[marker]) {
                            markersSent[marker] = true;
                            window.dataLayer.push({
                                'event': 'scroll_depth',
                                'percent_scrolled': marker
                            });
                        }
                    });
                }
            }
            
            var scrollTimer;
            window.addEventListener('scroll', function() {
                clearTimeout(scrollTimer);
                scrollTimer = setTimeout(trackScroll, 100);
            });
        })();
        <?php endif; ?>
    </script>
    <?php
}

/**
 * Add UTM preservation for better attribution
 */
add_action('wp_footer', 'nraizes_preserve_utm_parameters');
function nraizes_preserve_utm_parameters() {
    ?>
    <script>
        // Preserve UTM parameters across the site
        (function() {
            var utmParams = ['utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content', 'gclid', 'fbclid'];
            var urlParams = new URLSearchParams(window.location.search);
            var hasUTM = false;
            var utmString = '';
            
            utmParams.forEach(function(param) {
                if (urlParams.has(param)) {
                    hasUTM = true;
                    utmString += (utmString ? '&' : '?') + param + '=' + urlParams.get(param);
                }
            });
            
            if (hasUTM) {
                // Store UTM parameters in session
                sessionStorage.setItem('nraizes_utm', utmString);
                
                // Add UTM to internal links
                document.addEventListener('DOMContentLoaded', function() {
                    var links = document.querySelectorAll('a[href*="nraizes.com.br"]');
                    links.forEach(function(link) {
                        var href = link.getAttribute('href');
                        if (href && !href.includes('utm_') && !href.includes('gclid') && !href.includes('fbclid')) {
                            var separator = href.includes('?') ? '&' : '?';
                            link.setAttribute('href', href + separator + utmString.substring(1));
                        }
                    });
                });
            } else {
                // Check if we have stored UTM parameters
                var storedUTM = sessionStorage.getItem('nraizes_utm');
                if (storedUTM) {
                    // Reapply stored UTM to internal links
                    document.addEventListener('DOMContentLoaded', function() {
                        var links = document.querySelectorAll('a[href*="nraizes.com.br"]');
                        links.forEach(function(link) {
                            var href = link.getAttribute('href');
                            if (href && !href.includes('utm_') && !href.includes('gclid') && !href.includes('fbclid')) {
                                var separator = href.includes('?') ? '&' : '?';
                                link.setAttribute('href', href + separator + storedUTM.substring(1));
                            }
                        });
                    });
                }
            }
        })();
    </script>
    <?php
}