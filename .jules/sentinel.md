## 2024-05-23 - WordPress Canonical Redirect Race Condition
**Vulnerability:** User Enumeration Protection Bypass
**Learning:** WordPress's `redirect_canonical` function runs at priority 10 on `template_redirect` and will redirect `?author=1` to `/author/username/` BEFORE standard security checks running at the same or lower priority (higher number) can block it.
**Prevention:** Security hooks intended to block access based on query parameters in WordPress must run at priority < 10 (e.g., 5) on `template_redirect` to preempt core redirects.
