<?php
/**
 * SEO Improvements (Yoast-Compatible)
 * 
 * Only includes features NOT handled by Yoast SEO:
 * - H1 fixes
 * - Robots.txt optimization
 * - Feed redirects
 * 
 * Disabled (handled by Yoast/Schema plugin):
 * - Meta descriptions
 * - Product schema
 * - Organization schema
 * - Breadcrumb schema
 * 
 * @package Organium-Child
 */

// ============================================
// H1 FIXES
// ============================================

/**
 * Single Product: Replace default title with visible H1
 */
remove_action('woocommerce_single_product_summary', 'woocommerce_template_single_title', 5);
add_action('woocommerce_single_product_summary', 'nraizes_product_h1_title', 5);
function nraizes_product_h1_title() {
    the_title('<h1 class="product_title entry-title">', '</h1>');
}

/**
 * Archive pages: Ensure page title is shown (theme may hide it)
 */
add_filter('woocommerce_show_page_title', '__return_true');

// ============================================
// ROBOTS.TXT OPTIMIZATION
// ============================================

add_filter('robots_txt', 'nraizes_optimize_robots_txt', 9999, 2);
function nraizes_optimize_robots_txt($output, $public) {
    $output = preg_replace('/Disallow:.*\/feed\/(\r?\n)?/i', '', $output);
    $output .= "\nAllow: /feed/\n";
    $output .= "Allow: /*/feed/\n";
    return $output;
}

// ============================================
// FEED OPTIMIZATION
// ============================================

// Remove feed links from header (Yoast handles this better)
add_action('wp_head', 'nraizes_remove_feed_links', 1);
function nraizes_remove_feed_links() {
    remove_action('wp_head', 'feed_links', 2);
    remove_action('wp_head', 'feed_links_extra', 3);
}

// Redirect comment feeds to content
add_action('template_redirect', 'nraizes_redirect_comment_feeds', 5);
function nraizes_redirect_comment_feeds() {
    if (is_feed()) {
        if (is_singular()) {
            wp_redirect(get_permalink(), 301);
            exit;
        } elseif (is_tax() || is_category() || is_tag()) {
            wp_redirect(get_term_link(get_queried_object()), 301);
            exit;
        } else {
            wp_redirect(home_url(), 301);
            exit;
        }
    }
}

// ============================================
// DISABLED - HANDLED BY YOAST SEO
// ============================================
// 
// The following features are commented out because they conflict with
// Yoast SEO Premium and "Schema & Structured Data for WP & AMP" plugins:
//
// - nraizes_optimize_title_tags() - Yoast handles title tags
// - nraizes_meta_descriptions() - Yoast handles meta descriptions  
// - nraizes_product_schema() - Schema plugin handles product schema
// - nraizes_breadcrumbs_schema() - Yoast/Schema handles breadcrumbs
// - nraizes_homepage_schema() - Schema plugin handles organization schema
