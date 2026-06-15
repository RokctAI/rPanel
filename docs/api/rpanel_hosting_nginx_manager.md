# API Reference: nginx_manager

Source file: `rpanel/hosting/nginx_manager.py`

## Module Description
Nginx Configuration Manager for RPanel

This module manages Nginx configurations for hosted websites while being aware of:
- Frappe bench config (frappe-bench-frappe)

It ensures RPanel never conflicts with these existing configurations.

## Classes

### class `NginxManager`
Manages Nginx configurations for RPanel websites

#### Documented Internal Methods
##### `is_protected_config(self, filename)`
Check if a config file is protected (managed by Frappe/ROKCT)

##### `get_rpanel_config_name(self, domain)`
Get the config filename for a domain

##### `create_website_config(self, domain, site_path, php_version=None)`
Create Nginx config for a hosted website

Args:
    domain: Website domain name
    site_path: Absolute path to website root
    php_version: PHP version to use (discovered if None)

##### `enable_site(self, config_name)`
Enable a site by creating symlink in sites-enabled

##### `disable_site(self, config_name)`
Disable a site by removing symlink from sites-enabled

##### `test_and_reload(self)`
Test Nginx config and reload if valid

## Documented Module Functions

### `def setup_nginx_rate_limiting()`
Setup global rate limiting (run during installation)

### `def _safe_path(base, untrusted)`
Validate that resolved path stays within base directory (Layer 18 ZTNA).
