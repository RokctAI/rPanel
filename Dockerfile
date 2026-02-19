# Start clean with Python 3.14 (User requested)
FROM python:3.14-slim

# 1. System Dependencies (Frappe + MariaDB + PDF)
RUN apt-get update && apt-get install -y \
    git mariadb-client postgresql-client gettext-base wget libssl-dev \
    fonts-cantarell xvfb libfontconfig wkhtmltopdf \
    python3-dev python3-setuptools python3-pip python3-distutils build-essential \
    cron curl vim nodejs npm redis-server software-properties-common \
    && rm -rf /var/lib/apt/lists/*

RUN npm install -g yarn
RUN useradd -ms /bin/bash frappe

# 2. Bench Setup
USER frappe
WORKDIR /home/frappe
RUN pip3 install frappe-bench
RUN bench init --skip-assets --skip-redis-config_generation --python python3 frappe-bench

WORKDIR /home/frappe/frappe-bench

# 3. INJECT CI ARTIFACTS
# The CI will unzip the tested 'apps' folder here
COPY --chown=frappe:frappe apps ./apps

# 4. Install All Apps
# We iterate through the copied apps and install them
RUN for app in $(ls apps); do \
        bench pip install -e apps/$app; \
    done

# 5. Build Assets (JS/CSS)
RUN bench build

CMD ["bench", "start"]
