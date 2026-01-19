# Sentinel's Journal

## 2024-05-20 - Missing Security Headers and Enumeration
**Vulnerability:** The codebase lacked basic HTTP security headers (X-Frame-Options, X-Content-Type-Options) and allowed user enumeration via `?author=N` queries.
**Learning:** Even with a `security.php` file present, "empty" files often indicate planned but unimplemented security features.
**Prevention:** Always verify the content of security files, not just their existence.
