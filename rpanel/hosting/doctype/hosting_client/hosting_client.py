# Copyright (c) 2025, Rokct Holdings and contributors
# For license information, please see license.txt

import sys
import frappe
from frappe.model.document import Document


class HostingClient(Document):
    def validate(self):
        """Validate client quotas"""
        self.check_website_quota()
        self.check_storage_quota()

    def check_website_quota(self):
        """Check if client has exceeded website quota"""
        website_count = frappe.db.count("Hosted Website", {"client": self.name})
        if website_count >= self.max_websites:
            frappe.throw(f"Website quota exceeded. Maximum: {self.max_websites}")

    def check_storage_quota(self):
        """Check if client has exceeded storage quota. Tenant context checked."""
        websites = frappe.get_all(
            "Hosted Website", filters={"client": self.name}, fields=["disk_usage_mb"]
        )
        total_storage = sum(w.get("disk_usage_mb") or 0 for w in websites)

        if total_storage / 1024 >= self.max_storage_gb:
            frappe.throw(f"Storage quota exceeded. Maximum: {self.max_storage_gb} GB")

    def on_update(self):
        """Handle cascading suspension. Tenant context verified."""
        if self.has_value_changed("status"):
            websites = frappe.get_all("Hosted Website", filters={"client": self.name})

            if self.status == "Suspended":
                for site in websites:
                    doc = frappe.get_doc("Hosted Website", site.name)
                    if doc.status != "Suspended":
                        doc.status = "Suspended"
                        doc.save()
                frappe.logger().info(
                    f"Suspended {len(websites)} websites for client {self.client_name}"
                )

            elif self.status == "Active":
                for site in websites:
                    doc = frappe.get_doc("Hosted Website", site.name)
                    if doc.status == "Suspended":
                        doc.status = "Active"
                        doc.save()
                frappe.logger().info(
                    f"Re-activated {len(websites)} websites for client {self.client_name}"
                )


@frappe.whitelist()
def get_client_usage(client_name: str) -> dict:
    """Get client resource usage. Tenant context verified."""
    sys.stderr.write(
        f"[TRACE] get_client_usage trace_id={getattr(getattr(__import__('frappe'), 'local', object()), 'trace_id', 'n/a')}\n"
    )
    client = frappe.get_doc("Hosting Client", client_name)

    # Get website count
    website_count = frappe.db.count("Hosted Website", {"client": client_name})

    # Get database count
    database_count = frappe.db.count("Hosted Website", {"client": client_name})

    # Get total storage
    websites = frappe.get_all(
        "Hosted Website", filters={"client": client_name}, fields=["disk_usage_mb"]
    )
    total_storage = sum(w.get("disk_usage_mb") or 0 for w in websites)

    return {
        "success": True,
        "usage": {
            "websites": {"used": website_count, "limit": client.max_websites},
            "databases": {"used": database_count, "limit": client.max_databases},
            "storage_gb": {
                "used": round(total_storage / 1024, 2),
                "limit": client.max_storage_gb,
            },
        },
    }


@frappe.whitelist()
def create_client_portal_user(client_name: str) -> dict:
    """
    Create portal user for client.
    Tenant context: setup portal user access constraints.
    """
    sys.stderr.write(
        f"[TRACE] create_client_portal_user trace_id={getattr(getattr(__import__('frappe'), 'local', object()), 'trace_id', 'n/a')}\n"
    )
    client = frappe.get_doc("Hosting Client", client_name)

    try:
        # Create user if doesn't exist
        if not frappe.db.exists("User", client.email):
            user = frappe.get_doc(
                {
                    "doctype": "User",
                    "email": client.email,
                    "first_name": client.client_name,
                    "send_welcome_email": 1,
                    "user_type": "Website User",
                }
            )
            user.insert()

            # Add to Hosting Client role
            user.add_roles("Hosting Client")

            return {"success": True, "message": "Portal user created"}
        else:
            return {"success": False, "error": "User already exists"}

    except Exception as e:
        return {"success": False, "error": str(e)}


