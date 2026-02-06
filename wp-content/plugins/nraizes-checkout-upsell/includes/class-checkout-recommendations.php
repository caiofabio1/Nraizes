<?php
/**
 * Engine de recomendações e renderização no checkout.
 *
 * Agrega dados de "frequentemente comprados juntos" (FBT) de todos
 * os produtos do carrinho, rankeia por frequência cruzada, e exibe
 * cards compactos com add-to-cart via AJAX.
 *
 * Reutiliza funções do tema (cro.php) via function_exists(),
 * com fallback interno caso o tema mude.
 *
 * @package NRaizes\CheckoutUpsell
 */

defined( 'ABSPATH' ) || exit;

class NRaizes_Checkout_Recommendations {

    /**
     * Registra hooks.
     */
    public static function init(): void {
        // Settings no admin (WooCommerce > Produtos > Checkout Recommendations).
        add_filter( 'woocommerce_get_sections_products', array( __CLASS__, 'add_settings_section' ) );
        add_filter( 'woocommerce_get_settings_products', array( __CLASS__, 'get_settings' ), 10, 2 );

        // Renderização no checkout — hook dinâmico conforme configuração.
        $position = get_option( 'nraizes_cu_position', 'before_submit' );
        $hook     = 'before_submit' === $position
            ? 'woocommerce_review_order_before_submit'
            : 'woocommerce_after_order_notes';
        add_action( $hook, array( __CLASS__, 'render_recommendations' ) );

        // Assets.
        add_action( 'wp_enqueue_scripts', array( __CLASS__, 'enqueue_assets' ) );

        // Fragment para atualização AJAX.
        add_filter( 'woocommerce_update_order_review_fragments', array( __CLASS__, 'add_fragment' ) );
    }

    // =========================================================================
    // Settings (WooCommerce Settings API)
    // =========================================================================

    /**
     * Adiciona seção em WooCommerce > Produtos.
     *
     * @param array $sections Seções existentes.
     * @return array
     */
    public static function add_settings_section( array $sections ): array {
        $sections['nraizes_checkout_upsell'] = __( 'Checkout Recommendations', 'nraizes-checkout-upsell' );
        return $sections;
    }

    /**
     * Campos de configuração.
     *
     * @param array  $settings        Settings existentes.
     * @param string $current_section Seção ativa.
     * @return array
     */
    public static function get_settings( array $settings, string $current_section ): array {
        if ( 'nraizes_checkout_upsell' !== $current_section ) {
            return $settings;
        }

        return array(
            array(
                'title' => __( 'Recomendações no Checkout', 'nraizes-checkout-upsell' ),
                'type'  => 'title',
                'desc'  => __( 'Exibe produtos frequentemente comprados juntos durante o checkout para aumentar o ticket médio.', 'nraizes-checkout-upsell' ),
                'id'    => 'nraizes_cu_options',
            ),
            array(
                'title'   => __( 'Ativar', 'nraizes-checkout-upsell' ),
                'id'      => 'nraizes_cu_enabled',
                'type'    => 'checkbox',
                'default' => 'yes',
                'desc'    => __( 'Exibir recomendações de produtos no checkout', 'nraizes-checkout-upsell' ),
            ),
            array(
                'title'             => __( 'Número de produtos', 'nraizes-checkout-upsell' ),
                'id'                => 'nraizes_cu_count',
                'type'              => 'number',
                'default'           => 3,
                'custom_attributes' => array( 'min' => 2, 'max' => 4, 'step' => 1 ),
                'desc'              => __( 'Quantidade de produtos recomendados (2–4).', 'nraizes-checkout-upsell' ),
            ),
            array(
                'title'   => __( 'Posição', 'nraizes-checkout-upsell' ),
                'id'      => 'nraizes_cu_position',
                'type'    => 'select',
                'default' => 'before_submit',
                'options' => array(
                    'before_submit' => __( 'Antes do botão Finalizar Compra', 'nraizes-checkout-upsell' ),
                    'after_notes'   => __( 'Após notas do pedido', 'nraizes-checkout-upsell' ),
                ),
                'desc'    => __( 'Onde exibir as recomendações na página de checkout.', 'nraizes-checkout-upsell' ),
            ),
            array(
                'title'   => __( 'Título da seção', 'nraizes-checkout-upsell' ),
                'id'      => 'nraizes_cu_heading',
                'type'    => 'text',
                'default' => __( 'Clientes também compraram', 'nraizes-checkout-upsell' ),
                'desc'    => __( 'Título exibido acima das recomendações.', 'nraizes-checkout-upsell' ),
            ),
            array(
                'title'   => __( 'Excluir categorias', 'nraizes-checkout-upsell' ),
                'id'      => 'nraizes_cu_excluded_cats',
                'type'    => 'multiselect',
                'class'   => 'wc-enhanced-select',
                'options' => self::get_category_options(),
                'default' => '',
                'desc'    => __( 'Categorias cujos produtos não aparecerão como recomendação.', 'nraizes-checkout-upsell' ),
            ),
            array(
                'type' => 'sectionend',
                'id'   => 'nraizes_cu_options',
            ),
        );
    }

