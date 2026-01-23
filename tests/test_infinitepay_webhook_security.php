<?php
require_once 'tests/mock_wp_environment.php';
require_once 'wp-content/themes/organium-child/infinitepay-hpos-fixed.php';

// --- Test Execution ---

echo "--- 🛡️ Verifying Fix on ACTUAL FILE ---\n";

// TEST CASE 1: Invalid Transaction (Attack Attempt)
$order_attack = new WC_Order(666);
$mock_orders[666] = $order_attack;

echo "\nTest Case 1: Attack Attempt (Invalid TX)\n";
$payload_attack = [
    'order_nsu' => '666',
    'transaction_nsu' => 'invalid_fake_tx',
    'invoice_slug' => 'slug_666'
];

$request = new WP_REST_Request($payload_attack);
$response = wc_infinitepay_webhook_handler($request);

echo "Response Status: " . $response->status . " (Expected: 400)\n";
echo "Order Status: " . $order_attack->get_status() . " (Expected: pending)\n";

if ($response->status === 400 && $order_attack->get_status() === 'pending') {
    echo "✅ SUCCESS: Attack blocked.\n";
} else {
    echo "❌ FAILED: Attack was not properly blocked.\n";
    exit(1);
}


// TEST CASE 2: Valid Transaction (Legitimate Payment)
$order_legit = new WC_Order(777);
$mock_orders[777] = $order_legit;

echo "\nTest Case 2: Legitimate Payment (Valid TX)\n";
$payload_legit = [
    'order_nsu' => '777',
    'transaction_nsu' => 'valid_tx', // Matches mock_wp_environment "valid" check
    'invoice_slug' => 'slug_777'
];

$request = new WP_REST_Request($payload_legit);
$response = wc_infinitepay_webhook_handler($request);

echo "Response Status: " . $response->status . " (Expected: 200)\n";
echo "Order Status: " . $order_legit->get_status() . " (Expected: processing)\n";

if ($response->status === 200 && $order_legit->get_status() === 'processing') {
    echo "✅ SUCCESS: Legitimate payment processed.\n";
} else {
    echo "❌ FAILED: Legitimate payment failed.\n";
    exit(1);
}

echo "\n🎉 ALL TESTS PASSED. Fix is verified.\n";
exit(0);
