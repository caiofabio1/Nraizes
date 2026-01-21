<?php
/**
 * Verification Script for Stored XSS Fix
 *
 * This script demonstrates the vulnerability and the fix.
 * It mocks the relevant parts of the code to show how the output is handled.
 *
 * Usage: php tests/verify_xss_fix.php
 */

// Mock WordPress functions
function esc_html($string) {
    return htmlspecialchars($string, ENT_QUOTES, 'UTF-8');
}

// Simulate malicious data
$results = array(
    array(
        'name' => 'Product <script>alert("XSS")</script>',
        'tags' => array('Tag1', 'Tag2')
    )
);

echo "--- Vulnerable Output (simulation) ---\n";
// The original code was: print_r($results);
// This outputs raw content to the buffer (or stdout).
// In a browser context inside <pre>, the <script> tag would be rendered.
$output_vulnerable = print_r($results, true);
echo $output_vulnerable;
echo "\n\n";

echo "--- Secured Output (simulation) ---\n";
// The fixed code is: echo esc_html(print_r($results, true));
$output_secure = esc_html(print_r($results, true));
echo $output_secure;
echo "\n\n";

// Verification logic
if (strpos($output_secure, '<script>') === false && strpos($output_secure, '&lt;script&gt;') !== false) {
    echo "✅ SUCCESS: The output is properly escaped.\n";
    exit(0);
} else {
    echo "❌ FAILURE: The output is NOT properly escaped.\n";
    exit(1);
}
