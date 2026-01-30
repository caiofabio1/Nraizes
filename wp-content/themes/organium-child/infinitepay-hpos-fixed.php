<?php
/**
 * Plugin Name: WooCommerce InfinitePay (HPOS + API oficial)
 * Description: Gateway InfinitePay via API oficial (/checkout/links + /payment_check), com webhook REST, fallback de verificação e compatibilidade HPOS.
 * Version: 3.0.1
 * Author: ChatGPT for Caio Portella
 * Requires at least: 6.0
 * Requires PHP: 7.4
 * WC requires at least: 6.0
 * WC tested up to: 9.0
 * License: GPLv2 or later
 * Text Domain: wc-infinitepay-hpos
 */

if (!defined('ABSPATH')) exit;

add_action('before_woocommerce_init', function () {
	if (class_exists('\Automattic\WooCommerce\Utilities\FeaturesUtil')) {
		\Automattic\WooCommerce\Utilities\FeaturesUtil::declare_compatibility('custom_order_tables', __FILE__, true);
	}
});

add_action('plugins_loaded', function () {

	if (!class_exists('WooCommerce') || !class_exists('WC_Payment_Gateway')) {
		return;
	}

	class WC_Gateway_InfinitePay_HP0S extends WC_Payment_Gateway {

		const API_LINKS        = 'https://api.infinitepay.io/invoices/public/checkout/links';
		const API_PAYMENTCHECK = 'https://api.infinitepay.io/invoices/public/checkout/payment_check';
		const API_TIMEOUT      = 20;

		// Declaração explícita das propriedades para PHP 8.2+
		public $handle;
		public $debug;
		public $send_customer;
		public $send_address;
		public $webhook_secret;

		public function __construct() {
			$this->id                 = 'infinitepay_hpos';
			$this->method_title       = __('InfinitePay (API + HPOS)', 'wc-infinitepay-hpos');
			$this->method_description = __('Gera link via API oficial da InfinitePay, usa webhook REST e é compatível com HPOS.', 'wc-infinitepay-hpos');
			$this->has_fields         = false;

			$this->supports = array('products', 'refunds');

			$this->init_form_fields();
			$this->init_settings();

			$this->title       = $this->get_option('title', __('Cartão/Pix (InfinitePay)', 'wc-infinitepay-hpos'));
			$this->description = $this->get_option('description', __('Pague com segurança via InfinitePay.', 'wc-infinitepay-hpos'));

			$this->enabled       = $this->get_option('enabled', 'no');
			$this->handle        = sanitize_text_field($this->get_option('handle', ''));
			$this->debug         = ($this->get_option('debug', 'no') === 'yes');
			$this->send_customer = ($this->get_option('send_customer', 'yes') === 'yes');
			$this->send_address  = ($this->get_option('send_address', 'yes') === 'yes');
			$this->webhook_secret = sanitize_text_field($this->get_option('webhook_secret', ''));

			add_action('woocommerce_update_options_payment_gateways_' . $this->id, array($this, 'process_admin_options'));
			add_action('woocommerce_thankyou_' . $this->id, array($this, 'thankyou_page'), 10, 1);
		}

		public function init_form_fields() {
			$webhook_url = rest_url('wc-infinitepay/v1/webhook');

			$this->form_fields = array(
				'enabled' => array(
					'title'   => __('Ativar/Desativar', 'wc-infinitepay-hpos'),
					'type'    => 'checkbox',
					'label'   => __('Ativar InfinitePay (API + HPOS)', 'wc-infinitepay-hpos'),
					'default' => 'no',
				),
				'title' => array(
					'title'   => __('Título', 'wc-infinitepay-hpos'),
					'type'    => 'text',
					'default' => __('Cartão/Pix (InfinitePay)', 'wc-infinitepay-hpos'),
				),
				'description' => array(
					'title'   => __('Descrição', 'wc-infinitepay-hpos'),
					'type'    => 'textarea',
					'default' => __('Pague com segurança via InfinitePay.', 'wc-infinitepay-hpos'),
				),
				'handle' => array(
					'title'       => __('Handle (InfiniteTag, sem $)', 'wc-infinitepay-hpos'),
					'type'        => 'text',
					'description' => __('Encontre no app InfinitePay > Configurações > Link integrado.', 'wc-infinitepay-hpos'),
					'default'     => '',
				),
				'send_customer' => array(
					'title'   => __('Enviar dados do cliente', 'wc-infinitepay-hpos'),
					'type'    => 'checkbox',
					'label'   => __('Enviar nome, email e telefone', 'wc-infinitepay-hpos'),
					'default' => 'yes',
				),
				'send_address' => array(
					'title'   => __('Enviar endereço', 'wc-infinitepay-hpos'),
					'type'    => 'checkbox',
					'label'   => __('Enviar CEP, número e complemento', 'wc-infinitepay-hpos'),
					'default' => 'yes',
				),
				'webhook_secret' => array(
					'title'   => __('Webhook secret (opcional)', 'wc-infinitepay-hpos'),
					'type'    => 'text',
					'default' => '',
				),
				'debug' => array(
					'title'   => __('Debug', 'wc-infinitepay-hpos'),
					'type'    => 'checkbox',
					'label'   => __('Registrar logs', 'wc-infinitepay-hpos'),
					'default' => 'no',
				),
				'_webhook_help' => array(
					'title'       => __('Webhook URL', 'wc-infinitepay-hpos'),
					'type'        => 'title',
					'description' => sprintf(__('Configure no painel InfinitePay:<br><code>%s</code>', 'wc-infinitepay-hpos'), esc_html($webhook_url)),
				),
			);
		}

		public function is_available() {
			if ($this->enabled !== 'yes') return false;
			if (empty($this->handle)) return false;
			return parent::is_available();
		}

		private function log($message, $level = 'info') {
			if (!$this->debug) return;
			wc_get_logger()->log($level, $message, array('source' => 'infinitepay-hpos'));
		}

		private function format_phone_e164_br($raw) {
			$digits = preg_replace('/\D+/', '', (string) $raw);
			if (!$digits) return '';
			if (strpos($digits, '55') === 0) return '+' . $digits;
			return '+55' . $digits;
		}

		private function build_payload(WC_Order $order) {
			$order_id = (string) $order->get_id();
			$total_cents = (int) round(((float) $order->get_total()) * 100);

			$payload = array(
				'handle'      => $this->handle,
				'order_nsu'   => $order_id,
				'redirect_url'=> $this->get_return_url($order),
				'webhook_url' => rest_url('wc-infinitepay/v1/webhook'),
				'items'       => array(array(
					'quantity'    => 1,
					'price'       => $total_cents,
					'description' => sprintf('Pedido #%s', $order_id),
				)),
			);

			if ($this->send_customer) {
				$name  = trim($order->get_billing_first_name() . ' ' . $order->get_billing_last_name());
				$email = $order->get_billing_email();
				$phone = $this->format_phone_e164_br($order->get_billing_phone());
				$customer = array();
				if ($name) $customer['name'] = $name;
				if ($email && is_email($email)) $customer['email'] = $email;
				if ($phone) $customer['phone_number'] = $phone;
				if (!empty($customer)) $payload['customer'] = $customer;
			}

			if ($this->send_address) {
				$cep = preg_replace('/\D+/', '', (string) $order->get_billing_postcode());
				$number = $order->get_meta('_billing_number');
				if (!$number) {
					$a1 = (string) $order->get_billing_address_1();
					if (preg_match('/\b(\d{1,6})\b/', $a1, $m)) $number = $m[1];
				}
				$complement = (string) $order->get_billing_address_2();
				$address = array();
				if (strlen($cep) === 8) $address['cep'] = $cep;
				if ($number) $address['number'] = (string) $number;
				if ($complement) $address['complement'] = $complement;
				if (!empty($address)) $payload['address'] = $address;
			}

			return $payload;
		}

		private function create_checkout_link(array $payload) {
			$res = wp_remote_post(self::API_LINKS, array(
				'timeout' => self::API_TIMEOUT,
				'headers' => array('Accept' => 'application/json', 'Content-Type' => 'application/json'),
				'body' => wp_json_encode($payload, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES),
			));

			if (is_wp_error($res)) return $res;
			$code = (int) wp_remote_retrieve_response_code($res);
			$body = wp_remote_retrieve_body($res);
			if ($code < 200 || $code >= 300) return new WP_Error('http', 'HTTP ' . $code);
			$data = json_decode($body, true);
			if (!is_array($data) || empty($data['url'])) return new WP_Error('bad_response', 'URL não retornada');
			return $data['url'];
		}

		public function process_payment($order_id) {
			$order = wc_get_order($order_id);
			if (!$order) {
				wc_add_notice(__('Pedido não encontrado.', 'wc-infinitepay-hpos'), 'error');
				return array('result' => 'failure');
			}

			try {
				$payload = $this->build_payload($order);
				$this->log('Payload: ' . wp_json_encode($payload));
				$url = $this->create_checkout_link($payload);
				if (is_wp_error($url)) throw new Exception($url->get_error_message());

				$order->update_status('on-hold', __('Aguardando InfinitePay.', 'wc-infinitepay-hpos'));
				$order->update_meta_data('_infinitepay_handle', $this->handle);
				$order->update_meta_data('_infinitepay_pending', 'yes');
				$order->save();
				if (WC()->cart) WC()->cart->empty_cart();
				return array('result' => 'success', 'redirect' => $url);
			} catch (Exception $e) {
				$this->log('Erro: ' . $e->getMessage(), 'error');
				$order->add_order_note('❌ ' . $e->getMessage());
				wc_add_notice($e->getMessage(), 'error');
				return array('result' => 'failure');
			}
		}

		public function process_refund($order_id, $amount = null, $reason = '') {
			$order = wc_get_order($order_id);
			if (!$order) return new WP_Error('invalid', 'Pedido inválido');
			$order->add_order_note(sprintf('Reembolso: %s. Processe no painel InfinitePay.', wc_price($amount)));
			return true;
		}

		public function thankyou_page($order_id) {
			$order = wc_get_order($order_id);
			if (!$order || $order->get_meta('_infinitepay_pending') !== 'yes') return;

			echo '<div class="woocommerce-info"><p>Confirmando pagamento...</p></div>';

			$tx = isset($_GET['transaction_nsu']) ? sanitize_text_field($_GET['transaction_nsu']) : '';
			$slug = isset($_GET['slug']) ? sanitize_text_field($_GET['slug']) : '';

			if ($tx && $slug) {
				$result = wc_infinitepay_payment_check($this->handle, (string) $order->get_id(), $tx, $slug);
				if ($result['ok'] && $result['paid']) {
					$order->payment_complete($tx);
					$order->delete_meta_data('_infinitepay_pending');
					$order->update_meta_data('_infinitepay_slug', $slug);
					$order->save();
					echo '<div class="woocommerce-message"><strong>✅ Pagamento confirmado!</strong></div>';
				}
			}
		}
	}

	add_filter('woocommerce_payment_gateways', function ($methods) {
		$methods[] = 'WC_Gateway_InfinitePay_HP0S';
		return $methods;
	});

	add_action('rest_api_init', function () {
		register_rest_route('wc-infinitepay/v1', '/webhook', array(
			'methods'  => 'POST',
			'callback' => 'wc_infinitepay_webhook_handler',
			'permission_callback' => '__return_true',
		));
	});
});

