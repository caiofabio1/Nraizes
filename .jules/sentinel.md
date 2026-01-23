# Sentinel Journal

## 2026-01-23 - Authentication Bypass in Payment Webhook
**Vulnerability:** The InfinitePay webhook handler `wc_infinitepay_webhook_handler` accepted any POST request with an order ID and transaction ID, marking the order as paid without verifying the authenticity of the request.
**Learning:** Standalone webhook handler functions often lack the context/properties of the main Gateway class. In this case, the verification method `wc_infinitepay_payment_check` existed but was not called by the handler, likely because the handler was decoupled from the class instance that held the necessary API credentials.
**Prevention:** Enforce a "Trust but Verify" pattern for all webhooks. If a signature check is not possible/configured, mandate a synchronous callback to the payment provider's API to confirm the transaction status before updating the order. Ensure webhook handlers have access to necessary credentials to perform this check.
