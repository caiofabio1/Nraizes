<?php
/**
 * Organium Child Theme — Minimal Bootstrap
 * 
 * Só carrega o CSS do tema pai. Nenhum módulo extra.
 * Ative o child theme e confirme que funciona antes de adicionar módulos.
 */

add_action( 'wp_enqueue_scripts', 'organium_child_enqueue' );
function organium_child_enqueue() {
    wp_enqueue_style(
        'organium-child-style',
        get_stylesheet_uri(),
        array( 'organium-style' ),
        wp_get_theme()->get( 'Version' )
    );
}
