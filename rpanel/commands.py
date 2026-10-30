# Copyright (c) 2026, Rokct Intelligence (pty) Ltd.
# For license information, please see license.txt

# Bench commands are composed from hosting_sdk below.

# --- BEG OF DYNAMIC SDK COMMANDS ---
commands = globals().get("commands", [])
# --- Module: hosting ---
from rpanel.hosting.commands import update_ecosystem_command as _sdk_command_0

if _sdk_command_0 not in commands:
    commands.append(_sdk_command_0)
# --- END OF DYNAMIC SDK COMMANDS ---
