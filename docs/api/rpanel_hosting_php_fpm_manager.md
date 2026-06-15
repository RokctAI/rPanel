# API Reference: php_fpm_manager

Source file: `rpanel/hosting/php_fpm_manager.py`

## Module Description
PHP-FPM Pool Manager for rpanel

Creates and manages dedicated PHP-FPM pools for website isolation.
Each site can have its own pool running as a specific system user.

## Classes

### class `PHPFPMManager`
Manages PHP-FPM pools for website isolation

#### Documented Internal Methods
##### `create_pool(self, domain, system_user, max_children=5)`
Create dedicated PHP-FPM pool for a site

##### `delete_pool(self, domain)`
Delete PHP-FPM pool for a site

Args:
    domain: Website domain
