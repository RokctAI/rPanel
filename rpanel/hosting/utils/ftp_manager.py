# Copyright (c) 2026, Rokct Intelligence (pty) Ltd.
# For license information, please see license.txt

"""FTP account helpers called by the RokctAI hosting control pages."""

import re

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