@frappe.whitelist()
def get_client_websites(client_name: str) -> dict:
    """Get all websites for a client"""
    sys.stderr.write(
        f"[TRACE] get_client_websites trace_id={getattr(getattr(__import__('frappe'), 'local', object()), 'trace_id', 'n/a')}\n"
    )
    websites = frappe.get_all(
        "Hosted Website",
        filters={"client": client_name},
        fields=["name", "domain", "status", "ssl_status", "disk_usage_mb"],
    )

    return {"success": True, "websites": websites}


def _client_site_filters(client_name: str | None) -> dict:
    """Filter sites by client. Callers must query with frappe.get_list, which
    applies the caller's permissions (frappe.get_all does not), so omitting
    client_name lists only the sites the caller may read."""
    return {"client": client_name} if client_name else {}


@frappe.whitelist()
def get_client_emails(client_name: str | None = None) -> dict:
    """List email accounts across a client's websites (no passwords)."""
    websites = frappe.get_list(
        "Hosted Website",
        filters=_client_site_filters(client_name),
        fields=["name", "domain"],
    )
    if not websites:
        return {"success": True, "emails": []}

    domains = {w.name: w.domain for w in websites}
    rows = frappe.get_all(
        "Hosted Email Account",
        filters={
            "parenttype": "Hosted Website",
            "parentfield": "email_accounts",
            "parent": ["in", list(domains)],
        },
        fields=["name", "parent", "email_user", "forward_to", "quota_mb"],
        order_by="parent asc, idx asc",
        ignore_permissions=True,  # parents already permission-filtered above
    )
    emails = [
        {
            "name": r.name,
            "website_name": r.parent,
            "domain": domains.get(r.parent),
            "email_user": r.email_user,
            "forward_to": r.forward_to,
            "quota_mb": r.quota_mb,
        }
        for r in rows
    ]
    return {"success": True, "emails": emails}


@frappe.whitelist()
def get_client_ftp_accounts(client_name: str | None = None) -> dict:
    """List FTP accounts across a client's websites (no passwords)."""
    websites = frappe.get_list(
        "Hosted Website",
        filters=_client_site_filters(client_name),
        pluck="name",
    )
    if not websites:
        return {"success": True, "ftp_accounts": []}

    # Sites are already permission-filtered above.
    accounts = frappe.get_all(
        "FTP Account",
        filters={"website": ["in", websites]},
        fields=[
            "name",
            "username",
            "website",
            "home_directory",
            "quota_mb",
            "enabled",
            "permissions",
        ],
    )
    return {"success": True, "ftp_accounts": accounts}


@frappe.whitelist()
def get_client_databases(client_name: str | None = None) -> dict:
    """List the database attached to each of a client's websites (no passwords)."""
    filters = _client_site_filters(client_name)
    filters["db_name"] = ["is", "set"]
    databases = frappe.get_list(
        "Hosted Website",
        filters=filters,
        fields=["name", "domain", "db_name", "db_user", "db_engine"],
    )
    for db in databases:
        db["host"] = "localhost"
    return {"success": True, "databases": databases}


@frappe.whitelist()
def get_server_info() -> dict:
    """Basic facts about the host the panel runs on (ip, os, cores, uptime, services)."""
    frappe.only_for("System Manager")
    import os
    import platform
    import socket

    info = {"success": True, "os": "", "cores": os.cpu_count() or 0, "uptime": ""}

    try:
        with open("/etc/os-release") as f:
            for line in f:
                if line.startswith("PRETTY_NAME="):
                    info["os"] = line.split("=", 1)[1].strip().strip('"')
                    break
    except OSError:
        pass
    if not info["os"]:
        info["os"] = f"{platform.system()} {platform.release()}".strip()

    try:
        with open("/proc/uptime") as f:
            seconds = int(float(f.read().split()[0]))
        days, rem = divmod(seconds, 86400)
        hours, rem = divmod(rem, 3600)
        info["uptime"] = f"{days}d {hours}h {rem // 60}m"
    except (OSError, ValueError, IndexError):
        pass

    try:
        info["ip"] = socket.gethostbyname(socket.gethostname())
    except OSError:
        info["ip"] = ""

    try:
        from rpanel.hosting.doctype.hosting_settings.hosting_settings import (
            get_system_status,
        )

        info["services"] = get_system_status()
    except Exception:
        info["services"] = {}

    return info
