<?php
/**
 * Gateway de pagamento InfinitePay.
 *
 * Melhorias v4 sobre a versão anterior:
 * - Timeout reduzido (10s) com retry inteligente
 * - Thankyou page verifica meta antes de chamar API
 * - Cache transient evita chamadas redundantes
 * - Typo HPOS corrigido (era HP0S com zero)
 * - Classe separada, fora do tema
 * - Propriedades PHP 8.2+ compatíveis
 *
 * @package NRaizes\InfinitePay
 */

defined( 'ABSPATH' ) || exit;

class WC_Gateway_InfinitePay_HPOS extends WC_Payment_Gateway {

    /**
     * Endpoints da API InfinitePay.
     */
    const API_LINKS        = 'https://api.infinitepay.io/invoices/public/checkout/links';
    const API_PAYMENTCHECK = 'https://api.infinitepay.io/invoices/public/checkout/payment_check';

    /**
     * Timeout da API em segundos (reduzido de 20 para 10).
     */
    const API_TIMEOUT = 10;

    /**
     * Máximo de tentativas na API.
     */
    const API_MAX_RETRIES = 2;

    /**
     * Propriedades declaradas para PHP 8.2+.
     */
    public string $handle         = '';
    public bool   $debug          = false;
    public bool   $send_customer  = true;
    public bool   $send_address   = true;
    public string $webhook_secret = '';

    /**
     * Construtor.
     */
    public function __construct() {
        $this->id                 = 'infinitepay_hpos';
        $this->method_title       = __( 'InfinitePay (HPOS)', 'wc-infinitepay-hpos' );
        $this->method_description = __( 'Gateway InfinitePay via API oficial com checkout link, webhook seguro e compatibilidade HPOS.', 'wc-infinitepay-hpos' );
        $this->has_fields         = false;
        $this->supports           = array( 'products', 'refunds' );

        $this->init_form_fields();
        $this->init_settings();

        $this->title          = $this->get_option( 'title', __( 'Cartão/Pix (InfinitePay)', 'wc-infinitepay-hpos' ) );
        $this->description    = $this->get_option( 'description', __( 'Pague com segurança via InfinitePay.', 'wc-infinitepay-hpos' ) );
        $this->enabled        = $this->get_option( 'enabled', 'no' );
        $this->handle         = sanitize_text_field( $this->get_option( 'handle', '' ) );
        $this->debug          = 'yes' === $this->get_option( 'debug', 'no' );
        $this->send_customer  = 'yes' === $this->get_option( 'send_customer', 'yes' );
        $this->send_address   = 'yes' === $this->get_option( 'send_address', 'yes' );
        $this->webhook_secret = sanitize_text_field( $this->get_option( 'webhook_secret', '' ) );

        add_action( 'woocommerce_update_options_payment_gateways_' . $this->id, array( $this, 'process_admin_options' ) );
        add_action( 'woocommerce_thankyou_' . $this->id, array( $this, 'thankyou_page' ), 10, 1 );
    }

    /**
     * Campos de configuração no admin.
     */
    public function init_form_fields() {
        $webhook_url = rest_url( 'wc-infinitepay/v1/webhook' );

        $this->form_fields = array(
            'enabled'         => array(
                'title'   => __( 'Ativar/Desativar', 'wc-infinitepay-hpos' ),
                'type'    => 'checkbox',
                'label'   => __( 'Ativar InfinitePay', 'wc-infinitepay-hpos' ),
                'default' => 'no',
            ),
            'title'           => array(
                'title'   => __( 'Título', 'wc-infinitepay-hpos' ),
                'type'    => 'text',
                'default' => __( 'Cartão/Pix (InfinitePay)', 'wc-infinitepay-hpos' ),
                'desc_tip' => true,
                'description' => __( 'Nome exibido para o cliente no checkout.', 'wc-infinitepay-hpos' ),
            ),
            'description'     => array(
                'title'   => __( 'Descrição', 'wc-infinitepay-hpos' ),
                'type'    => 'textarea',
                'default' => __( 'Pague com segurança via InfinitePay.', 'wc-infinitepay-hpos' ),
            ),
            'handle'          => array(
                'title'       => __( 'Handle (InfiniteTag, sem $)', 'wc-infinitepay-hpos' ),
                'type'        => 'text',
                'description' => __( 'Encontre no app InfinitePay > Configurações > Link integrado.', 'wc-infinitepay-hpos' ),
                'default'     => '',
            ),
            'send_customer'   => array(
                'title'   => __( 'Enviar dados do cliente', 'wc-infinitepay-hpos' ),
                'type'    => 'checkbox',
                'label'   => __( 'Enviar nome, email e telefone', 'wc-infinitepay-hpos' ),
                'default' => 'yes',
            ),
            'send_address'    => array(
                'title'   => __( 'Enviar endereço', 'wc-infinitepay-hpos' ),
                'type'    => 'checkbox',
                'label'   => __( 'Enviar CEP, número e complemento', 'wc-infinitepay-hpos' ),
                'default' => 'yes',
            ),
            'webhook_secret'  => array(
                'title'       => __( 'Webhook Secret', 'wc-infinitepay-hpos' ),
                'type'        => 'password',
                'description' => __( 'Chave secreta para validar webhooks. Configure a mesma no painel InfinitePay.', 'wc-infinitepay-hpos' ),
                'default'     => '',
                'desc_tip'    => true,
            ),
            'debug'           => array(
                'title'   => __( 'Debug', 'wc-infinitepay-hpos' ),
                'type'    => 'checkbox',
                'label'   => __( 'Registrar logs em WooCommerce > Status > Logs', 'wc-infinitepay-hpos' ),
                'default' => 'no',
            ),
            '_webhook_help'   => array(
                'title'       => __( 'Webhook URL', 'wc-infinitepay-hpos' ),
                'type'        => 'title',
                'description' => sprintf(
                    /* translators: %s: webhook URL */
                    __( 'Configure no painel InfinitePay:<br><code>%s</code>', 'wc-infinitepay-hpos' ),
                    esc_html( $webhook_url )
                ),
            ),
        );
    }

