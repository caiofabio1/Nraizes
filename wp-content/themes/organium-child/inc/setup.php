<?php
/**
 * Theme Setup and Enqueue
 * 
 * @package Organium-Child
 */

add_action('wp_enqueue_scripts', 'nraizes_enqueue_styles');
function nraizes_enqueue_styles() {
    if (class_exists('WooCommerce')) {
        wp_enqueue_style('child-style', get_stylesheet_directory_uri() . '/style.css', array('organium-theme', 'organium-style', 'organium-woocommerce'));
    } else {
        wp_enqueue_style('child-style', get_stylesheet_directory_uri() . '/style.css', array('organium-theme', 'organium-style'));
    }
}
