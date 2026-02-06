"""
Secure PostgreSQL command execution utilities.
"""

import os
import subprocess
from typing import Optional
import frappe

def run_psql_command(
    sql: str,
    database: Optional[str] = None,
    user: str = "postgres",
    password: Optional[str] = None,
    host: str = "localhost",
    as_sudo: bool = True
) -> subprocess.CompletedProcess:
    """
    Execute a PostgreSQL command securely.
    """
    # Build environment with password for secure transmission
    env = os.environ.copy()
    if password:
        env["PGPASSWORD"] = password

    # Build command
    cmd = []
    if as_sudo:
        # If we use sudo -u postgres psql, it often uses peer auth and ignores PGPASSWORD
        # so we need to be careful with the user flag.
        cmd.extend(["sudo", "-u", user])
    
    cmd.extend(["psql", "-h", host, "-U", user])
    
    if database:
        cmd.extend(["-d", database])
    
    cmd.extend(["-c", sql])
    
    # Execute command
    return subprocess.run(cmd, env=env, check=True, capture_output=True, text=True)

def create_pg_database(db_name: str, db_user: str, db_password: str):
    """
    Create a new PG database and user.
    """
    try:
        # 1. Create User
        run_psql_command(f"CREATE USER {db_user} WITH PASSWORD '{db_password}';")
        
        # 2. Create Database
        run_psql_command(f"CREATE DATABASE {db_name} OWNER {db_user};")
        
        # 3. Grant Privileges
        run_psql_command(f"GRANT ALL PRIVILEGES ON DATABASE {db_name} TO {db_user};")
        
    except subprocess.CalledProcessError as e:
        frappe.log_error(f"PostgreSQL Setup Failed: {e.stderr}")
        raise
