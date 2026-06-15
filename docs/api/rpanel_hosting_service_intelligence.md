# API Reference: service_intelligence

Source file: `rpanel/hosting/service_intelligence.py`

## Classes

### class `ServiceIntelligence`
Dynamic detection of service versions and paths.
Ensures RPanel works across different Ubuntu/Debian distributions
without hardcoded version strings.

#### Documented Internal Methods
##### `get_default_php_version()`
Detect the best PHP version to use as default

##### `get_php_fpm_socket(version=None, user=None)`
Get path to PHP-FPM socket

##### `get_php_fpm_pool_dir(version=None)`
Get PHP-FPM pool configuration directory

## Documented Module Functions

### `def _safe_path(base, untrusted)`
Validate that resolved path stays within base directory (Layer 18 ZTNA).
