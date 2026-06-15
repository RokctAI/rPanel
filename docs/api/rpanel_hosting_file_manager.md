# API Reference: file_manager

Source file: `rpanel/hosting/file_manager.py`

## Whitelisted API Endpoints

### `def get_file_list(website_name, path='')`
Get list of files and directories for a website

### `def download_file(website_name, file_path)`
Download a file from the website directory

### `def upload_file(website_name, path, filename, filedata)`
Upload a file to the website directory

### `def delete_file(website_name, file_path)`
Delete a file or directory

### `def create_directory(website_name, path, dirname)`
Create a new directory

### `def read_file(website_name, file_path)`
Read file content (for text files)

### `def save_file(website_name, file_path, content)`
Save file content (for text files)
