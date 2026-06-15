# API Reference: factory

Source file: `rpanel/hosting/vps/factory.py`

## Classes

### class `VPSPoolManager`
Composite VPS provider acting as a failover pool.
Cascades server creation requests down the list of active providers
(OVH -> Hetzner -> Hostinger) when stock/API constraints occur.

#### Documented Internal Methods
##### `create_vps(self, plan_code, site_name, **kwargs)`
Attempts to provision a VPS in sequence across the pool providers.

## Documented Module Functions

### `def get_vps_provider(provider_type=None, **kwargs)`
Factory method to dynamically retrieve the correct VPS provider instance.
If 'pool' or None is specified, returns the composite VPSPoolManager.

Usage:
        provider = get_vps_provider() # returns failover pool
        status = provider.get_vps_status("vps-xxxx.ovh.net")
