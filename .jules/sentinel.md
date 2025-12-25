## 2024-05-22 - [Minimal Security Baseline]
**Vulnerability:** Lack of basic WordPress hardening (User Enumeration, Version Leaking, Headers).
**Learning:** The child theme had an `inc/security.php` file but it was underutilized, only disabling XML-RPC. This indicates security was considered but not fully implemented.
**Prevention:** Regularly review and expand the security baseline of the theme using a checklist of standard hardening practices.
