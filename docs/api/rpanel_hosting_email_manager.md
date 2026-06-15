# API Reference: email_manager

Source file: `rpanel/hosting/email_manager.py`

## Whitelisted API Endpoints

### `def generate_dkim_keys(domain, selector='default')`
Generate DKIM keys for a domain using opendkim-genkey

### `def get_spf_record(domain, ip_address=None)`
Generate SPF record for a domain

## Documented Module Functions

### `def _safe_path(base, untrusted)`
Validate that resolved path stays within base directory (Layer 18 ZTNA).
