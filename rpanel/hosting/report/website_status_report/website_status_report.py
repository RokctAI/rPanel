# Copyright (c) 2025, ROKCT Holdings and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    chart = get_chart_data(data)
    return columns, data, None, chart


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
            "fieldname": "status",
            "label": _("Status"),
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "fieldname": "site_type",
            "label": _("Site Type"),
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "fieldname": "cms_type",
            "label": _("CMS Type"),
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "fieldname": "php_version",
            "label": _("PHP Version"),
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "fieldname": "ssl_status",
            "label": _("SSL Status"),
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "fieldname": "db_name",
            "label": _("Database"),
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "fieldname": "email_count",
            "label": _("Email Accounts"),
            "fieldtype": "Int",
            "width": 120,
        },
        {
            "fieldname": "creation",
            "label": _("Created On"),
            "fieldtype": "Date",
            "width": 120,
        },
    ]


def get_data(filters):
    """
    Get website status using database-agnostic Frappe ORM queries.
    Tenant/session.user context is preserved.
    """
    db_filters = {}

    if filters.get("domain"):
        db_filters["name"] = ["like", f"%{filters.get('domain')}%"]

    if filters.get("status"):
        db_filters["status"] = filters.get("status")

    if filters.get("site_type"):
        db_filters["site_type"] = filters.get("site_type")

    if filters.get("ssl_status"):
        db_filters["ssl_status"] = filters.get("ssl_status")

    if filters.get("from_date") or filters.get("to_date"):
        creation_filter = []
        if filters.get("from_date"):
            creation_filter.append([">=", filters.get("from_date")])
        if filters.get("to_date"):
            creation_filter.append(["<=", filters.get("to_date")])
        db_filters["creation"] = creation_filter

    websites = frappe.get_all(
        "Hosted Website",
        filters=db_filters,
        fields=[
            "name as domain",
            "status",
            "site_type",
            "cms_type",
            "php_version",
            "ssl_status",
            "db_name",
            "creation",
        ],
        order_by="creation desc",
    )

    # Get email counts using ORM group by parent
    email_counts = frappe.get_all(
        "Hosted Email Account",
        fields=["parent", "count(name) as email_count"],
        group_by="parent",
    )
    email_map = {e.parent: e.email_count for e in email_counts if e.parent}

    for w in websites:
        w["email_count"] = email_map.get(w.domain, 0)

    return websites


def get_chart_data(data):
    """Generate chart showing website status distribution"""
    status_count = {}
    ssl_count = {"Active": 0, "Inactive": 0}

    for row in data:
        # Status distribution
        status = row.get("status", "Unknown")
        status_count[status] = status_count.get(status, 0) + 1

        # SSL distribution
        if row.get("ssl_status") == "Active":
            ssl_count["Active"] += 1
        else:
            ssl_count["Inactive"] += 1

    return {
        "data": {
            "labels": list(status_count.keys()),
            "datasets": [
                {"name": "Website Status", "values": list(status_count.values())}
            ],
        },
        "type": "donut",
        "height": 250,
        "colors": ["#10B981", "#F59E0B", "#EF4444", "#6B7280"],
    }
