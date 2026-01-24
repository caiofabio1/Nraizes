# Sentinel's Journal

## 2025-02-18 - Unverified Payment Webhook
**Vulnerability:** The InfinitePay webhook handler (`wc_infinitepay_webhook_handler`) in `infinitepay-hpos-fixed.php` accepted any request with valid JSON keys and marked orders as paid without verification.
**Learning:** Global webhook functions (outside the Gateway class) do not automatically have access to gateway settings (`$this->get_option` is not available). Developers often forget to manually retrieve options (`get_option('woocommerce_gateway_id_settings')`) to perform verification.
**Prevention:** Always verify payment webhooks by calling back the payment provider's API (e.g., `payment_check`) or verifying a signature using a secret stored in settings. For global functions, ensure settings are retrieved explicitly.
