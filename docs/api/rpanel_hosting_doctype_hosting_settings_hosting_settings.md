# API Reference: hosting_settings

Source file: `rpanel/hosting/doctype/hosting_settings/hosting_settings.py`

## Classes

### class `HostingSettings`

#### Whitelisted API Methods
##### `renew_platform_ssl(self)`
API endpoint: renew platform ssl.

##### `renew_wildcard_ssl(self)`
API endpoint: renew wildcard ssl.

##### `install_roundcube(self)`
Installs Roundcube Webmail to /var/www/roundcube

## Whitelisted API Endpoints

### `def get_system_status()`
Check status of system services

### `def reload_nginx()`
Reload Nginx configuration

### `def test_email(email)`
Send a test email to verify email configuration

## Documented Module Functions

### `def _safe_path(base, untrusted)`
Validate that resolved path stays within base directory (Layer 18 ZTNA).
