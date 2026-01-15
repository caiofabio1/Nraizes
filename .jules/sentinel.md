# Sentinel's Journal

## 2024-05-22 - Missing Security Headers vs Memory
**Vulnerability:** The codebase lacked standard security headers (HSTS, X-Frame-Options, etc.) despite internal documentation/memory suggesting they were implemented in `inc/security.php`.
**Learning:** Reliance on memory or documentation without verification can lead to security gaps. The file `inc/security.php` only contained XML-RPC disabling code.
**Prevention:** Always verify the actual code content against security claims. Implemented `nraizes_security_headers` to enforce these protections.