    /**
     * Lista de categorias de produto para o multiselect.
     *
     * @return array<int, string>
     */
    private static function get_category_options(): array {
        $terms   = get_terms( array( 'taxonomy' => 'product_cat', 'hide_empty' => false ) );
        $options = array();
        if ( is_array( $terms ) ) {
            foreach ( $terms as $term ) {
                $options[ $term->term_id ] = $term->name;
            }
        }
        return $options;
    }

    // =========================================================================
    // Recommendation Engine
    // =========================================================================

    /**
     * Obtém recomendações agregadas para o carrinho atual.
     *
     * Fluxo:
     * 1. Para cada produto no carrinho, busca FBT (do tema ou fallback).
     * 2. Pontua cada candidato (aparece em mais FBTs = maior score).
     * 3. Fallback: mesma categoria se FBT estiver vazio.
     * 4. Filtra: estoque, purchasable, categorias excluídas.
     * 5. Cache por 1h baseado no hash do carrinho.
     *
     * @return int[] IDs dos produtos recomendados.
     */
    public static function get_recommendations(): array {
        if ( 'yes' !== get_option( 'nraizes_cu_enabled', 'yes' ) ) {
            return array();
        }

        $cart = WC()->cart;
        if ( ! $cart || $cart->is_empty() ) {
            return array();
        }

        // Cache por combinação de carrinho.
        $cart_hash = self::build_cart_hash();
        $cache_key = 'nraizes_cu_recs_' . $cart_hash;
        $cached    = get_transient( $cache_key );
        if ( false !== $cached ) {
            return $cached;
        }

        $max_products  = (int) get_option( 'nraizes_cu_count', 3 );
        $excluded_cats = array_map( 'intval', (array) get_option( 'nraizes_cu_excluded_cats', array() ) );
        $cart_items    = $cart->get_cart();

        $cart_product_ids = array();
        foreach ( $cart_items as $item ) {
            $cart_product_ids[] = (int) $item['product_id'];
        }

        // Fase 1: Agregar FBT de todos os itens do carrinho.
        $candidate_scores = array();
        foreach ( $cart_items as $item ) {
            $product_id = (int) $item['product_id'];
            $fbt_ids    = self::get_fbt_for_product( $product_id );

            foreach ( $fbt_ids as $rank => $fbt_id ) {
                $fbt_id = (int) $fbt_id;
                if ( in_array( $fbt_id, $cart_product_ids, true ) ) {
                    continue;
                }
                if ( ! isset( $candidate_scores[ $fbt_id ] ) ) {
                    $candidate_scores[ $fbt_id ] = 0;
                }
                // Score: mais pontos para ranking mais alto e para aparecer em múltiplos FBTs.
                $candidate_scores[ $fbt_id ] += max( 1, 8 - $rank );
            }
        }

        // Fase 2: Fallback por categoria se não há dados FBT.
        if ( empty( $candidate_scores ) ) {
            foreach ( $cart_items as $item ) {
                $product_id = (int) $item['product_id'];
                $cat_ids    = self::get_category_for_product( $product_id );

                foreach ( $cat_ids as $cat_id ) {
                    $cat_id = (int) $cat_id;
                    if ( in_array( $cat_id, $cart_product_ids, true ) ) {
                        continue;
                    }
                    if ( ! isset( $candidate_scores[ $cat_id ] ) ) {
                        $candidate_scores[ $cat_id ] = 0;
                    }
                    $candidate_scores[ $cat_id ] += 1;
                }
            }
        }

        // Ordena por score (maior primeiro).
        arsort( $candidate_scores );

        // Fase 3: Filtra e limita.
        $recommended = array();
        foreach ( $candidate_scores as $product_id => $score ) {
            if ( count( $recommended ) >= $max_products ) {
                break;
            }

            $product = wc_get_product( $product_id );
            if ( ! $product || ! $product->is_purchasable() || ! $product->is_in_stock() ) {
                continue;
            }

            // Excluir categorias bloqueadas.
            if ( ! empty( $excluded_cats ) ) {
                $product_cats = wp_get_post_terms( $product_id, 'product_cat', array( 'fields' => 'ids' ) );
                if ( array_intersect( $product_cats, $excluded_cats ) ) {
                    continue;
                }
            }

            $recommended[] = $product_id;
        }

        set_transient( $cache_key, $recommended, HOUR_IN_SECONDS );

        return $recommended;
    }

