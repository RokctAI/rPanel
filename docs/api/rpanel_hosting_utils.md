# API Reference: utils

Source file: `rpanel/hosting/utils.py`

## Documented Module Functions

### `def _safe_path(base, untrusted)`
Validate that resolved path stays within base directory (Layer 18 ZTNA).

### `def run_certbot(domain, webroot)`
Issues a certificate for the domain using webroot challenge

### `def update_exim_config(domain, accounts)`
Updates Exim4 configuration for a domain.
accounts: list of dicts {'user': 'info', 'password': '...', 'forward_to': '...'}
