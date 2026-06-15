# API Reference: hetzner

Source file: `rpanel/hosting/vps/hetzner.py`

## Classes

### class `HetznerVPSProvider`
Concrete VPS Provider implementation for Hetzner Cloud Services.
Utilizes direct REST API queries to https://api.hetzner.cloud/v1/

#### Documented Internal Methods
##### `create_vps(self, plan_code, site_name, **kwargs)`
Provisions a brand new Hetzner Cloud server instance dynamically.

##### `rebuild_vps(self, vps_id, image_name, ssh_keys, **kwargs)`
Rebuilds the Hetzner server utilizing a designated OS image.

##### `get_vps_status(self, vps_id)`
Retrieves runtime status metrics and metadata.

##### `reboot_vps(self, vps_id, hard=False)`
Triggers reboot action.

##### `terminate_vps(self, vps_id, **kwargs)`
Permanently deletes the server instance to stop billing.
