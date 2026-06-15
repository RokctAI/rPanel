# API Reference: website_status_report

Source file: `rpanel/hosting/report/website_status_report/website_status_report.py`

## Documented Module Functions

### `def get_data(filters)`
Get website status using database-agnostic Frappe ORM queries.
Tenant/session.user context is preserved.

### `def get_chart_data(data)`
Generate chart showing website status distribution
