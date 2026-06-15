# API Reference: server_provisioner

Source file: `rpanel/hosting/server_provisioner.py`

## Whitelisted API Endpoints

### `def provision_server(server_name)`
Automatically install and configure all required services on a remote server
- Nginx
- MariaDB
- PostgreSQL
- PHP-FPM (multiple versions)
- phpMyAdmin
- Certbot (Let's Encrypt)
- Exim4 (email)
- Roundcube (webmail)
- WordPress CLI
- ClamAV (malware scanner)
- Fail2Ban
- UFW (firewall)

### `def check_server_services(server_name)`
Check which services are installed on the server
