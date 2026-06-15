# API Reference: modsecurity_manager

Source file: `rpanel/hosting/modsecurity_manager.py`

## Module Description
ModSecurity Manager

Manages ModSecurity Web Application Firewall configuration for RPanel websites.
Protects against: SQL Injection, XSS, File Inclusion, Command Injection, CSRF, etc.

## Classes

### class `ModSecurityManager`
Manages ModSecurity WAF configuration

#### Documented Internal Methods
##### `setup_modsecurity(self)`
Initial setup of ModSecurity
Installs OWASP Core Rule Set and creates base configuration

## Documented Module Functions

### `def setup_modsecurity()`
Setup ModSecurity (run during installation)
