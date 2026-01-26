## 2024-05-23 - Unescaped Debug Output in Admin Tools
**Vulnerability:** Stored XSS in admin tools via unescaped `print_r` output of product data.
**Learning:** Custom admin tools often lack the rigorous review of frontend code. Debugging code (`print_r`) left in production UI is a common source of XSS.
**Prevention:** Always use `esc_html()` or `esc_textarea()` when outputting raw data arrays or objects, even in admin panels.
