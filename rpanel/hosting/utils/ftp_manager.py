# Copyright (c) 2026, Rokct Intelligence (pty) Ltd.
# For license information, please see license.txt

"""FTP account helpers called by the RokctAI hosting control pages."""

import re
import subprocess

import frappe

_USERNAME_RE = re.compile(r"^[a-z_][a-z0-9_-]{0,31}$")


@frappe.whitelist()
def create_ftp_account(website: str, username: str, password: str) -> dict:
    """Create an FTP Account for a hosted website the caller can write to.

    The FTP Account's on_insert hook creates the system user.
    """
    if not frappe.has_permission("Hosted Website", "write", doc=website):
        frappe.throw("Not permitted", frappe.PermissionError)

    if not username or not _USERNAME_RE.match(username):
        return {
            "success": False,
            "error": "Invalid username. Use lowercase letters, digits, _ or -.",
        }
    if not password:
        return {"success": False, "error": "Password is required"}
    if frappe.db.exists("FTP Account", {"username": username}):
        return {"success": False, "error": "FTP username already exists"}

    site = frappe.get_doc("Hosted Website", website)
    ftp = frappe.get_doc(
        {
            "doctype": "FTP Account",
            "username": username,
            "password": password,
            "website": site.name,
            "home_directory": site.site_path,
            "enabled": 1,
        }
    )
    ftp.insert()

    return {"success": True, "name": ftp.name, "username": ftp.username}


def _get_writable_ftp_account(username: str):
    name = frappe.db.get_value("FTP Account", {"username": username}, "name")
    if not name:
        frappe.throw("FTP account not found", frappe.DoesNotExistError)
    ftp = frappe.get_doc("FTP Account", name)
    if not frappe.has_permission("Hosted Website", "write", doc=ftp.website):
        frappe.throw("Not permitted", frappe.PermissionError)
    ftp.check_permission("write")
    return ftp


@frappe.whitelist()
def change_ftp_password(username: str, new_password: str) -> dict:
    """Change an FTP user's system password; store it only if chpasswd succeeds."""
    ftp = _get_writable_ftp_account(username)
    if not new_password:
        return {"success": False, "error": "Password is required"}
    if not _USERNAME_RE.match(ftp.username or ""):
        return {"success": False, "error": "Invalid FTP username"}

    try:
        # Password goes over stdin so it never appears in the process list.
        subprocess.run(
            ["chpasswd"],
            input=f"{ftp.username}:{new_password}",
            text=True,
            check=True,
            capture_output=True,
        )
    except (subprocess.CalledProcessError, OSError):
        frappe.log_error(
            f"chpasswd failed for FTP user {ftp.username}", "FTP password change"
        )
        return {"success": False, "error": "Failed to change the FTP password"}

    ftp.password = new_password
    ftp.save()
    return {"success": True}


@frappe.whitelist()
def delete_ftp_account(username: str) -> dict:
    """Delete an FTP account; its on_trash removes the system user."""
    ftp = _get_writable_ftp_account(username)
    ftp.delete()
    return {"success": True}
