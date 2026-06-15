# API Reference: system_user_manager

Source file: `rpanel/hosting/system_user_manager.py`

## Module Description
System User Manager for rpanel

Manages Linux system users for website isolation with reference counting.
Ensures users are only deleted when no websites reference them.

## Classes

### class `SystemUserManager`
Manages system users for website isolation

#### Documented Internal Methods
##### `user_exists(self, username)`
Check if a Linux user exists

##### `create_user(self, username)`
Create a Linux system user without sudo privileges

Args:
    username: Username to create

Security:
    - No shell access (/bin/false)
    - No home directory or uses /var/www/{username}
    - Member of www-data group
    - NO sudo privileges

##### `delete_user(self, username)`
Delete a Linux system user

Args:
    username: Username to delete

WARNING: Only call this after verifying reference count is 0

##### `increment_user_reference(self, username, site_name)`
Increment reference count for a user

Args:
    username: System user name
    site_name: Website domain name

##### `decrement_user_reference(self, username, site_name)`
Decrement reference count for a user

Args:
    username: System user name
    site_name: Website domain name

##### `get_user_reference_count(self, username)`
Get number of sites referencing a user

Args:
    username: System user name

Returns:
    int: Number of sites using this user
