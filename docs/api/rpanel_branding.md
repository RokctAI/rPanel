# API Reference: branding

Source file: `rpanel/branding.py`

## Documented Module Functions

### `def get_brand_html()`
Returns the brand HTML for the navbar.
If ROKCT is installed, returns None (lets ROKCT handle it).
Otherwise, returns RPanel branding.

### `def get_client_branding(bootinfo)`
Get branding for client portal
