# API Reference: hostinger

Source file: `rpanel/hosting/vps/hostinger.py`

## Classes

### class `HostingerVPSProvider`
Concrete VPS Provider implementation for Hostinger API Services.
Utilizes direct REST API queries to Hostinger Developer API.

#### Documented Internal Methods
##### `create_vps(self, plan_code, site_name, **kwargs)`
Provisions a Hostinger VPS. First scans the active VPS list for any stopped/sleeping 
pre-paid instances (names starting with 'sleep-', 'prepaid-', or 'unassigned-').
If a stopped instance is found, it reuses it by renaming and starting it, 
saving billing costs. Otherwise, purchases a brand new one.

##### `rebuild_vps(self, vps_id, image_name, ssh_keys, **kwargs)`
Re-installs chosen template on Hostinger virtual machine.

##### `get_vps_status(self, vps_id)`
Retrieves runtime state, resources, and IP mapping.

##### `reboot_vps(self, vps_id, hard=False)`
Triggers reboot/restart action on Hostinger.

##### `terminate_vps(self, vps_id, **kwargs)`
Recycles the Hostinger VPS instead of deleting it. Put it to sleep (stop it)
and rename it back to 'sleep-{vps_id}' so it returns to the prepaid sleep pool
for future tenants, preserving active 12-month commitments.
