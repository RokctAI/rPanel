# Copyright (c) 2026 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt

import frappe
from rpanel.hosting.vps.ovh import OVHVPSProvider

def get_vps_provider(provider_type: str = None, **kwargs) -> object:
	"""
	Factory method to dynamically retrieve the correct VPS provider instance.
	Defaults to 'ovh' if none is configured.
	
	Usage:
		provider = get_vps_provider()
		status = provider.get_vps_status("vps-xxxx.ovh.net")
	"""
	provider_type = provider_type or frappe.conf.get("default_vps_provider") or "ovh"
	provider_type = provider_type.lower().strip()

	if provider_type == "ovh":
		return OVHVPSProvider(**kwargs)
	else:
		raise ValueError(f"Unsupported VPS provider type: '{provider_type}'")
