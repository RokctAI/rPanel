# API Reference: database_manager

Source file: `rpanel/hosting/database_manager.py`

## Whitelisted API Endpoints

### `def execute_query(database_name, query)`
Execute SQL query

### `def get_tables(database_name)`
Get list of tables in database

### `def export_database(database_name, export_format='sql')`
Export database

### `def import_database(database_name, import_file)`
Import database from SQL file

### `def optimize_database(database_name)`
Optimize all tables in database