    /**
     * Obtém FBT para um produto — reutiliza tema ou usa fallback.
     *
     * @param int $product_id ID do produto.
     * @return int[]
     */
    private static function get_fbt_for_product( int $product_id ): array {
        if ( function_exists( 'nraizes_get_frequently_bought_together' ) ) {
            return (array) nraizes_get_frequently_bought_together( $product_id );
        }
        return self::get_fbt_fallback( $product_id );
    }

    /**
     * Obtém produtos da mesma categoria — reutiliza tema ou usa fallback.
     *
     * @param int $product_id ID do produto.
     * @return int[]
     */
    private static function get_category_for_product( int $product_id ): array {
        if ( function_exists( 'nraizes_get_same_category_products' ) ) {
            return (array) nraizes_get_same_category_products( $product_id );
        }
        return self::get_category_fallback( $product_id );
    }

    /**
     * Fallback FBT — cópia da lógica do tema para funcionar sem ele.
     * Usa o mesmo cache key `nraizes_fbt_{id}` para compartilhar cache.
     *
     * @param int $product_id ID do produto.
     * @return int[]
     */
    private static function get_fbt_fallback( int $product_id ): array {
        global $wpdb;

        $cache_key = 'nraizes_fbt_' . $product_id;
        $cached    = get_transient( $cache_key );
        if ( false !== $cached ) {
            return $cached;
        }

        $order_ids = $wpdb->get_col( $wpdb->prepare(
            "SELECT DISTINCT order_id
             FROM {$wpdb->prefix}woocommerce_order_items oi
             INNER JOIN {$wpdb->prefix}woocommerce_order_itemmeta oim
                 ON oi.order_item_id = oim.order_item_id
             WHERE oim.meta_key = '_product_id'
             AND oim.meta_value = %d
             LIMIT 100",
            $product_id
        ) );

        if ( empty( $order_ids ) ) {
            set_transient( $cache_key, array(), DAY_IN_SECONDS );
            return array();
        }

        $placeholders = implode( ',', array_fill( 0, count( $order_ids ), '%d' ) );
        $query        = $wpdb->prepare(
            "SELECT oim.meta_value as product_id, COUNT(*) as frequency
             FROM {$wpdb->prefix}woocommerce_order_items oi
             INNER JOIN {$wpdb->prefix}woocommerce_order_itemmeta oim
                 ON oi.order_item_id = oim.order_item_id
             WHERE oi.order_id IN ($placeholders)
             AND oim.meta_key = '_product_id'
             AND oim.meta_value != %d
             GROUP BY oim.meta_value
             ORDER BY frequency DESC
             LIMIT 8",
            array_merge( $order_ids, array( $product_id ) )
        );

        $results     = $wpdb->get_results( $query );
        $product_ids = array();

        foreach ( $results as $row ) {
            if ( 'publish' === get_post_status( $row->product_id ) ) {
                $product_ids[] = (int) $row->product_id;
            }
        }

        set_transient( $cache_key, $product_ids, DAY_IN_SECONDS );

        return $product_ids;
    }

    /**
     * Fallback categoria — cópia da lógica do tema.
     *
     * @param int $product_id ID do produto.
     * @return int[]
     */
    private static function get_category_fallback( int $product_id ): array {
        $terms = get_the_terms( $product_id, 'product_cat' );
        if ( empty( $terms ) || is_wp_error( $terms ) ) {
            return array();
        }

        $category_ids = wp_list_pluck( $terms, 'term_id' );

        $products = get_posts( array(
            'post_type'      => 'product',
            'posts_per_page' => 8,
            'post_status'    => 'publish',
            'post__not_in'   => array( $product_id ),
            'orderby'        => 'rand',
            'tax_query'      => array(
                array(
                    'taxonomy' => 'product_cat',
                    'field'    => 'term_id',
                    'terms'    => $category_ids,
                ),
            ),
        ) );

        return ! empty( $products ) ? wp_list_pluck( $products, 'ID' ) : array();
    }

    /**
     * Hash determinístico do carrinho (sorted product IDs).
     *
     * @return string
     */
    private static function build_cart_hash(): string {
        $ids = array();
        foreach ( WC()->cart->get_cart() as $item ) {
            $ids[] = (int) $item['product_id'];
        }
        sort( $ids );
        return md5( implode( '-', $ids ) );
    }

