# API Reference: backup_encryption

Source file: `rpanel/hosting/backup_encryption.py`

## Module Description
Backup Encryption Manager

Handles GPG encryption/decryption of backups before uploading to cloud storage.

## Classes

### class `BackupEncryptionManager`
Manages GPG encryption for backups

#### Documented Internal Methods
##### `generate_encryption_key(self, email='backup@rpanel.local', name='RPanel Backup')`
Generate a new GPG key pair for backup encryption

Args:
    email: Email for the key
    name: Name for the key

Returns:
    dict: Key information including fingerprint

## Whitelisted API Endpoints

### `def generate_encryption_key()`
Generate a new encryption key (whitelisted for UI)

### `def download_public_key()`
Download public key (whitelisted for UI)

### `def download_private_key()`
Download private key (whitelisted for UI) - KEEP SECURE!

## Documented Module Functions

### `def encrypt_backup(backup_file_path)`
Encrypt a backup file

Args:
    backup_file_path: Path to backup file

Returns:
    str: Path to encrypted file

### `def decrypt_backup(encrypted_file_path)`
Decrypt an encrypted backup file

Args:
    encrypted_file_path: Path to encrypted file

Returns:
    str: Path to decrypted file
