# Sentinel's Journal

## 2026-01-21 - Stored XSS in Admin Tools Debug Output
**Vulnerability:** Found unescaped `print_r($results)` in `inc/admin-tools.php`. This tool displays a preview of product tag updates. Since product names can be influenced by users (e.g. Shop Managers) or imports, a malicious product name containing `<script>` tags would execute JavaScript in the context of the Administrator viewing the tools page.
**Learning:** Developers often treat `print_r` or `var_dump` inside `<pre>` tags as "safe text output". However, `<pre>` only preserves whitespace; it does NOT escape HTML entities. The browser still parses and executes tags inside `<pre>`.
**Prevention:** Always use `esc_html()` when outputting debug data or array structures in HTML, even inside `<pre>`. Example: `echo esc_html(print_r($data, true));`.
