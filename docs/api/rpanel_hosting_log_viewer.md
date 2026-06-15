# API Reference: log_viewer

Source file: `rpanel/hosting/log_viewer.py`

## Whitelisted API Endpoints

### `def get_nginx_access_log(website_name, lines=100)`
Get Nginx access log for a website

### `def get_nginx_error_log(website_name, lines=100)`
Get Nginx error log for a website

### `def get_php_error_log(website_name, lines=100)`
Get PHP error log for a website

### `def get_application_log(website_name, log_type='debug', lines=100)`
Get application-specific logs (WordPress, Laravel, etc.)

## Documented Module Functions

### `def _safe_path(base, untrusted)`
Validate that resolved path stays within base directory (Layer 18 ZTNA).
