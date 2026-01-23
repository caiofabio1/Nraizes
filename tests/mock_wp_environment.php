<?php
// Mock WordPress and WooCommerce environment

if (!defined('ABSPATH')) {
    define('ABSPATH', '/tmp/');
}

// WP Core Classes
class WP_Error {
    public function __construct($code = '', $message = '', $data = '') {}
    public function get_error_message() { return 'error'; }
}

class WP_REST_Response {
    public $data;
    public $status;
    public function __construct($data = null, $status = 200) {
        $this->data = $data;
        $this->status = $status;
    }
}

class WP_REST_Request {
    private $params;
    public function __construct($params) {
        $this->params = $params;
    }
    public function get_json_params() {
        return $this->params;
    }
}

// WooCommerce Classes
class WC_Order {
    public $id;
    public $status = 'pending';
    public $meta = [];
    public $notes = [];

    public function __construct($id) {
        $this->id = $id;
    }
    public function get_id() { return $this->id; }
    public function get_status() { return $this->status; }
    public function payment_complete($tx) {
        $this->status = 'processing';
    }
    public function update_meta_data($key, $val) { $this->meta[$key] = $val; }
    public function delete_meta_data($key) { unset($this->meta[$key]); }
    public function add_order_note($note) { $this->notes[] = $note; }
    public function save() {}
    public function get_total() { return 100.00; }
    public function get_billing_first_name() { return 'Test'; }
    public function get_billing_last_name() { return 'User'; }
    public function get_billing_email() { return 'test@example.com'; }
    public function get_billing_phone() { return '11999999999'; }
    public function get_billing_postcode() { return '12345678'; }
    public function get_meta($key) { return isset($this->meta[$key]) ? $this->meta[$key] : ''; }
    public function get_billing_address_1() { return 'Rua Teste, 123'; }
    public function get_billing_address_2() { return ''; }
}

class WC_Payment_Gateway {
    public $id;
    public $method_title;
    public $method_description;
    public $has_fields;
    public $supports;
    public $title;
    public $description;
    public $enabled;
    public $form_fields;
    public function init_form_fields() {}
    public function init_settings() {}
    public function get_option($key, $default = '') { return $default; }
    public function is_available() { return true; }
    public function get_return_url($order) { return 'http://example.com/return'; }
}

// Mock the Gateway class constant used by the validation function
class WC_Gateway_InfinitePay_HP0S {
    const API_PAYMENTCHECK = 'https://api.infinitepay.io/invoices/public/checkout/payment_check';
}


// Mock Data
$mock_orders = [];

// Functions
function wc_get_order($id) {
    global $mock_orders;
    return isset($mock_orders[$id]) ? $mock_orders[$id] : false;
}

function sanitize_text_field($str) { return trim((string)$str); }
function esc_url_raw($url) { return $url; }
function esc_html($str) { return $str; }
function __($str, $domain = '') { return $str; }
function _e($str, $domain = '') { echo $str; }
function is_email($email) { return filter_var($email, FILTER_VALIDATE_EMAIL); }
function wc_price($price) { return '$' . $price; }
function wc_add_notice($message, $type = 'success') {}
function wc_get_logger() { return new class { public function log($l, $m, $c) {} }; }
function rest_url($path = '') { return 'http://example.com/wp-json/' . $path; }

function get_option($key, $default = false) {
    if ($key === 'woocommerce_infinitepay_hpos_settings') {
        return ['handle' => 'test_handle', 'enabled' => 'yes'];
    }
    return $default;
}

// Mock HTTP functions
function wp_remote_post($url, $args) {
    // Simulate API response
    $body = json_decode($args['body'], true);

    // Check if this is the payment check call
    if (strpos($url, 'payment_check') !== false) {
        // Only return success if specific 'valid' transaction data is provided
        if (isset($body['transaction_nsu']) && $body['transaction_nsu'] === 'valid_tx') {
            return [
                'response' => ['code' => 200],
                'body' => json_encode(['success' => true, 'paid' => true])
            ];
        } else {
             return [
                'response' => ['code' => 200],
                'body' => json_encode(['success' => false, 'paid' => false])
            ];
        }
    }
    // Mock checkout link creation
    if (strpos($url, 'checkout/links') !== false) {
        return [
            'response' => ['code' => 201],
            'body' => json_encode(['url' => 'http://payment.url'])
        ];
    }
    return new WP_Error('http', 'error');
}

function wp_remote_retrieve_response_code($res) { return $res['response']['code']; }
function wp_remote_retrieve_body($res) { return $res['body']; }
function is_wp_error($thing) { return $thing instanceof WP_Error; }
function wp_json_encode($data, $options = 0) { return json_encode($data, $options); }

// Hooks
function add_action($tag, $callback, $priority = 10, $accepted_args = 1) {}
function add_filter($tag, $callback, $priority = 10, $accepted_args = 1) {}
function register_rest_route($ns, $route, $args) {}
