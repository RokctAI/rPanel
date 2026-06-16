# API Reference: mysql_utils

Source file: `rpanel/hosting/mysql_utils.py`

## Module Description
Secure MySQL/MariaDB command execution utilities.

Prevents password exposure in process lists by using temporary config files.

## Documented Module Functions

### `def run_mysql_command(sql, database=None, user='root', password=None, host='localhost', as_sudo=True)`
Execute a MySQL command securely without exposing passwords.

Args:
    sql: SQL statement to execute
    database: Database name (optional)
    user: MySQL user (default: root)
    password: MySQL password (passed securely via config file)
    host: MySQL host (default: localhost)
    as_sudo: Run with sudo privileges (default: True)

Returns:
    subprocess.CompletedProcess instance

Example:
    run_mysql_command("CREATE DATABASE mydb", user=frappe.conf.get("db_user", "root"), password=frappe.conf.get("db_password", ""))

### `def run_mysqldump(database, output_file, user='root', password=None, host='localhost', tables=None, as_sudo=False)`
Execute mysqldump securely without exposing passwords.

Args:
    database: Database to dump
    output_file: Path to output SQL file
    user: MySQL user (default: root)
    password: MySQL password (passed securely)
    host: MySQL host (default: localhost)
    tables: Specific tables to dump (optional)
    as_sudo: Run with sudo (default: False for mysqldump)

Returns:
    subprocess.CompletedProcess instance

Example:
    run_mysqldump("mydb", "/backups/mydb.sql", user=frappe.conf.get("db_user", "root"), password=frappe.conf.get("db_password", ""))

### `def run_mysql_restore(database, input_file, user='root', password=None, host='localhost', as_sudo=False)`
Restore a MySQL database from SQL file securely.

Args:
    database: Target database
    input_file: Path to SQL file to import
    user: MySQL user (default: root)
    password: MySQL password (passed securely)
    host: MySQL host (default: localhost)
    as_sudo: Run with sudo (default: False)

Returns:
    subprocess.CompletedProcess instance

Example:
    run_mysql_restore("mydb", "/backups/mydb.sql", user=frappe.conf.get("db_user", "root"), password=frappe.conf.get("db_password", ""))

### `def _safe_path(base, untrusted)`
Validate that resolved path stays within base directory (Layer 18 ZTNA).
