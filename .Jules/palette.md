## 2026-01-28 - Custom Progress Bar Accessibility
**Learning:** Custom `div`-based progress bars are invisible to screen readers without ARIA roles.
**Action:** Always add `role="progressbar"`, `aria-valuenow`, and `aria-labelledby` linking to the status text.
