<?php
/**
 * Plugin Name: WooCommerce InfinitePay HPOS
 * Description: Gateway de pagamento InfinitePay otimizado com suporte a HPOS (High-Performance Order Storage).
 * Author: ChatGPT for Caio Portella
 * Version: 2.4.0
 * Requires at least: 6.0
 * Requires PHP: 7.4
 * WC requires at least: 6.0
 * WC tested up to: 9.0
 * License: GPLv2 or later
 * Text Domain: wc-infinitepay-link
 * Domain Path: /languages
 */

// Prevent direct access
if (!defined('ABSPATH')) {
    exit;
}

// Check if WooCommerce is active
if (!in_array('woocommerce/woocommerce.php', apply_filters('active_plugins', get_option('active_plugins')))) {
    return;
}

// Define plugin constants
define('WC_INFINITEPAY_LINK_VERSION', '2.4.0');
define('WC_INFINITEPAY_LINK_PLUGIN_URL', plugin_dir_url(__FILE__));
define('WC_INFINITEPAY_LINK_PLUGIN_PATH', plugin_dir_path(__FILE__));

/**
 * Declare HPOS (High-Performance Order Storage) compatibility
 */
add_action('before_woocommerce_init', function() {
    if (class_exists('\Automattic\WooCommerce\Utilities\FeaturesUtil')) {
        \Automattic\WooCommerce\Utilities\FeaturesUtil::declare_compatibility('custom_order_tables', __FILE__, true);
    }
});

// Initialize plugin
add_action('plugins_loaded', 'wc_infinitepay_link_init', 11);