    /**
     * Verifica se o gateway está disponível.
     *
     * @return bool
     */
    public function is_available() {
        if ( 'yes' !== $this->enabled || empty( $this->handle ) ) {
            return false;
        }
        return parent::is_available();
    }

    /**
     * Logger condicional.
     *
     * @param string $message Mensagem.
     * @param string $level   Nível (info, error, warning).
     */
    public function log( string $message, string $level = 'info' ): void {
        if ( ! $this->debug ) {
            return;
        }
        wc_get_logger()->log( $level, $message, array( 'source' => 'infinitepay-hpos' ) );
    }

    /**
     * Formata telefone para E.164 brasileiro.
     *
     * @param string $raw Telefone bruto.
     * @return string
     */
    private function format_phone_e164_br( string $raw ): string {
        $digits = preg_replace( '/\D+/', '', $raw );
        if ( ! $digits ) {
            return '';
        }
        if ( str_starts_with( $digits, '55' ) ) {
            return '+' . $digits;
        }
        return '+55' . $digits;
    }

    /**
     * Monta o payload para a API de checkout links.
     *
     * @param WC_Order $order Pedido.
     * @return array
     */
    private function build_payload( WC_Order $order ): array {
        $order_id    = (string) $order->get_id();
        $total_cents = (int) round( ( (float) $order->get_total() ) * 100 );

        $payload = array(
            'handle'       => $this->handle,
            'order_nsu'    => $order_id,
            'redirect_url' => $this->get_return_url( $order ),
            'webhook_url'  => rest_url( 'wc-infinitepay/v1/webhook' ),
            'items'        => array(
                array(
                    'quantity'    => 1,
                    'price'       => $total_cents,
                    'description' => sprintf( 'Pedido #%s', $order_id ),
                ),
            ),
        );

        // Dados do cliente.
        if ( $this->send_customer ) {
            $name  = trim( $order->get_billing_first_name() . ' ' . $order->get_billing_last_name() );
            $email = $order->get_billing_email();
            $phone = $this->format_phone_e164_br( (string) $order->get_billing_phone() );

            $customer = array();
            if ( $name ) {
                $customer['name'] = $name;
            }
            if ( $email && is_email( $email ) ) {
                $customer['email'] = $email;
            }
            if ( $phone ) {
                $customer['phone_number'] = $phone;
            }
            if ( ! empty( $customer ) ) {
                $payload['customer'] = $customer;
            }
        }

        // Endereço.
        if ( $this->send_address ) {
            $cep    = preg_replace( '/\D+/', '', (string) $order->get_billing_postcode() );
            $number = $order->get_meta( '_billing_number' );

            if ( ! $number ) {
                $a1 = (string) $order->get_billing_address_1();
                if ( preg_match( '/\b(\d{1,6})\b/', $a1, $m ) ) {
                    $number = $m[1];
                }
            }

            $complement = (string) $order->get_billing_address_2();
            $address    = array();

            if ( 8 === strlen( $cep ) ) {
                $address['cep'] = $cep;
            }
            if ( $number ) {
                $address['number'] = (string) $number;
            }
            if ( $complement ) {
                $address['complement'] = $complement;
            }
            if ( ! empty( $address ) ) {
                $payload['address'] = $address;
            }
        }

        return $payload;
    }

