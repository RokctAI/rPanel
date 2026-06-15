# API Reference: dns_zone

Source file: `rpanel/hosting/doctype/dns_zone/dns_zone.py`

## Classes

### class `DNSZone`

#### Documented Internal Methods
##### `validate(self)`
Validate DNS zone

##### `on_update(self)`
Sync with Cloudflare after update if enabled

##### `sync_with_cloudflare(self)`
Sync DNS zone with Cloudflare

## Whitelisted API Endpoints

### `def sync_with_cloudflare(zone_name)`
Manually sync DNS zone with Cloudflare

### `def check_dns_propagation(domain, record_type='A')`
Check DNS propagation status

### `def get_common_records()`
Get common DNS record templates