function wc_infinitepay_link_init() {
    if (!class_exists('WC_Payment_Gateway')) {
        return;
    }

    load_plugin_textdomain('wc-infinitepay-link', false, dirname(plugin_basename(__FILE__)) . '/languages');

    class WC_Gateway_InfinitePay_Link extends WC_Payment_Gateway {

        const CHECKOUT_BASE_URL = 'https://checkout.infinitepay.io/';
        const API_BASE_URL = 'https://api.infinitepay.io/invoices/public/checkout/payment_check/';
        const API_TIMEOUT = 15;
        const MAX_URL_LENGTH = 800;

        private $logger;
        public $instructions;

        public function __construct() {
            $this->id                 = 'infinitepay_link';
            $this->icon               = '';
            $this->has_fields         = false;
            $this->method_title       = __('InfinitePay HPOS', 'wc-infinitepay-link');
            $this->method_description = __('Gateway com suporte a HPOS.', 'wc-infinitepay-link');
            $this->order_button_text  = __('Pagar com InfinitePay', 'wc-infinitepay-link');
            $this->supports           = array('products', 'refunds');

            if (class_exists('WC_Logger')) {
                $this->logger = new WC_Logger();
            }

            $this->init_form_fields();
            $this->init_settings();

            $this->title              = $this->get_option('title');
            $this->description        = $this->get_option('description');
            $this->enabled            = $this->get_option('enabled');
            $this->handle             = sanitize_text_field(trim($this->get_option('handle')));
            $this->return_page_type   = $this->get_option('return_page_type', 'wc_thank_you');
            $this->success_slug       = sanitize_text_field($this->get_option('success_slug', ''));
            $this->success_page       = absint($this->get_option('success_page', 0));
            $this->send_customer      = 'yes' === $this->get_option('send_customer', 'yes');
            $this->item_name_format   = $this->get_option('item_name_format', 'pedido_numero');
            $this->debug              = 'yes' === $this->get_option('debug', 'yes');
            $this->test_mode          = 'yes' === $this->get_option('test_mode', 'no');
            $this->neighborhood_field = sanitize_text_field($this->get_option('neighborhood_field', ''));
            $this->instructions       = $this->get_option('instructions', '');

            add_action('woocommerce_update_options_payment_gateways_' . $this->id, array($this, 'process_admin_options'));
            add_action('woocommerce_thankyou_' . $this->id, array($this, 'thankyou_page'));
            add_action('woocommerce_api_wc_gateway_infinitepay_link', array($this, 'check_infinitepay_response'));
        }

        private function get_pages_options() {
            $pages = get_pages(array('sort_order' => 'ASC', 'sort_column' => 'post_title', 'number' => 100));
            $options = array('' => __('-- Selecione --', 'wc-infinitepay-link'));
            foreach ($pages as $page) {
                $options[$page->ID] = $page->post_title;
            }
            return $options;
        }

        private function get_return_url_for_order($order) {
            switch ($this->return_page_type) {
                case 'custom_slug':
                    if (!empty($this->success_slug)) {
                        return home_url('/' . ltrim($this->success_slug, '/'));
                    }
                    return $this->get_return_url($order);
                case 'custom_page':
                    if ($this->success_page > 0) {
                        $page_url = get_permalink($this->success_page);
                        if ($page_url) {
                            return add_query_arg(array('order_id' => $order->get_id(), 'key' => $order->get_order_key()), $page_url);
                        }
                    }
                    return $this->get_return_url($order);
                default:
                    return $this->get_return_url($order);
            }
        }

        public function init_form_fields() {
            $this->form_fields = array(
                'enabled' => array('title' => __('Ativar', 'wc-infinitepay-link'), 'type' => 'checkbox', 'label' => __('Ativar InfinitePay HPOS', 'wc-infinitepay-link'), 'default' => 'yes'),
                'title' => array('title' => __('Título', 'wc-infinitepay-link'), 'type' => 'text', 'default' => __('Cartão (InfinitePay)', 'wc-infinitepay-link')),
                'description' => array('title' => __('Descrição', 'wc-infinitepay-link'), 'type' => 'textarea', 'default' => __('Pague com cartão via InfinitePay.', 'wc-infinitepay-link')),
                'handle' => array('title' => __('Handle InfinitePay', 'wc-infinitepay-link'), 'type' => 'text', 'default' => '', 'custom_attributes' => array('required' => 'required', 'placeholder' => 'nraizes')),
                'return_page_type' => array('title' => __('Página de retorno', 'wc-infinitepay-link'), 'type' => 'select', 'default' => 'wc_thank_you', 'options' => array('wc_thank_you' => __('WooCommerce (recomendado)', 'wc-infinitepay-link'), 'custom_slug' => __('Slug personalizado', 'wc-infinitepay-link'), 'custom_page' => __('Página específica', 'wc-infinitepay-link'))),
                'success_slug' => array('title' => __('Slug', 'wc-infinitepay-link'), 'type' => 'text', 'default' => ''),
                'success_page' => array('title' => __('Página', 'wc-infinitepay-link'), 'type' => 'select', 'default' => '', 'options' => $this->get_pages_options()),
                'test_mode' => array('title' => __('Modo teste', 'wc-infinitepay-link'), 'type' => 'checkbox', 'label' => __('Ativar', 'wc-infinitepay-link'), 'default' => 'no'),
                'item_name_format' => array('title' => __('Nome do item', 'wc-infinitepay-link'), 'type' => 'select', 'default' => 'pedido_numero', 'options' => array('pedido_numero' => 'Pedido #123', 'loja_pedido' => 'Compra Nraizes #123')),
                'send_customer' => array('title' => __('Enviar cliente', 'wc-infinitepay-link'), 'type' => 'checkbox', 'label' => __('Incluir dados', 'wc-infinitepay-link'), 'default' => 'yes'),
                'neighborhood_field' => array('title' => __('Campo Bairro', 'wc-infinitepay-link'), 'type' => 'text', 'default' => '', 'placeholder' => 'billing_neighborhood'),
                'debug' => array('title' => __('Debug', 'wc-infinitepay-link'), 'type' => 'checkbox', 'label' => __('Ativar logs', 'wc-infinitepay-link'), 'default' => 'yes'),
            );
        }

        public function is_available() {
            return 'yes' === $this->enabled && !empty($this->handle) && parent::is_available();
        }

        private function generate_item_name($order) {
            $order_id = $order->get_id();
            switch ($this->item_name_format) {
                case 'loja_pedido':
                    return sprintf('Compra %s #%s', get_bloginfo('name'), $order_id);
                default:
                    return sprintf('Pedido #%s', $order_id);
            }
        }

        private function sanitize_for_url($string, $max_length = 40) {
            $string = remove_accents($string);
            $string = preg_replace('/[^a-zA-Z0-9\s]/', '', $string);
            return substr(trim($string), 0, $max_length);
        }

        private function build_customer_data($order) {
            if (!$this->send_customer) return array();

            $data = array();
            
            $name = trim($order->get_billing_first_name() . ' ' . $order->get_billing_last_name());
            if ($name) $data['customer_name'] = $this->sanitize_for_url($name, 40);
            
            $email = $order->get_billing_email();
            if ($email && is_email($email)) $data['customer_email'] = sanitize_email($email);
            
            $phone = preg_replace('/\D+/', '', $order->get_billing_phone());
            if (strlen($phone) >= 10) $data['customer_cellphone'] = $phone;
            
            $address = $order->get_billing_address_1();
            if ($address) $data['address_street'] = $this->sanitize_for_url($address, 60);
            
            // HPOS: use order meta
            $number = $order->get_meta('_billing_number');
            if ($number) $data['address_number'] = substr(preg_replace('/\D+/', '', $number), 0, 10);
            
            $neighborhood = $order->get_meta('_billing_neighborhood');
            if (!$neighborhood) $neighborhood = $order->get_meta('_billing_bairro');
            if ($neighborhood) $data['address_district'] = $this->sanitize_for_url($neighborhood, 40);
            
            $city = $order->get_billing_city();
            if ($city) $data['address_city'] = $this->sanitize_for_url($city, 40);
            
            $state = $order->get_billing_state();
            if ($state) $data['address_state'] = strtoupper(substr($state, 0, 2));
            
            $cep = preg_replace('/\D+/', '', $order->get_billing_postcode());
            if (strlen($cep) === 8) $data['address_cep'] = $cep;

            return $data;
        }

        public function process_payment($order_id) {
            try {
                $order = wc_get_order($order_id);
                if (!$order) throw new Exception('Pedido não encontrado.');

                $total_cents = absint(round($order->get_total() * 100));
                if ($total_cents <= 0) throw new Exception('Valor inválido.');

                $item_name = $this->generate_item_name($order);
                $items = array(array('name' => $item_name, 'price' => $total_cents, 'quantity' => 1));
                $items_json = wp_json_encode($items, JSON_UNESCAPED_UNICODE);

                $params = array(
                    'items' => $items_json,
                    'order_nsu' => $order->get_id(),
                    'redirect_url' => $this->get_return_url_for_order($order),
                );

                $customer = $this->build_customer_data($order);
                $test_url = $this->build_url(array_merge($params, $customer));
                
                if (strlen($test_url) <= self::MAX_URL_LENGTH) {
                    $params = array_merge($params, $customer);
                }

                $payment_url = $this->build_url($params);

                // HPOS: use order meta methods
                $order->update_meta_data('_infinitepay_handle', $this->handle);
                $order->update_meta_data('_infinitepay_transaction_pending', true);
                $order->update_status('on-hold', 'Aguardando InfinitePay.');
                $order->save();

                if ($this->debug) {
                    $order->add_order_note('🔗 URL: ' . esc_url_raw($payment_url));
                }

                if (WC()->cart) WC()->cart->empty_cart();

                return array('result' => 'success', 'redirect' => $payment_url);

            } catch (Exception $e) {
                wc_add_notice($e->getMessage(), 'error');
                return array('result' => 'failure');
            }
        }

        private function build_url($params) {
            $base = self::CHECKOUT_BASE_URL . rawurlencode($this->handle);
            $query = array();
            foreach ($params as $key => $value) {
                $query[] = $key . '=' . rawurlencode((string)$value);
            }
            return $base . '?' . implode('&', $query);
        }

        public function process_refund($order_id, $amount = null, $reason = '') {
            $order = wc_get_order($order_id);
            if (!$order) return new WP_Error('invalid_order', 'Pedido inválido');
            $order->add_order_note(sprintf('Reembolso: %s. Processe no painel InfinitePay.', wc_price($amount)));
            return true;
        }

        public function check_infinitepay_response() {
            $transaction_id = sanitize_text_field($_REQUEST['transaction_id'] ?? '');
            $order_nsu = absint($_REQUEST['order_nsu'] ?? 0);
            
            if (!$transaction_id || !$order_nsu) wp_die('Dados inválidos', 'InfinitePay', array('response' => 400));

            $order = wc_get_order($order_nsu);
            if (!$order) wp_die('Pedido não encontrado', 'InfinitePay', array('response' => 404));

            $status = $this->verify_payment($transaction_id, $order_nsu, $order);
            
            if ($status['success']) {
                $order->payment_complete($transaction_id);
                $order->add_order_note('Pagamento confirmado: ' . $transaction_id);
                $order->delete_meta_data('_infinitepay_transaction_pending');
                $order->save();
            } else {
                $order->update_status('failed', 'Pagamento não confirmado.');
            }

            wp_redirect($this->get_return_url($order));
            exit;
        }

        private function verify_payment($transaction_id, $order_nsu, $order) {
            $handle = $order->get_meta('_infinitepay_handle') ?: $this->handle;
            
            $url = self::API_BASE_URL . rawurlencode($handle) . '?' . http_build_query(array(
                'transaction_nsu' => $transaction_id,
                'external_order_nsu' => $order_nsu,
            ));

            $response = wp_remote_get($url, array('timeout' => self::API_TIMEOUT));
            if (is_wp_error($response)) return array('success' => false);

            $data = json_decode(wp_remote_retrieve_body($response), true);
            return array('success' => !empty($data['success']) && !empty($data['paid']));
        }

        public function thankyou_page($order_id) {
            $order = wc_get_order($order_id);
            if (!$order) return;

            if ($order->get_meta('_infinitepay_transaction_pending')) {
                echo '<div class="woocommerce-info"><p>Verificando pagamento...</p></div>';
            }
        }

        public function admin_options() {
            echo '<h3>' . esc_html($this->method_title) . '</h3>';
            echo '<div style="background: #4CAF50; color: white; padding: 15px; margin: 15px 0; border-radius: 8px;">';
            echo '<strong>✅ HPOS Compatível</strong> - Suporte a High-Performance Order Storage</div>';
            echo '<table class="form-table">';
            $this->generate_settings_html();
            echo '</table>';
        }
    }

    add_filter('woocommerce_payment_gateways', function($methods) {
        $methods[] = 'WC_Gateway_InfinitePay_Link';
        return $methods;
    });
}