function wc_infinitepay_payment_check($handle, $order_nsu, $transaction_nsu, $slug) {
	$res = wp_remote_post(WC_Gateway_InfinitePay_HP0S::API_PAYMENTCHECK, array(
		'timeout' => 20,
		'headers' => array('Accept' => 'application/json', 'Content-Type' => 'application/json'),
		'body' => wp_json_encode(array(
			'handle' => $handle,
			'order_nsu' => $order_nsu,
			'transaction_nsu' => $transaction_nsu,
			'slug' => $slug,
		)),
	));
	if (is_wp_error($res)) return array('ok' => false, 'paid' => false);
	if (wp_remote_retrieve_response_code($res) !== 200) return array('ok' => false, 'paid' => false);
	$data = json_decode(wp_remote_retrieve_body($res), true);
	return array('ok' => true, 'paid' => !empty($data['success']) && !empty($data['paid']), 'data' => $data);
}

function wc_infinitepay_webhook_handler(WP_REST_Request $request) {
	$body = $request->get_json_params();
	if (!is_array($body)) return new WP_REST_Response(array('success' => false), 400);

	$order_nsu = isset($body['order_nsu']) ? (string) $body['order_nsu'] : '';
	$tx = isset($body['transaction_nsu']) ? sanitize_text_field($body['transaction_nsu']) : '';
	$slug = isset($body['invoice_slug']) ? sanitize_text_field($body['invoice_slug']) : '';
	$receipt = isset($body['receipt_url']) ? esc_url_raw($body['receipt_url']) : '';

	if (!$order_nsu || !$tx || !$slug) return new WP_REST_Response(array('success' => false), 400);

	$order = wc_get_order((int)$order_nsu);
	if (!$order) return new WP_REST_Response(array('success' => false), 400);

	if (in_array($order->get_status(), array('processing', 'completed'))) {
		return new WP_REST_Response(array('success' => true), 200);
	}

	// Security Check: Verify with InfinitePay API
	$settings = get_option('woocommerce_infinitepay_hpos_settings');
	$handle = isset($settings['handle']) ? $settings['handle'] : '';

	if (empty($handle)) {
		return new WP_REST_Response(array('success' => false, 'message' => 'Config error'), 500);
	}

	$check = wc_infinitepay_payment_check($handle, $order_nsu, $tx, $slug);
	if (!$check['ok'] || !$check['paid']) {
		return new WP_REST_Response(array('success' => false, 'message' => 'Verification failed'), 400);
	}

	$order->payment_complete($tx);
	$order->update_meta_data('_infinitepay_slug', $slug);
	$order->update_meta_data('_infinitepay_receipt_url', $receipt);
	$order->delete_meta_data('_infinitepay_pending');
	$order->add_order_note('✅ Webhook: ' . $tx);
	$order->save();

	return new WP_REST_Response(array('success' => true), 200);
}
