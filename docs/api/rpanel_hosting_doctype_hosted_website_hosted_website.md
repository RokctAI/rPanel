# API Reference: hosted_website

Source file: `rpanel/hosting/doctype/hosted_website/hosted_website.py`

## Classes

### class `HostedWebsite`

#### Whitelisted API Methods
##### `provision_site(self)`
Creates directory and basic config

#### Documented Internal Methods
##### `check_client_quota(self)`
Check if client has exceeded their website quota

## Documented Module Functions

### `def _safe_path(base, untrusted)`
Validate that resolved path stays within base directory (Layer 18 ZTNA).