// AJAX check
add_action('wp_ajax_check_infinitepay_order_status', 'wc_infinitepay_check_order_status');
add_action('wp_ajax_nopriv_check_infinitepay_order_status', 'wc_infinitepay_check_order_status');

function wc_infinitepay_check_order_status() {
    if (!wp_verify_nonce($_POST['nonce'] ?? '', 'check_order_status')) wp_send_json_error('Nonce inválido');
    $order = wc_get_order(absint($_POST['order_id'] ?? 0));
    if (!$order) wp_send_json_error('Pedido não encontrado');
    wp_send_json_success(array('status' => $order->get_status(), 'is_paid' => in_array($order->get_status(), array('processing', 'completed'))));
}

// Shortcode
add_shortcode('infinitepay_check', function($atts) {
    $atts = shortcode_atts(array('handle' => ''), $atts);
    $handle = $atts['handle'] ?: (WC()->payment_gateways->get_available_payment_gateways()['infinitepay_link']->get_option('handle') ?? '');
    if (!$handle) return '<p>Handle não configurado.</p>';

    $tx = sanitize_text_field($_GET['transaction_id'] ?? '');
    $order_nsu = sanitize_text_field($_GET['order_nsu'] ?? '');
    if (!$tx || !$order_nsu) return '<div class="woocommerce-error">Parâmetros não encontrados.</div>';

    $url = 'https://api.infinitepay.io/invoices/public/checkout/payment_check/' . rawurlencode($handle) . '?' . http_build_query(array('transaction_nsu' => $tx, 'external_order_nsu' => $order_nsu));
    $data = json_decode(wp_remote_retrieve_body(wp_remote_get($url, array('timeout' => 15))), true);

    if (!empty($data['success']) && !empty($data['paid'])) {
        $order = wc_get_order($order_nsu);
        if ($order && $order->get_status() === 'on-hold') {
            $order->payment_complete($tx);
        }
        return '<div class="woocommerce-message">✅ Pagamento confirmado! Pedido #' . esc_html($order_nsu) . '</div>';
    }
    return '<div class="woocommerce-info">⏳ Aguardando confirmação...</div>';
});

add_filter('plugin_action_links_' . plugin_basename(__FILE__), function($links) {
    array_unshift($links, '<a href="' . admin_url('admin.php?page=wc-settings&tab=checkout&section=infinitepay_link') . '">Configurações</a>');
    return $links;
});
