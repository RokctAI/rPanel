# API Reference: ssl_expiry_report

Source file: `rpanel/hosting/report/ssl_expiry_report/ssl_expiry_report.py`

## Documented Module Functions

### `def get_data(filters)`
Get SSL Expiry data using Frappe ORM to guarantee database-agnostic compatibility.
Tenant/session.user context is preserved.
