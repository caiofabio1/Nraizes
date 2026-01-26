
import os

def test_admin_tools_escaped():
    """
    Verify that wp-content/themes/organium-child/inc/admin-tools.php
    uses esc_html with print_r.
    """
    file_path = 'wp-content/themes/organium-child/inc/admin-tools.php'

    with open(file_path, 'r') as f:
        content = f.read()

    # Check for the secure pattern
    secure_pattern = "echo esc_html(print_r($results, true));"

    # Check for the insecure pattern
    insecure_pattern = "print_r($results);"

    if insecure_pattern in content:
         assert False, f"Found insecure pattern in {file_path}"

    if secure_pattern not in content:
        assert False, f"Did not find secure pattern in {file_path}"

    print("✅ Verified: Admin tools output is escaped.")

if __name__ == "__main__":
    test_admin_tools_escaped()
