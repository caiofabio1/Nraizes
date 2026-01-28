## 2026-01-28 - Critical Payment Webhook Bypass
**Vulnerability:** The InfinitePay webhook handler blindly trusted incoming requests, allowing any attacker to mark orders as paid by sending a JSON payload with a valid order ID.
**Learning:** Payment gateways often separate the "Gateway Class" logic from "Webhook Handler" logic (REST API). Checks present in the Gateway Class might not be automatically applied to the REST handler unless explicitly invoked.
**Prevention:** Always implement a "verify with source" step in webhook handlers. Do not trust the payload alone. Explicitly retrieve settings and call verification endpoints before changing order status.
