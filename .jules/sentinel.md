# Sentinel's Journal

## 2026-01-30 - Unverified Payment Webhooks
**Vulnerability:** The InfinitePay webhook handler blindly accepted payment confirmations based solely on the POST body, allowing anyone to mark orders as paid without actual payment.
**Learning:** Payment gateways often provide webhooks that include payment status, but these must *always* be verified either by signature validation (HMAC) or by querying the gateway's API directly to confirm the status before updating the order. Trusting the webhook payload directly is a critical flaw.
**Prevention:** Always implement a verification step in webhook handlers. If signature validation is not available or complex, use a "callback" pattern where the webhook triggers a server-side check against the payment provider's API.
