# API Reference: resource_usage_report

Source file: `rpanel/hosting/report/resource_usage_report/resource_usage_report.py`

## Documented Module Functions

### `def get_data(filters)`
Get Resource Usage Log data using database-agnostic Frappe ORM queries.
Multi-tenant isolation context (tenant / session.user) is preserved.
