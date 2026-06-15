# API Reference: setup

Source file: `integration_examples/setup.py`

## Module Description
RPanel Integration: Auto-Install Hook
=====================================

Use this code in your custom Frappe app to automatically install RPanel on your control site.

How to use:
1. Copy this function to your app (e.g., `yourapp/setup.py`).
2. Add a hook in `hooks.py`:
   `after_install = "yourapp.setup.check_and_install_rpanel"`
