# API Reference: git_manager

Source file: `rpanel/hosting/git_manager.py`

## Whitelisted API Endpoints

### `def clone_repository(website_name, repo_url, branch='main', deploy_key=None)`
Clone a Git repository to website directory

### `def pull_latest(website_name)`
Pull latest changes from Git repository

### `def switch_branch(website_name, branch)`
Switch to a different Git branch

### `def get_deployment_history(website_name, limit=10)`
Get deployment history from Git log

### `def rollback_deployment(website_name, commit_hash)`
Rollback to a specific commit

### `def setup_webhook(website_name)`
Generate webhook URL and secret for auto-deployment
