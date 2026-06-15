# API Reference: postgres_utils

Source file: `rpanel/hosting/postgres_utils.py`

## Module Description
Secure PostgreSQL command execution utilities.

## Documented Module Functions

### `def create_pg_database(db_name, db_user, db_password)`
Create a new PG database and user.

### `def run_pg_dump(database, output_file, user='postgres', password=None, host='localhost', as_sudo=False)`
Execute pg_dump securely without exposing passwords.

Args:
    database: Database to dump
    output_file: Path to output SQL file
    user: PostgreSQL user
    password: PostgreSQL password (passed via PGPASSWORD env var)
    host: PostgreSQL host (default: localhost)
    as_sudo: Run with sudo (default: False)

Returns:
    subprocess.CompletedProcess instance

Example:
    run_pg_dump("mydb", "/backups/mydb.sql", user="dbuser", password="secret")

### `def run_pg_restore(database, input_file, user='postgres', password=None, host='localhost', as_sudo=False)`
Restore a PostgreSQL database from SQL file securely.

Args:
    database: Target database
    input_file: Path to SQL file to import
    user: PostgreSQL user
    password: PostgreSQL password (passed via PGPASSWORD env var)
    host: PostgreSQL host (default: localhost)
    as_sudo: Run with sudo (default: False)

Returns:
    subprocess.CompletedProcess instance

Example:
    run_pg_restore("mydb", "/backups/mydb.sql", user="dbuser", password="secret")
