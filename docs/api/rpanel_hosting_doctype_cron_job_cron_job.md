# API Reference: cron_job

Source file: `rpanel/hosting/doctype/cron_job/cron_job.py`

## Classes

### class `CronJob`

#### Documented Internal Methods
##### `validate(self)`
Validate cron expression and calculate next run

##### `validate_cron_expression(self, expression)`
Validate if cron expression is valid

##### `execute(self)`
Execute the cron job

## Whitelisted API Endpoints

### `def execute_cron_job(job_name)`
Execute a cron job manually

### `def get_cron_templates()`
Get pre-built cron job templates

### `def validate_cron_expression(expression)`
Validate cron expression and return next 5 run times

## Documented Module Functions

### `def execute_scheduled_cron_jobs()`
Execute all enabled cron jobs that are due (called by scheduler)
