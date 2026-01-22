# Sentinel's Journal

## 2024-05-22 - InfinitePay Webhook Authentication Bypass
**Vulnerability:** The custom InfinitePay gateway's webhook endpoint (`/wc-infinitepay/v1/webhook`) allowed unauthorized users to mark orders as paid by sending a crafted POST request with valid Order ID but faked transaction data. It lacked signature verification or secret checking.
**Learning:** Custom payment integrations often neglect webhook security, trusting that "hidden" URLs are safe. However, Order IDs are often sequential or guessable.
**Prevention:** Always verify webhook authenticity. If the provider supports signatures, check them. If not (or as a defense-in-depth), verify the transaction status by calling the provider's API (backend-to-backend) before trusting the webhook payload.
