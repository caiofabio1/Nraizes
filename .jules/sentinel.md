## 2024-05-22 - Missing Security Headers
**Vulnerability:** The application lacks standard HTTP security headers (X-Content-Type-Options, X-Frame-Options, X-XSS-Protection, Referrer-Policy).
**Learning:** WordPress themes often focus on functionality and rely on plugins for security headers, but a "Security" module in a child theme should enforce these defaults for defense-in-depth.
**Prevention:** Implement a default set of security headers in the theme's initialization hook, independent of plugins.