    /**
     * Cria checkout link na API com retry inteligente.
     *
     * Tenta até API_MAX_RETRIES vezes com backoff progressivo.
     * Timeout reduzido para não travar o checkout do cliente.
     *
     * @param array $payload Dados para a API.
     * @return string|WP_Error URL do checkout ou erro.
     */
    private function create_checkout_link( array $payload ) {
        $last_error = null;

        for ( $attempt = 1; $attempt <= self::API_MAX_RETRIES; $attempt++ ) {
            // Backoff: 0s na primeira, 1s na segunda.
            if ( $attempt > 1 ) {
                sleep( $attempt - 1 );
                $this->log( sprintf( 'Retry %d/%d para criar checkout link.', $attempt, self::API_MAX_RETRIES ) );
            }

            $response = wp_remote_post( self::API_LINKS, array(
                'timeout' => self::API_TIMEOUT,
                'headers' => array(
                    'Accept'       => 'application/json',
                    'Content-Type' => 'application/json',
                ),
                'body'    => wp_json_encode( $payload, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES ),
            ) );

            if ( is_wp_error( $response ) ) {
                $last_error = $response;
                $this->log( 'Erro HTTP: ' . $response->get_error_message(), 'error' );
                continue;
            }

            $code = (int) wp_remote_retrieve_response_code( $response );
            $body = wp_remote_retrieve_body( $response );

            if ( $code >= 500 ) {
                // Erro do servidor — vale retry.
                $last_error = new WP_Error( 'server_error', 'HTTP ' . $code );
                $this->log( 'Servidor retornou ' . $code . ', tentando novamente...', 'warning' );
                continue;
            }

            if ( $code < 200 || $code >= 300 ) {
                // Erro do cliente (4xx) — não adianta retry.
                $this->log( 'API retornou HTTP ' . $code . ': ' . $body, 'error' );
                return new WP_Error( 'api_error', 'HTTP ' . $code );
            }

            $data = json_decode( $body, true );
            if ( ! is_array( $data ) || empty( $data['url'] ) ) {
                $this->log( 'Resposta inesperada: ' . $body, 'error' );
                return new WP_Error( 'bad_response', __( 'URL de checkout não retornada pela API.', 'wc-infinitepay-hpos' ) );
            }

            $this->log( 'Checkout link criado com sucesso na tentativa ' . $attempt );
            return $data['url'];
        }

        return $last_error ?? new WP_Error( 'unknown', __( 'Falha ao criar link de pagamento.', 'wc-infinitepay-hpos' ) );
    }

    /**
     * Processa o pagamento — chamado pelo WooCommerce no checkout.
     *
     * @param int $order_id ID do pedido.
     * @return array{result: string, redirect?: string}
     */
    public function process_payment( $order_id ) {
        $order = wc_get_order( $order_id );
        if ( ! $order ) {
            wc_add_notice( __( 'Pedido não encontrado.', 'wc-infinitepay-hpos' ), 'error' );
            return array( 'result' => 'failure' );
        }

        try {
            $payload = $this->build_payload( $order );
            $this->log( 'Payload pedido #' . $order_id . ': ' . wp_json_encode( $payload ) );

            $url = $this->create_checkout_link( $payload );
            if ( is_wp_error( $url ) ) {
                throw new \Exception( $url->get_error_message() );
            }

            $order->update_status( 'on-hold', __( 'Aguardando pagamento InfinitePay.', 'wc-infinitepay-hpos' ) );
            $order->update_meta_data( '_infinitepay_handle', $this->handle );
            $order->update_meta_data( '_infinitepay_pending', 'yes' );
            $order->update_meta_data( '_infinitepay_checkout_url', esc_url_raw( $url ) );
            $order->save();

            if ( WC()->cart ) {
                WC()->cart->empty_cart();
            }

            return array(
                'result'   => 'success',
                'redirect' => $url,
            );
        } catch ( \Exception $e ) {
            $this->log( 'Erro no pedido #' . $order_id . ': ' . $e->getMessage(), 'error' );
            $order->add_order_note( '❌ Erro InfinitePay: ' . $e->getMessage() );
            wc_add_notice(
                __( 'Erro ao processar pagamento. Tente novamente.', 'wc-infinitepay-hpos' ),
                'error'
            );
            return array( 'result' => 'failure' );
        }
    }

    /**
     * Reembolso (manual — InfinitePay não tem API de refund).
     *
     * @param int        $order_id ID do pedido.
     * @param float|null $amount   Valor.
     * @param string     $reason   Motivo.
     * @return bool|WP_Error
     */
    public function process_refund( $order_id, $amount = null, $reason = '' ) {
        $order = wc_get_order( $order_id );
        if ( ! $order ) {
            return new WP_Error( 'invalid', __( 'Pedido inválido.', 'wc-infinitepay-hpos' ) );
        }
        $order->add_order_note(
            sprintf(
                /* translators: %s: valor do reembolso */
                __( 'Reembolso de %s solicitado. Processe manualmente no painel InfinitePay.', 'wc-infinitepay-hpos' ),
                wc_price( $amount )
            )
        );
        return true;
    }

