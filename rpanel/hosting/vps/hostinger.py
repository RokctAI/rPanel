# Copyright (c) 2026 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt

import requests
import frappe
from rpanel.hosting.vps.provider import VPSProvider

class HostingerVPSProvider(VPSProvider):
	"""
	Concrete VPS Provider implementation for Hostinger API Services.
	Utilizes direct REST API queries to Hostinger Developer API.
	"""

	def __init__(self, **kwargs):
		self.token = kwargs.get("api_token") or frappe.conf.get("hostinger_api_token")
		self.api_url = "https://api.hostinger.com/v1" # Standard endpoint or developers.hostinger.com gateway fallback
		self.headers = {
			"Authorization": f"Bearer {self.token}",
			"Content-Type": "application/json",
			"Accept": "application/json"
		}

	def create_vps(self, plan_code: str, site_name: str, **kwargs) -> dict:
		"""
		Orders/purchases a brand new Hostinger KVM VPS instance dynamically.
		"""
		if not self.token:
			return {"status": "failed", "error": "Hostinger API Token is missing."}

		try:
			# Plan mapping: map 'vps-1' to Hostinger's 8GB RAM plan 'kvm-4' or specific plan code
			plan = "kvm-4" if plan_code in ["vps-1", "vps-comfort-8"] else plan_code
			
			payload = {
				"name": site_name.replace(".", "-"),
				"plan": plan,
				"operating_system": kwargs.get("image", "debian-12-docker"),
				"location": kwargs.get("location", "us-east")
			}

			# Post purchase request to Hostinger endpoint
			response = requests.post(f"{self.api_url}/virtual-machines", json=payload, headers=self.headers, timeout=30)
			res_data = response.json()

			if response.status_code in [200, 201]:
				vm = res_data.get("virtual_machine", {})
				vps_id = vm.get("id") or res_data.get("id")
				
				# Auto-trigger setup if required by API specification
				if vps_id:
					requests.post(f"{self.api_url}/virtual-machines/{vps_id}/setup", json={}, headers=self.headers, timeout=30)
				
				frappe.log(f"SUCCESS: Hostinger KVM VPS created for {site_name} (ID: {vps_id})")
				return {
					"status": "success",
					"order_id": vps_id,
					"vps_id": str(vps_id),
					"ip": vm.get("ip_address") or vm.get("ip")
				}
			else:
				error_msg = res_data.get("message") or res_data.get("error", "Unknown error")
				return {"status": "failed", "error": f"Hostinger API Error: {error_msg}"}

		except Exception as e:
			frappe.log_error(f"Hostinger VPS Creation Failed for {site_name}: {e}", "VPS Orchestrator Error")
			return {"status": "failed", "error": str(e)}

	def rebuild_vps(self, vps_id: str, image_name: str, ssh_keys: list, **kwargs) -> bool:
		"""
		Re-installs chosen template on Hostinger virtual machine.
		"""
		if not self.token:
			return False

		try:
			payload = {"operating_system": image_name}
			response = requests.post(f"{self.api_url}/virtual-machines/{vps_id}/rebuild", json=payload, headers=self.headers, timeout=30)
			return response.status_code in [200, 202]
		except Exception as e:
			frappe.log_error(f"Hostinger Rebuild Failed for {vps_id}: {e}", "VPS Orchestrator Error")
			return False

	def get_vps_status(self, vps_id: str) -> dict:
		"""
		Retrieves runtime state, resources, and IP mapping.
		"""
		if not self.token:
			return {"vps_id": vps_id, "state": "unknown", "error": "Missing token"}

		try:
			response = requests.get(f"{self.api_url}/virtual-machines/{vps_id}", headers=self.headers, timeout=20)
			if response.status_code == 200:
				vm = response.json().get("virtual_machine", {})
				return {
					"vps_id": vps_id,
					"state": "running" if vm.get("status") == "running" else "stopped",
					"ip": vm.get("ip_address"),
					"memory": vm.get("ram", 0), # RAM in MB
					"vcpus": vm.get("cpu_cores", 0),
					"raw_info": vm
				}
			return {"vps_id": vps_id, "state": "unknown", "error": response.text}
		except Exception as e:
			frappe.log_error(f"Hostinger Status Query Failed for {vps_id}: {e}", "VPS Orchestrator Error")
			return {"vps_id": vps_id, "state": "unknown", "error": str(e)}

	def reboot_vps(self, vps_id: str, hard: bool = False) -> bool:
		"""
		Triggers reboot/restart action on Hostinger.
		"""
		if not self.token:
			return False

		try:
			action = "restart" if not hard else "reset"
			response = requests.post(f"{self.api_url}/virtual-machines/{vps_id}/{action}", headers=self.headers, timeout=30)
			return response.status_code in [200, 202]
		except Exception as e:
			frappe.log_error(f"Hostinger Reboot Failed for {vps_id}: {e}", "VPS Orchestrator Error")
			return False

	def terminate_vps(self, vps_id: str, **kwargs) -> bool:
		"""
		Permanently terminates and deletes the Hostinger VM.
		"""
		if not self.token:
			return False

		try:
			response = requests.delete(f"{self.api_url}/virtual-machines/{vps_id}", headers=self.headers, timeout=30)
			return response.status_code in [200, 202, 204]
		except Exception as e:
			frappe.log_error(f"Hostinger Termination Failed for {vps_id}: {e}", "VPS Orchestrator Error")
			return False
