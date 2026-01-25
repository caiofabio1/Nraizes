## 2024-05-23 - InfinitePay Webhook Authentication Bypass
**Vulnerability:** The `wc_infinitepay_webhook_handler` function blindly trusted incoming POST requests to mark orders as paid without verifying the transaction with the payment provider.
**Learning:** The webhook handler was defined as a standalone function outside the `WC_Gateway_InfinitePay_HP0S` class, meaning it did not have automatic access to the gateway's settings or helper methods, leading to a missing verification step.
**Prevention:** Always verify webhook payloads against the provider's API or signature before performing sensitive actions like payment completion. Ensure standalone webhook handlers explicitly retrieve necessary configuration.
