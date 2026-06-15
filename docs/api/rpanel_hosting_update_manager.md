# API Reference: update_manager

Source file: `rpanel/hosting/update_manager.py`

## Whitelisted API Endpoints

### `def update_ecosystem(immediate=False)`
Triggers a pull and restart of the Docker ecosystem.
If immediate=True, it runs now (used by CI).
If False, it marks an update as 'Authorized' for the next maintenance window.
