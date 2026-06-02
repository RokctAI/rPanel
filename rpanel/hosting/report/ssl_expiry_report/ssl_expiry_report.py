# Copyright (c) 2025, ROKCT Holdings and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {
            "fieldname": "domain",
            "label": _("Domain"),
            "fieldtype": "Link",
            "options": "Hosted Website",
            "width": 200,
        },
        {
            "fieldname": "ssl_status",
            "label": _("SSL Status"),
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "fieldname": "ssl_issuer",
            "label": _("SSL Issuer"),
            "fieldtype": "Data",
            "width": 120,
        },
        {
            "fieldname": "ssl_expiry_date",
            "label": _("Expiry Date"),
            "fieldtype": "Date",
            "width": 120,
        },
        {
            "fieldname": "days_until_expiry",
            "label": _("Days Until Expiry"),
            "fieldtype": "Int",
            "width": 130,
        },
        {
            "fieldname": "status",
            "label": _("Site Status"),
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "fieldname": "site_path",
            "label": _("Site Path"),
            "fieldtype": "Data",
            "width": 200,
        },
    ]


def get_data(filters):
    """
    Get SSL Expiry data using Frappe ORM to guarantee database-agnostic compatibility.
    Tenant/session.user context is preserved.
    """
    from frappe.utils import date_diff, today

    db_filters = {"ssl_status": "Active"}

    if filters.get("domain"):
        db_filters["name"] = ["like", f"%{filters.get('domain')}%"]

    if filters.get("status"):
        db_filters["status"] = filters.get("status")

    websites = frappe.get_all(
        "Hosted Website",
        filters=db_filters,
        fields=[
            "name as domain",
            "ssl_status",
            "ssl_issuer",
            "ssl_expiry_date",
            "status",
            "site_path",
        ],
    )

    current_date = today()
    for w in websites:
        if w.ssl_expiry_date:
            w["days_until_expiry"] = date_diff(w.ssl_expiry_date, current_date)
        else:
            w["days_until_expiry"] = 9999

    if filters.get("expiring_within_days"):
        limit_days = int(filters.get("expiring_within_days"))
        websites = [w for w in websites if w["days_until_expiry"] <= limit_days]

    websites.sort(key=lambda x: x["days_until_expiry"])
    return websites
