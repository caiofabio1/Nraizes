<?php
/**
 * Método de envio: Frete Grátis Condicional.
 *
 * Estende WC_Shipping_Method para oferecer frete grátis quando
 * o subtotal do carrinho atinge um valor mínimo configurável.
 *
 * @package NRaizes\FreteGratis
 */

defined( 'ABSPATH' ) || exit;

class WC_Shipping_NRaizes_Free extends WC_Shipping_Method {

    /**
     * Valor mínimo para frete grátis.
     *
     * @var float
     */
    public $min_amount = 0;

    /**
     * Se cupons de frete grátis ativam o método.
     *
     * @var string yes|no
     */
    public $requires = '';

    /**
     * Construtor.
     *
     * @param int $instance_id ID da instância da zona de envio.
     */
    public function __construct( $instance_id = 0 ) {
        $this->id                 = 'nraizes_free_shipping';
        $this->instance_id        = absint( $instance_id );
        $this->method_title       = __( 'Frete Grátis NRaizes', 'nraizes-frete-gratis' );
        $this->method_description = __( 'Frete grátis condicional: ativa quando o subtotal do carrinho atinge o valor mínimo configurado.', 'nraizes-frete-gratis' );
        $this->supports           = array(
            'shipping-zones',
            'instance-settings',
            'instance-settings-modal',
        );

        $this->init();
    }

    /**
     * Inicializa configurações.
     */
    private function init() {
        $this->init_form_fields();
        $this->init_settings();

        $this->title      = $this->get_option( 'title', __( 'Frete Grátis', 'nraizes-frete-gratis' ) );
        $this->min_amount = (float) $this->get_option( 'min_amount', 500 );
        $this->requires   = $this->get_option( 'requires', 'min_amount' );

        add_action(
            'woocommerce_update_options_shipping_' . $this->id,
            array( $this, 'process_admin_options' )
        );
    }

    /**
     * Campos de configuração (exibidos no modal da zona de envio).
     */
    public function init_form_fields() {
        $this->instance_form_fields = array(
            'title'      => array(
                'title'   => __( 'Título', 'nraizes-frete-gratis' ),
                'type'    => 'text',
                'default' => __( 'Frete Grátis', 'nraizes-frete-gratis' ),
                'desc_tip' => true,
                'description' => __( 'Nome exibido para o cliente no carrinho e checkout.', 'nraizes-frete-gratis' ),
            ),
            'requires'   => array(
                'title'   => __( 'Condição para frete grátis', 'nraizes-frete-gratis' ),
                'type'    => 'select',
                'class'   => 'wc-enhanced-select',
                'default' => 'min_amount',
                'options' => array(
                    'min_amount'            => __( 'Valor mínimo do pedido', 'nraizes-frete-gratis' ),
                    'coupon'                => __( 'Cupom de frete grátis', 'nraizes-frete-gratis' ),
                    'min_amount_or_coupon'  => __( 'Valor mínimo OU cupom', 'nraizes-frete-gratis' ),
                    'min_amount_and_coupon' => __( 'Valor mínimo E cupom', 'nraizes-frete-gratis' ),
                ),
            ),
            'min_amount' => array(
                'title'       => __( 'Valor mínimo (R$)', 'nraizes-frete-gratis' ),
                'type'        => 'price',
                'default'     => 500,
                'placeholder' => wc_format_localized_price( 500 ),
                'description' => __( 'Subtotal mínimo do carrinho para liberar frete grátis. Desconsiderando descontos de cupom.', 'nraizes-frete-gratis' ),
                'desc_tip'    => true,
            ),
            'ignore_discounts' => array(
                'title'   => __( 'Cupons de desconto', 'nraizes-frete-gratis' ),
                'type'    => 'checkbox',
                'label'   => __( 'Usar subtotal antes de descontos de cupom', 'nraizes-frete-gratis' ),
                'default' => 'no',
            ),
            'show_progress_bar' => array(
                'title'   => __( 'Barra de progresso', 'nraizes-frete-gratis' ),
                'type'    => 'checkbox',
                'label'   => __( 'Exibir barra de progresso no carrinho e checkout', 'nraizes-frete-gratis' ),
                'default' => 'yes',
            ),
        );
    }

    /**
     * Verifica se o cliente tem cupom de frete grátis aplicado.
     *
     * @return bool
     */
    private function has_free_shipping_coupon() {
        $coupons = WC()->cart->get_coupons();
        foreach ( $coupons as $coupon ) {
            if ( $coupon->get_free_shipping() ) {
                return true;
            }
        }
        return false;
    }

    /**
     * Calcula o subtotal relevante do carrinho.
     *
     * @return float
     */
    private function get_cart_subtotal() {
        $ignore_discounts = 'yes' === $this->get_option( 'ignore_discounts', 'no' );

        if ( $ignore_discounts ) {
            $total = WC()->cart->get_subtotal();
        } else {
            $total = WC()->cart->get_displayed_subtotal();

            if ( WC()->cart->display_prices_including_tax() ) {
                $total -= WC()->cart->get_discount_tax();
            }

            $total -= WC()->cart->get_discount_total();
        }

        return (float) $total;
    }

    /**
     * Verifica se o método está disponível.
     *
     * @param array $package Pacote de envio.
     * @return bool
     */
    public function is_available( $package ) {
        $is_available  = false;
        $has_coupon    = $this->has_free_shipping_coupon();
        $has_min       = $this->get_cart_subtotal() >= $this->min_amount;

        switch ( $this->requires ) {
            case 'min_amount':
                $is_available = $has_min;
                break;
            case 'coupon':
                $is_available = $has_coupon;
                break;
            case 'min_amount_or_coupon':
                $is_available = $has_min || $has_coupon;
                break;
            case 'min_amount_and_coupon':
                $is_available = $has_min && $has_coupon;
                break;
        }

        return apply_filters(
            'nraizes_free_shipping_is_available',
            $is_available,
            $package,
            $this
        );
    }

    /**
     * Calcula o envio (custo zero).
     *
     * @param array $package Pacote de envio.
     */
    public function calculate_shipping( $package = array() ) {
        $this->add_rate(
            array(
                'id'      => $this->get_rate_id(),
                'label'   => $this->title,
                'cost'    => 0,
                'package' => $package,
            )
        );
    }
}
