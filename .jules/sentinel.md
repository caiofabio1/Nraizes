## 2024-05-23 - Missing Security Controls
**Vulnerability:** Core security headers (X-Frame-Options, HSTS, etc.) and user enumeration protection were completely missing from the codebase.
**Learning:** Memory/Documentation indicated these controls were present, but the actual code (inc/security.php) only contained XML-RPC disabling. This discrepancy suggests a potential rollback or sync issue in the past.
**Prevention:** Always verify "known" security controls by inspecting the actual code, not just relying on documentation or memory.