    /**
     * Página de obrigado — verifica pagamento de forma inteligente.
     *
     * Fluxo otimizado:
     * 1. Se webhook já confirmou → exibe sucesso imediatamente (sem API call)
     * 2. Se tem parâmetros de verificação → chama API com cache transient
     * 3. Senão → exibe mensagem de aguardando
     *
     * @param int $order_id ID do pedido.
     */
    public function thankyou_page( $order_id ): void {
        $order = wc_get_order( $order_id );
        if ( ! $order ) {
            return;
        }

        // 1. Já confirmado pelo webhook? Não precisa chamar API.
        if ( 'yes' !== $order->get_meta( '_infinitepay_pending' ) ) {
            echo '<div class="woocommerce-message"><strong>';
            echo esc_html__( '✅ Pagamento confirmado!', 'wc-infinitepay-hpos' );
            echo '</strong></div>';
            return;
        }

        // 2. Tenta verificar via API se temos os parâmetros.
        $tx   = isset( $_GET['transaction_nsu'] ) ? sanitize_text_field( wp_unslash( $_GET['transaction_nsu'] ) ) : '';
        $slug = isset( $_GET['slug'] ) ? sanitize_text_field( wp_unslash( $_GET['slug'] ) ) : '';

        if ( $tx && $slug ) {
            $result = $this->verify_payment_cached( $order, $tx, $slug );

            if ( $result['paid'] ) {
                echo '<div class="woocommerce-message"><strong>';
                echo esc_html__( '✅ Pagamento confirmado!', 'wc-infinitepay-hpos' );
                echo '</strong></div>';
                return;
            }
        }

        // 3. Ainda pendente — aguardando webhook.
        echo '<div class="woocommerce-info"><p>';
        echo esc_html__( 'Confirmando pagamento... Você receberá um email quando confirmado.', 'wc-infinitepay-hpos' );
        echo '</p></div>';
    }

    /**
     * Verifica pagamento com cache transient (evita chamadas duplicadas).
     *
     * Se o cliente recarregar a thankyou page, o transient retorna
     * o resultado anterior sem chamar a API novamente.
     *
     * @param WC_Order $order Pedido.
     * @param string   $tx    Transaction NSU.
     * @param string   $slug  Invoice slug.
     * @return array{ok: bool, paid: bool}
     */
    private function verify_payment_cached( WC_Order $order, string $tx, string $slug ): array {
        $cache_key = 'ip_check_' . $order->get_id() . '_' . md5( $tx . $slug );
        $cached    = get_transient( $cache_key );

        if ( false !== $cached ) {
            $this->log( 'Verificação do pedido #' . $order->get_id() . ' servida do cache.' );
            return $cached;
        }

        $result = $this->payment_check( (string) $order->get_id(), $tx, $slug );

        // Cache por 5 minutos (sucesso ou falha).
        set_transient( $cache_key, $result, 5 * MINUTE_IN_SECONDS );

        if ( $result['paid'] ) {
            $order->payment_complete( $tx );
            $order->delete_meta_data( '_infinitepay_pending' );
            $order->update_meta_data( '_infinitepay_slug', $slug );
            $order->save();
            $this->log( 'Pagamento confirmado via thankyou para pedido #' . $order->get_id() );
        }

        return $result;
    }

    /**
     * Chama a API de payment check.
     *
     * @param string $order_nsu       NSU do pedido.
     * @param string $transaction_nsu NSU da transação.
     * @param string $slug            Slug do invoice.
     * @return array{ok: bool, paid: bool, data?: array}
     */
    public function payment_check( string $order_nsu, string $transaction_nsu, string $slug ): array {
        $response = wp_remote_post( self::API_PAYMENTCHECK, array(
            'timeout' => self::API_TIMEOUT,
            'headers' => array(
                'Accept'       => 'application/json',
                'Content-Type' => 'application/json',
            ),
            'body'    => wp_json_encode( array(
                'handle'          => $this->handle,
                'order_nsu'       => $order_nsu,
                'transaction_nsu' => $transaction_nsu,
                'slug'            => $slug,
            ) ),
        ) );

        if ( is_wp_error( $response ) ) {
            $this->log( 'Payment check erro: ' . $response->get_error_message(), 'error' );
            return array( 'ok' => false, 'paid' => false );
        }

        $code = (int) wp_remote_retrieve_response_code( $response );
        if ( 200 !== $code ) {
            $this->log( 'Payment check HTTP ' . $code, 'warning' );
            return array( 'ok' => false, 'paid' => false );
        }

        $data = json_decode( wp_remote_retrieve_body( $response ), true );
        $paid = ! empty( $data['success'] ) && ! empty( $data['paid'] );

        return array(
            'ok'   => true,
            'paid' => $paid,
            'data' => $data,
        );
    }
}
