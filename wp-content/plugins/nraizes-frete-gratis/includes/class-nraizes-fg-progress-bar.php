<?php
/**
 * Barra de progresso para frete grátis.
 *
 * Exibe uma barra visual informando quanto falta para o cliente
 * atingir o valor mínimo de frete grátis. Atualiza via AJAX
 * quando o carrinho é modificado.
 *
 * @package NRaizes\FreteGratis
 */

defined( 'ABSPATH' ) || exit;

class NRaizes_FG_Progress_Bar {

    /**
     * Registra hooks.
     */
    public static function init() {
        add_action( 'woocommerce_before_cart', array( __CLASS__, 'render' ) );
        add_action( 'woocommerce_before_checkout_form', array( __CLASS__, 'render' ) );
        add_action( 'woocommerce_before_mini_cart_contents', array( __CLASS__, 'render' ) );
        add_action( 'wp_enqueue_scripts', array( __CLASS__, 'enqueue_assets' ) );

        // Fragmento AJAX para atualizar a barra quando o carrinho muda.
        add_filter( 'woocommerce_update_order_review_fragments', array( __CLASS__, 'add_fragment' ) );
        add_filter( 'woocommerce_add_to_cart_fragments', array( __CLASS__, 'add_fragment' ) );
    }

    /**
     * Obtém as configurações da primeira instância ativa do método de envio.
     *
     * @return array{min_amount: float, show_bar: bool}
     */
    private static function get_settings() {
        $min_amount = 500;
        $show_bar   = true;

        // Busca a configuração da zona de envio que contém nosso método.
        $zones = WC_Shipping_Zones::get_zones();
        $zones['0'] = array( 'zone_id' => 0 ); // Inclui "Locais não cobertos".

        foreach ( $zones as $zone_data ) {
            $zone    = WC_Shipping_Zones::get_zone( $zone_data['zone_id'] );
            $methods = $zone->get_shipping_methods( true ); // Apenas ativos.

            foreach ( $methods as $method ) {
                if ( 'nraizes_free_shipping' === $method->id ) {
                    $min_amount = (float) $method->get_option( 'min_amount', 500 );
                    $show_bar   = 'yes' === $method->get_option( 'show_progress_bar', 'yes' );
                    break 2;
                }
            }
        }

        return array(
            'min_amount' => $min_amount,
            'show_bar'   => $show_bar,
        );
    }

    /**
     * Obtém o subtotal atual do carrinho.
     *
     * @return float
     */
    private static function get_cart_total() {
        if ( ! WC()->cart ) {
            return 0;
        }
        return (float) WC()->cart->get_displayed_subtotal();
    }

    /**
     * Renderiza a barra de progresso.
     */
    public static function render() {
        $settings = self::get_settings();

        if ( ! $settings['show_bar'] ) {
            return;
        }

        $min_amount = $settings['min_amount'];
        $current    = self::get_cart_total();
        $remaining  = max( 0, $min_amount - $current );
        $percent    = $min_amount > 0 ? min( ( $current / $min_amount ) * 100, 100 ) : 0;

        echo '<div class="nraizes-fg-bar-wrapper" id="nraizes-fg-bar-wrapper">';
        self::render_bar_html( $remaining, $percent );
        echo '</div>';
    }

    /**
     * HTML interno da barra (reutilizado pelo fragmento AJAX).
     *
     * @param float $remaining Valor restante.
     * @param float $percent   Percentual preenchido.
     */
    private static function render_bar_html( $remaining, $percent ) {
        if ( $remaining > 0 ) {
            ?>
            <div class="nraizes-fg-bar nraizes-fg-bar--progress"
                 role="region"
                 aria-label="<?php esc_attr_e( 'Progresso para frete grátis', 'nraizes-frete-gratis' ); ?>"
                 aria-live="polite">
                <p class="nraizes-fg-bar__text" id="nraizes-fg-bar-text">
                    <span class="nraizes-fg-bar__icon" aria-hidden="true">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <rect x="1" y="3" width="15" height="13"/><polygon points="16 8 20 8 23 11 23 16 16 16 16 8"/><circle cx="5.5" cy="18.5" r="2.5"/><circle cx="18.5" cy="18.5" r="2.5"/>
                        </svg>
                    </span>
                    <?php
                    printf(
                        /* translators: %s: valor restante formatado. */
                        esc_html__( 'Faltam %s para FRETE GRÁTIS!', 'nraizes-frete-gratis' ),
                        '<strong>R$&nbsp;' . esc_html( number_format( $remaining, 2, ',', '.' ) ) . '</strong>'
                    );
                    ?>
                </p>
                <div class="nraizes-fg-bar__track"
                     role="progressbar"
                     aria-valuenow="<?php echo esc_attr( round( $percent ) ); ?>"
                     aria-valuemin="0"
                     aria-valuemax="100"
                     aria-labelledby="nraizes-fg-bar-text">
                    <div class="nraizes-fg-bar__fill" style="width:<?php echo esc_attr( $percent ); ?>%;"></div>
                </div>
            </div>
            <?php
        } else {
            ?>
            <div class="nraizes-fg-bar nraizes-fg-bar--complete"
                 role="status"
                 aria-live="polite">
                <p class="nraizes-fg-bar__text">
                    <span class="nraizes-fg-bar__icon" aria-hidden="true">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>
                        </svg>
                    </span>
                    <?php
                    printf(
                        '<strong>%s</strong> %s',
                        esc_html__( 'Parabéns!', 'nraizes-frete-gratis' ),
                        esc_html__( 'Você ganhou FRETE GRÁTIS!', 'nraizes-frete-gratis' )
                    );
                    ?>
                </p>
            </div>
            <?php
        }
    }

    /**
     * Adiciona o HTML da barra como fragmento AJAX do WooCommerce.
     *
     * Permite que a barra atualize automaticamente quando o carrinho
     * é modificado sem recarregar a página.
     *
     * @param array $fragments Fragmentos HTML.
     * @return array
     */
    public static function add_fragment( $fragments ) {
        $settings = self::get_settings();

        if ( ! $settings['show_bar'] ) {
            return $fragments;
        }

        $min_amount = $settings['min_amount'];
        $current    = self::get_cart_total();
        $remaining  = max( 0, $min_amount - $current );
        $percent    = $min_amount > 0 ? min( ( $current / $min_amount ) * 100, 100 ) : 0;

        ob_start();
        echo '<div class="nraizes-fg-bar-wrapper" id="nraizes-fg-bar-wrapper">';
        self::render_bar_html( $remaining, $percent );
        echo '</div>';

        $fragments['#nraizes-fg-bar-wrapper'] = ob_get_clean();

        return $fragments;
    }

    /**
     * Enfileira CSS e JS no frontend.
     */
    public static function enqueue_assets() {
        if ( ! is_cart() && ! is_checkout() ) {
            return;
        }

        wp_enqueue_style(
            'nraizes-fg-bar',
            NRAIZES_FG_URL . 'assets/css/progress-bar.css',
            array(),
            NRAIZES_FG_VERSION
        );
    }
}
