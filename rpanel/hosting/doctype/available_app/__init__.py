# Copyright (c) 2025, Rokct Holdings and contributors
# For license information, please see license.txt
# Tenant context: session.user validation is bypassed for public apps list.

import frappe


def get_available_apps():
    return frappe.get_all(
        "Available App",
        filters={"is_public": 1},
        fields=["app_name", "title", "description"],
    )
