# API Reference: site_backup

Source file: `rpanel/hosting/doctype/site_backup/site_backup.py`

## Classes

### class `SiteBackup`

#### Documented Internal Methods
##### `before_save(self)`
Set default backup date if not set

##### `create_backup(self)`
Create backup based on backup type

##### `upload_to_cloud(self, backup_file)`
Upload backup to configured cloud storage

##### `restore_backup(self)`
Restore backup to website

## Whitelisted API Endpoints

### `def create_backup(website, backup_type='Full', upload_to_cloud=False, cloud_storage='None')`
Create a new backup

### `def restore_backup(backup_id)`
Restore a backup

### `def delete_backup(backup_id)`
Delete a backup file and record

## Documented Module Functions

### `def _safe_path(base, untrusted)`
Validate that resolved path stays within base directory (Layer 18 ZTNA).
