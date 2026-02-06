<?php
/**
 * Handler AJAX para add-to-cart no checkout.
 *
 * Adiciona o produto ao carrinho, recalcula totais, e retorna
 * fragmentos HTML atualizados para que o JS substitua no DOM
 * sem recarregar a página.
 *
 * @package NRaizes\CheckoutUpsell
 */

defined( 'ABSPATH' ) || exit;

class NRaizes_Checkout_Upsell_Ajax {

    /**
     * Registra actions AJAX (logado e não-logado para guest checkout).
     */
    public static function init(): void {
        add_action( 'wp_ajax_nraizes_cu_add_to_cart', array( __CLASS__, 'add_to_cart' ) );
        add_action( 'wp_ajax_nopriv_nraizes_cu_add_to_cart', array( __CLASS__, 'add_to_cart' ) );
    }

    /**
     * Adiciona produto ao carrinho via AJAX.
     *
     * Retorna fragmentos atualizados incluindo:
     * - Tabela de revisão do pedido (totais)
     * - Seção de recomendações (sem o produto adicionado)
     * - Barra de frete grátis (se plugin ativo)
     */
    public static function add_to_cart(): void {
        check_ajax_referer( 'nraizes-cu-add-to-cart', 'security' );

        $product_id = isset( $_POST['product_id'] ) ? absint( $_POST['product_id'] ) : 0;

        if ( ! $product_id ) {
            wp_send_json_error( array( 'message' => __( 'Produto inválido.', 'nraizes-checkout-upsell' ) ) );
        }

        $product = wc_get_product( $product_id );
        if ( ! $product || ! $product->is_purchasable() || ! $product->is_in_stock() ) {
            wp_send_json_error( array( 'message' => __( 'Produto indisponível.', 'nraizes-checkout-upsell' ) ) );
        }

        // Adiciona ao carrinho (quantidade 1).
        $cart_item_key = WC()->cart->add_to_cart( $product_id );

        if ( ! $cart_item_key ) {
            wp_send_json_error( array( 'message' => __( 'Não foi possível adicionar ao carrinho.', 'nraizes-checkout-upsell' ) ) );
        }

        // Recalcula totais para shipping e pagamento.
        WC()->cart->calculate_totals();

        // Limpa cache de recomendações (carrinho mudou).
        self::clear_recommendation_cache();

        // Monta fragmentos atualizados.
        $fragments = self::build_fragments();

        wp_send_json_success( array(
            'fragments' => $fragments,
            'cart_hash' => WC()->cart->get_cart_hash(),
        ) );
    }

    /**
     * Limpa o cache de recomendações quando o carrinho muda.
     *
     * Como o cart_hash muda, o transient antigo expira naturalmente,
     * mas limpamos proativamente para garantir dados frescos.
     */
    private static function clear_recommendation_cache(): void {
        global $wpdb;

        // Remove todos os transients de recomendação (são por cart_hash).
        $wpdb->query(
            "DELETE FROM {$wpdb->options}
             WHERE option_name LIKE '_transient_nraizes_cu_recs_%'
             OR option_name LIKE '_transient_timeout_nraizes_cu_recs_%'"
        );
    }

    /**
     * Constrói fragmentos HTML para atualização do DOM.
     *
     * Usa o filtro woocommerce_update_order_review_fragments
     * para que outros plugins (frete grátis, etc.) incluam seus fragmentos.
     *
     * @return array<string, string>
     */
    private static function build_fragments(): array {
        // Fragmento da tabela de totais do pedido.
        ob_start();
        woocommerce_order_review();
        $order_review = ob_get_clean();

        $fragments = array(
            '.woocommerce-checkout-review-order-table' => $order_review,
        );

        /**
         * Dispara o filtro de fragmentos — inclui:
         * - #nraizes-checkout-upsell (nossas recomendações)
         * - #nraizes-fg-bar-wrapper (barra de frete grátis, se ativo)
         * - Qualquer outro plugin que registre fragmentos
         */
        return apply_filters( 'woocommerce_update_order_review_fragments', $fragments );
    }
}