    // =========================================================================
    // Rendering
    // =========================================================================

    /**
     * Renderiza a seção de recomendações no checkout.
     */
    public static function render_recommendations(): void {
        $product_ids = self::get_recommendations();

        // Container vazio para fragment replacement (mesmo sem produtos).
        if ( empty( $product_ids ) ) {
            echo '<div class="nraizes-checkout-upsell" id="nraizes-checkout-upsell"></div>';
            return;
        }

        $heading = get_option( 'nraizes_cu_heading', __( 'Clientes também compraram', 'nraizes-checkout-upsell' ) );

        echo '<div class="nraizes-checkout-upsell" id="nraizes-checkout-upsell">';
        echo '<h3 class="nraizes-checkout-upsell__heading">' . esc_html( $heading ) . '</h3>';
        echo '<div class="nraizes-checkout-upsell__grid">';

        foreach ( $product_ids as $product_id ) {
            $product = wc_get_product( $product_id );
            if ( ! $product ) {
                continue;
            }
            self::render_product_card( $product );
        }

        echo '</div>';
        echo '</div>';
    }

    /**
     * Renderiza um card de produto individual.
     *
     * @param WC_Product $product Produto.
     */
    private static function render_product_card( WC_Product $product ): void {
        $product_id = $product->get_id();
        ?>
        <div class="nraizes-checkout-upsell__item" data-product-id="<?php echo esc_attr( $product_id ); ?>">
            <div class="nraizes-checkout-upsell__img">
                <?php echo $product->get_image( 'woocommerce_gallery_thumbnail', array(
                    'loading'  => 'lazy',
                    'decoding' => 'async',
                ) ); ?>
            </div>
            <div class="nraizes-checkout-upsell__info">
                <span class="nraizes-checkout-upsell__name">
                    <?php echo esc_html( wp_trim_words( $product->get_name(), 6 ) ); ?>
                </span>
                <span class="nraizes-checkout-upsell__price">
                    <?php echo $product->get_price_html(); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped ?>
                </span>
            </div>
            <button type="button"
                    class="nraizes-checkout-upsell__btn js-nraizes-cu-add"
                    data-product-id="<?php echo esc_attr( $product_id ); ?>"
                    aria-label="<?php
                        printf(
                            /* translators: %s: nome do produto */
                            esc_attr__( 'Adicionar %s ao carrinho', 'nraizes-checkout-upsell' ),
                            $product->get_name()
                        );
                    ?>">
                <?php esc_html_e( 'Adicionar', 'nraizes-checkout-upsell' ); ?>
            </button>
        </div>
        <?php
    }

    // =========================================================================
    // Fragments & Assets
    // =========================================================================

    /**
     * Adiciona HTML como fragmento AJAX do WooCommerce.
     *
     * @param array $fragments Fragmentos existentes.
     * @return array
     */
    public static function add_fragment( array $fragments ): array {
        if ( 'yes' !== get_option( 'nraizes_cu_enabled', 'yes' ) ) {
            return $fragments;
        }

        ob_start();
        self::render_recommendations();
        $fragments['#nraizes-checkout-upsell'] = ob_get_clean();

        return $fragments;
    }

    /**
     * Enfileira CSS e JS no checkout.
     */
    public static function enqueue_assets(): void {
        if ( ! is_checkout() ) {
            return;
        }

        if ( 'yes' !== get_option( 'nraizes_cu_enabled', 'yes' ) ) {
            return;
        }

        wp_enqueue_style(
            'nraizes-checkout-upsell',
            NRAIZES_CU_URL . 'assets/css/checkout-upsell.css',
            array(),
            NRAIZES_CU_VERSION
        );

        wp_enqueue_script(
            'nraizes-checkout-upsell',
            NRAIZES_CU_URL . 'assets/js/checkout-upsell.js',
            array( 'jquery' ),
            NRAIZES_CU_VERSION,
            true
        );

        wp_localize_script( 'nraizes-checkout-upsell', 'nraizesCU', array(
            'ajax_url' => admin_url( 'admin-ajax.php' ),
            'nonce'    => wp_create_nonce( 'nraizes-cu-add-to-cart' ),
            'i18n'     => array(
                'adding' => __( 'Adicionando...', 'nraizes-checkout-upsell' ),
                'added'  => __( 'Adicionado!', 'nraizes-checkout-upsell' ),
                'error'  => __( 'Erro. Tente novamente.', 'nraizes-checkout-upsell' ),
            ),
        ) );
    }
}
