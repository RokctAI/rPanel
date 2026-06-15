# API Reference: provider

Source file: `rpanel/hosting/vps/provider.py`

## Classes

### class `VPSProvider`
Abstract Base Class defining the contract for all VPS Cloud Providers
(e.g., OVH, Hetzner, DigitalOcean, AWS) managed natively by rpanel.

#### Documented Internal Methods
##### `create_vps(self, plan_code, site_name, **kwargs)`
Orders and provisions a brand new VPS instance dynamically.

Returns:
        dict: Standardized metadata including status, order_id, invoice_id, and provision URL.

##### `rebuild_vps(self, vps_id, image_name, ssh_keys, **kwargs)`
Re-installs/rebuilds a clean OS image on an existing VPS instance.

Returns:
        bool: True if execution succeeded, False otherwise.

##### `get_vps_status(self, vps_id)`
Retrieves runtime state, resource specifications, and billing info.

Returns:
        dict: Standardized status dictionary (vps_id, state, ip, memory, vcpus, raw_info).

##### `reboot_vps(self, vps_id, hard=False)`
Triggers a reboot action on the VPS instance.

Returns:
        bool: True if successful, False otherwise.

##### `terminate_vps(self, vps_id, **kwargs)`
Permanently cancels and terminates the VPS instance subscription.

Returns:
        bool: True if successful, False otherwise.
