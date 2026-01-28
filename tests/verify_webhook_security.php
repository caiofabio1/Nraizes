<?php
// Tests/verify_webhook_security.php

// Mock WP Environment
define('ABSPATH', '/tmp/');

// Global state for assertions
$global_state = [
    'payment_complete_called' => false,
    'wp_remote_post_called' => false,
];

function add_action($hook, $callback, $priority = 10, $accepted_args = 1) {}
function add_filter($hook, $callback, $priority = 10, $accepted_args = 1) {}
function register_rest_route($ns, $route, $args) {}
function sanitize_text_field($str) { return trim($str); }
function esc_url_raw($url) { return $url; }
function is_wp_error($thing) { return $thing instanceof WP_Error; }
function wc_get_logger() { return new MockLogger(); }
function wp_json_encode($data) { return json_encode($data); }
function rest_url($path) { return 'http://localhost/wp-json/' . $path; }

// Mock Option for Settings
function get_option($option, $default = false) {
    if ($option === 'woocommerce_infinitepay_hpos_settings') {
        return ['handle' => 'test_handle'];
    }
    return $default;
}

// Mock HTTP Requests
function wp_remote_post($url, $args) {
    global $global_state;
    // Only track calls to the payment check API
    if (strpos($url, 'payment_check') !== false) {
        $global_state['wp_remote_post_called'] = true;

        // Return a response that says "NOT PAID" to verify the fix works (it should block payment_complete)
        return [
            'response' => ['code' => 200],
            'body' => json_encode(['success' => true, 'paid' => false])
        ];
    }
    return ['response' => ['code' => 200], 'body' => '{}'];
}

function wp_remote_retrieve_response_code($response) { return $response['response']['code']; }
function wp_remote_retrieve_body($response) { return $response['body']; }

class WP_Error {}
class WP_REST_Response {
    public $data;
    public $status;
    public function __construct($data, $status) { $this->data = $data; $this->status = $status; }
}

class WC_Payment_Gateway {}

// Define the class and constant needed by the global function
class WC_Gateway_InfinitePay_HP0S extends WC_Payment_Gateway {
    const API_PAYMENTCHECK = 'https://api.infinitepay.io/invoices/public/checkout/payment_check';
}

class WC_Order {
    public function get_id() { return 123; }
    public function get_status() { return 'pending'; }
    public function payment_complete($tx) {
        global $global_state;
        $global_state['payment_complete_called'] = true;
    }
    public function update_meta_data($key, $val) {}
    public function delete_meta_data($key) {}
    public function add_order_note($note) {}
    public function save() {}
}

function wc_get_order($id) {
    if ($id == 123) return new WC_Order();
    return false;
}

class WP_REST_Request {
    private $params;
    public function __construct($params) { $this->params = $params; }
    public function get_json_params() { return $this->params; }
}

class MockLogger { public function log($l, $m, $c) {} }

// Include the file to test
require_once 'wp-content/themes/organium-child/infinitepay-hpos-fixed.php';

// --- TEST EXECUTION ---

// Payload
$payload = [
    'order_nsu' => '123',
    'transaction_nsu' => 'tx_fake',
    'invoice_slug' => 'slug_fake',
    'receipt_url' => 'http://fake.com/receipt'
];

$request = new WP_REST_Request($payload);

echo "Running wc_infinitepay_webhook_handler...\n";
$response = wc_infinitepay_webhook_handler($request);

echo "Handler returned status: " . $response->status . "\n";
echo "Payment Complete Called: " . ($global_state['payment_complete_called'] ? 'YES' : 'NO') . "\n";
echo "Verification API Called: " . ($global_state['wp_remote_post_called'] ? 'YES' : 'NO') . "\n";

// Validation Logic for the test script
// If the fix is applied:
// We expect API Called = YES
// We expect Payment Complete = NO (because the API returns paid=false)

// If the vulnerability is present:
// We expect API Called = NO (or YES if it was already there, but it wasn't)
// We expect Payment Complete = YES

if ($global_state['wp_remote_post_called'] && !$global_state['payment_complete_called']) {
    echo "SUCCESS: Fix is working. Payment check was performed and payment was NOT completed because check failed.\n";
    exit(0);
} elseif (!$global_state['wp_remote_post_called'] && $global_state['payment_complete_called']) {
    echo "FAIL: Vulnerability present. Payment completed WITHOUT verification.\n";
    exit(1);
} else {
    echo "FAIL: Unexpected state (API: " . ($global_state['wp_remote_post_called'] ? 'Y' : 'N') . ", Complete: " . ($global_state['payment_complete_called'] ? 'Y' : 'N') . ").\n";
    exit(1);
}
