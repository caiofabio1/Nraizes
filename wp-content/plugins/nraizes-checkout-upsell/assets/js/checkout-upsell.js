/**
 * NRaizes Checkout Upsell — Add-to-cart via AJAX.
 *
 * - Event delegation (funciona após fragment replacement)
 * - Atualiza totais, recomendações e barra de frete via fragments
 * - Feedback visual: loading → added → fade out
 *
 * @package NRaizes\CheckoutUpsell
 */
(function( $ ) {
    'use strict';

    if ( typeof nraizesCU === 'undefined' ) {
        return;
    }

    // Event delegation — sobrevive a fragment replacement.
    $( document.body ).on( 'click', '.js-nraizes-cu-add', function( e ) {
        e.preventDefault();

        var $btn       = $( this );
        var $item      = $btn.closest( '.nraizes-checkout-upsell__item' );
        var productId  = $btn.data( 'product-id' );

        // Previne duplo-clique.
        if ( $btn.hasClass( 'is-loading' ) ) {
            return;
        }

        var originalText = $btn.text();
        $btn.addClass( 'is-loading' ).text( nraizesCU.i18n.adding );

        $.ajax({
            type: 'POST',
            url:  nraizesCU.ajax_url,
            data: {
                action:     'nraizes_cu_add_to_cart',
                product_id: productId,
                security:   nraizesCU.nonce
            },
            success: function( response ) {
                if ( response.success && response.data.fragments ) {
                    // Substitui fragmentos no DOM.
                    $.each( response.data.fragments, function( selector, html ) {
                        $( selector ).replaceWith( html );
                    });

                    // Dispara recálculo nativo do WooCommerce (shipping, payment, etc).
                    $( document.body ).trigger( 'update_checkout' );

                    // Feedback visual: "Adicionado!" + fade out do card.
                    $btn.removeClass( 'is-loading' )
                        .addClass( 'is-added' )
                        .text( nraizesCU.i18n.added );

                    $item.delay( 600 ).fadeOut( 300, function() {
                        $( this ).remove();

                        // Se não sobrou nenhum card, esconde a seção.
                        var $grid = $( '.nraizes-checkout-upsell__grid' );
                        if ( $grid.length && $grid.children().length === 0 ) {
                            $( '.nraizes-checkout-upsell' ).fadeOut( 200 );
                        }
                    });
                } else {
                    $btn.removeClass( 'is-loading' ).text( originalText );
                }
            },
            error: function() {
                $btn.removeClass( 'is-loading' ).text( nraizesCU.i18n.error );
                setTimeout( function() {
                    $btn.text( originalText );
                }, 2000 );
            }
        });
    });

})( jQuery );
