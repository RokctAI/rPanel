# API Reference: ovh

Source file: `rpanel/hosting/vps/ovh.py`

## Classes

### class `OVHVPSProvider`
Concrete VPS Provider implementation for OVH Cloud Services.
Utilizes the official 'ovh' Python SDK.

#### Documented Internal Methods
##### `create_vps(self, plan_code, site_name, **kwargs)`
Places a new order cart for a VPS comfort/basic plan and checks out automatically.

##### `rebuild_vps(self, vps_id, image_name, ssh_keys, **kwargs)`
Re-installs the VPS OS utilizing the chosen template and authorized SSH keys.

##### `get_vps_status(self, vps_id)`
Retrieves active power states, DNS names, and system details.

##### `reboot_vps(self, vps_id, hard=False)`
Triggers a reboot instruction on the virtual instance.

##### `terminate_vps(self, vps_id, **kwargs)`
Permanently terminates the VPS service on OVH.
