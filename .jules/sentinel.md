## 2024-05-22 - Missing Security Headers vs Memory
**Vulnerability:** Missing HTTP Security Headers (HSTS, X-Frame-Options, etc.)
**Learning:** Memory indicated headers were present in `inc/security.php`, but the file only contained XML-RPC disabling. This discrepancy suggests either a regression or an environment sync issue.
**Prevention:** Always verify current code state against documentation/memory before assuming security controls are active. Added headers back to enforce security posture.
