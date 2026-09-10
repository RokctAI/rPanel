# Copyright (c) 2025, Rokct Holdings and contributors
# For license information, please see license.txt

"""
Nginx Configuration Manager for RPanel

This module manages Nginx configurations for hosted websites while being aware of:
- Frappe bench config (frappe-bench-frappe)

It ensures RPanel never conflicts with these existing configurations.
"""

import os
import re
import subprocess
import frappe
from pathlib import Path
from rpanel.hosting.service_intelligence import ServiceIntelligence
from rpanel.hosting.utils import run_certbot

# Protected config files that RPanel should NEVER modify
PROTECTED_CONFIGS = [
    # Frappe bench (created by bench setup production)
    "frappe-bench-frappe",
    "default",  # System default
]

# RPanel config file prefix
RPANEL_PREFIX = "rpanel-"

# Nginx paths
NGINX_AVAILABLE = "/etc/nginx/sites-available"
NGINX_ENABLED = "/etc/nginx/sites-enabled"
NGINX_CONF_D = "/etc/nginx/conf.d"

# Webroot served for ACME HTTP-01 challenges by reverse-proxy vhosts and used
# by ``issue_certificate`` (certbot --webroot). Must be readable by nginx.
ACME_WEBROOT = "/var/www/letsencrypt"

# Where certbot places issued certificates
LETSENCRYPT_LIVE = "/etc/letsencrypt/live"

# Upload limit for proxied Frappe sites (file uploads, backups restore)
PROXY_CLIENT_MAX_BODY_SIZE = "50m"

# Hostname: lowercase labels, at least one dot, no leading/trailing hyphen
_DOMAIN_RE = re.compile(
    r"^(?=.{1,253}$)(?!-)[a-z0-9-]{1,63}(?<!-)(\.(?!-)[a-z0-9-]{1,63}(?<!-))+$"
)

# Upstream: http(s)://host[:port] - a docker service name, hostname or IP
_UPSTREAM_RE = re.compile(
    r"^https?://[a-z0-9]([a-z0-9._-]*[a-z0-9])?(:[0-9]{1,5})?$", re.IGNORECASE
)


def _validate_domain(domain):
    """Normalise ``domain`` and refuse anything that is not a plain hostname.

    The value is interpolated into an nginx config, so this is the guard
    against config injection (spaces, braces, semicolons, wildcards).
    """
    normalised = str(domain or "").strip().lower().rstrip(".")
    if not _DOMAIN_RE.match(normalised):
        raise ValueError(f"Invalid domain for nginx vhost: {domain!r}")
    return normalised


def _validate_upstream(upstream):
    """Refuse upstreams that are not ``http(s)://host[:port]``."""
    normalised = str(upstream or "").strip().rstrip("/")
    if not _UPSTREAM_RE.match(normalised):
        raise ValueError(f"Invalid upstream for nginx vhost: {upstream!r}")
    return normalised


def _privileged(cmd):
    """Prefix ``cmd`` with sudo unless we already run as root.

    On the hub host the bench user relies on sudo; inside the hub container
    nginx and the bench run as root and sudo is typically not installed.
    """
    if os.geteuid() == 0:
        return list(cmd)
    return ["sudo", *cmd]


def _write_text(path, content):
    """Write ``content`` to ``path`` atomically, falling back to ``sudo tee``."""
    path = Path(path)
    try:
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_text(content)
        os.chmod(tmp, 0o644)
        os.replace(tmp, path)
    except PermissionError:
        subprocess.run(
            ["sudo", "tee", str(path)],
            input=content,
            text=True,
            check=True,
            stdout=subprocess.DEVNULL,
        )
        subprocess.run(["sudo", "chmod", "644", str(path)], check=True)


def _read_text(path):
    """Return the content of ``path`` or ``None`` when it does not exist."""
    try:
        return Path(path).read_text()
    except (FileNotFoundError, PermissionError):
        return None


def _remove_path(path):
    """Remove a file or symlink if present. Returns True when something went."""
    path = Path(path)
    if not (path.is_symlink() or path.exists()):
        return False
    try:
        path.unlink()
    except PermissionError:
        subprocess.run(["sudo", "rm", "-f", str(path)], check=True)
    return True


def _symlink(source, target):
    """(Re)create ``target`` -> ``source``, falling back to sudo."""
    source, target = Path(source), Path(target)
    try:
        if target.is_symlink() or target.exists():
            target.unlink()
        os.symlink(source, target)
    except PermissionError:
        subprocess.run(["sudo", "rm", "-f", str(target)], check=True)
        subprocess.run(["sudo", "ln", "-s", str(source), str(target)], check=True)


def _ensure_dir(path):
    """``mkdir -p`` with a sudo fallback for root-owned parents."""
    try:
        os.makedirs(path, exist_ok=True)
    except PermissionError:
        subprocess.run(["sudo", "mkdir", "-p", str(path)], check=True)


def test_nginx_config():
    """Run ``nginx -t`` and raise ``RuntimeError`` when the config is invalid."""
    result = subprocess.run(
        _privileged(["nginx", "-t"]), capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Nginx configuration test failed: {(result.stderr or '').strip()}"
        )


def reload_nginx():
    """Reload nginx, preferring systemd and falling back to ``nginx -s reload``.

    On the hub host nginx is a systemd unit. Inside the hub container it runs
    as ``nginx -g 'daemon off;'`` with no systemd, where ``systemctl`` is either
    missing or refuses to operate; there the master process is signalled
    directly. Returns the command that succeeded; raises ``RuntimeError`` when
    every attempt failed.
    """
    attempts = [
        _privileged(["systemctl", "reload", "nginx"]),
        _privileged(["nginx", "-s", "reload"]),
    ]
    errors = []
    for cmd in attempts:
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            return cmd
        except subprocess.CalledProcessError as exc:
            errors.append(f"{' '.join(cmd)}: {(exc.stderr or '').strip()}")
        except OSError as exc:  # sudo/systemctl/nginx binary missing
            errors.append(f"{' '.join(cmd)}: {exc}")
    raise RuntimeError("Failed to reload nginx: " + "; ".join(errors))


class NginxManager:
    """Manages Nginx configurations for RPanel websites"""

    def __init__(self):
        self.available_path = Path(NGINX_AVAILABLE)
        self.enabled_path = Path(NGINX_ENABLED)
        self.conf_d_path = Path(NGINX_CONF_D)
        self.letsencrypt_live = Path(LETSENCRYPT_LIVE)
        self.acme_webroot = ACME_WEBROOT

    def is_protected_config(self, filename):
        """Check if a config file is protected (managed by Frappe/ROKCT)"""
        return filename in PROTECTED_CONFIGS

    def get_rpanel_config_name(self, domain):
        """Get the config filename for a domain"""
        # Sanitize domain name for filename
        safe_domain = domain.replace(".", "_").replace(":", "_")
        return f"{RPANEL_PREFIX}{safe_domain}.conf"

    def create_website_config(self, domain, site_path, php_version=None):
        """
        Create Nginx config for a hosted website

        Args:
            domain: Website domain name
            site_path: Absolute path to website root
            php_version: PHP version to use (discovered if None)
        """
        ver = php_version or ServiceIntelligence.get_default_php_version()  # noqa: F841
        config_name = self.get_rpanel_config_name(domain)
        config_path = self.available_path / config_name

        # Check if this would conflict with protected configs
        if self.is_protected_config(config_name):
            frappe.throw(
                f"Cannot create config '{config_name}' - this filename is protected"
            )

        # Generate Nginx config
        config_content = self._generate_website_config(domain, site_path, php_version)

        # Write config file
        try:
            # Use sudo tee to write to protected directory
            subprocess.run(
                ["sudo", "tee", str(config_path)],
                input=config_content,
                text=True,
                check=True,
                stdout=subprocess.DEVNULL,
            )

            # Set proper permissions
            subprocess.run(["sudo", "chmod", "644", str(config_path)], check=True)

            # Enable the site
            self.enable_site(config_name)

            # Test and reload Nginx
            self.test_and_reload()

            frappe.logger().info(f"Nginx configuration created for {domain}")

        except Exception as e:
            frappe.log_error(f"Failed to create Nginx config for {domain}: {str(e)}")
            frappe.throw(f"Failed to create Nginx configuration: {str(e)}")

    def _generate_website_config(self, domain, site_path, php_version):
        """Generate Nginx configuration content for a website"""

        config = f"""# Managed by RPanel - Website: {domain}
# DO NOT EDIT MANUALLY - Changes will be overwritten by RPanel

server {{
    listen 80;
    server_name {domain};

    root {site_path};
    index index.php index.html index.htm;

    # Include RPanel rate limiting (if exists)
    include /etc/nginx/conf.d/rpanel-rate-limits.conf;

    # Logging
    access_log /var/log/nginx/{domain}-access.log;
    error_log /var/log/nginx/{domain}-error.log;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Deny access to hidden files
    location ~ /\\. {{
        deny all;
    }}

    # PHP handling
    location ~ \\.php$ {{
        include snippets/fastcgi-php.conf;
        fastcgi_pass unix:{ServiceIntelligence.get_php_fpm_socket(php_version)};
        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
        include fastcgi_params;
    }}

    # WordPress permalinks
    location / {{
        try_files $uri $uri/ /index.php?$args;
    }}

    # Deny access to sensitive files
    location ~* \\.(htaccess|htpasswd|ini|log|sh|sql|conf)$ {{
        deny all;
    }}

    # Cache static assets
    location ~* \\.(jpg|jpeg|png|gif|ico|css|js|svg|woff|woff2|ttf|eot)$ {{
        expires 30d;
        add_header Cache-Control "public, immutable";
    }}
}}
"""
        return config

    # ------------------------------------------------------------------
    # Reverse-proxy vhosts (tenant backend domains)
    # ------------------------------------------------------------------

    def _generate_proxy_location(self, domain, upstream, websocket):
        """``location /`` block proxying to a Frappe tenant upstream."""
        lines = [
            "    location / {",
            f"        proxy_pass {upstream};",
            "        proxy_http_version 1.1;",
            "        proxy_set_header Host $host;",
            "        proxy_set_header X-Real-IP $remote_addr;",
            "        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;",
            "        proxy_set_header X-Forwarded-Proto $scheme;",
            "        proxy_set_header X-Forwarded-Host $host;",
            "        proxy_set_header X-Forwarded-Port $server_port;",
            f"        proxy_set_header X-Frappe-Site-Name {domain};",
        ]
        if websocket:
            # $http_connection forwards the client's own Connection header, so
            # socket.io upgrades work without an http-level ``map`` block
            # (which a sites-enabled server block cannot declare).
            lines += [
                "        proxy_set_header Upgrade $http_upgrade;",
                "        proxy_set_header Connection $http_connection;",
            ]
        lines += [
            "        proxy_connect_timeout 60s;",
            "        proxy_send_timeout 300s;",
            "        proxy_read_timeout 300s;",
            "        proxy_buffer_size 128k;",
            "        proxy_buffers 4 256k;",
            "        proxy_busy_buffers_size 256k;",
            "        proxy_redirect off;",
            "    }",
        ]
        return "\n".join(lines)

    def _generate_reverse_proxy_config(self, domain, upstream, websocket, ssl):
        """Generate the nginx server block(s) for a reverse-proxied domain.

        Port 80 always serves the ACME HTTP-01 challenge from the shared
        webroot. Before a certificate exists it proxies to the upstream; once
        one exists it redirects to https and a 443 block carries the proxy.
        """
        proxy_location = self._generate_proxy_location(domain, upstream, websocket)
        acme_location = (
            "    # ACME HTTP-01 challenge (certbot --webroot)\n"
            "    location ^~ /.well-known/acme-challenge/ {\n"
            f"        root {self.acme_webroot};\n"
            '        default_type "text/plain";\n'
            "        try_files $uri =404;\n"
            "    }"
        )
        cert_dir = self.letsencrypt_live / domain
        header = (
            f"# Managed by RPanel - Reverse proxy: {domain} -> {upstream}\n"
            "# DO NOT EDIT MANUALLY - Changes will be overwritten by RPanel\n"
        )
        common = (
            f"    server_name {domain};\n"
            "\n"
            f"    access_log /var/log/nginx/{domain}-access.log;\n"
            f"    error_log /var/log/nginx/{domain}-error.log;\n"
            "\n"
            f"    client_max_body_size {PROXY_CLIENT_MAX_BODY_SIZE};\n"
        )
        http_root = (
            "    location / {\n        return 301 https://$host$request_uri;\n    }"
            if ssl
            else proxy_location
        )
        config = (
            f"{header}\n"
            "server {\n"
            "    listen 80;\n"
            f"{common}\n"
            f"{acme_location}\n"
            "\n"
            f"{http_root}\n"
            "}\n"
        )
        if ssl:
            config += (
                "\n"
                "server {\n"
                "    listen 443 ssl;\n"
                f"{common}\n"
                f"    ssl_certificate {cert_dir / 'fullchain.pem'};\n"
                f"    ssl_certificate_key {cert_dir / 'privkey.pem'};\n"
                "    ssl_protocols TLSv1.2 TLSv1.3;\n"
                "    ssl_prefer_server_ciphers off;\n"
                "    ssl_session_timeout 1d;\n"
                "    ssl_session_cache shared:rpanel_proxy_ssl:10m;\n"
                "\n"
                f"{proxy_location}\n"
                "}\n"
            )
        return config

    def certificate_exists(self, domain):
        """True when certbot has a live certificate for ``domain``.

        ``/etc/letsencrypt/live`` is root-only, so a non-root bench user
        checks through ``sudo test -e``.
        """
        fullchain = self.letsencrypt_live / domain / "fullchain.pem"
        try:
            if fullchain.exists():
                return True
        except OSError:
            pass
        if os.geteuid() == 0:
            return False
        result = subprocess.run(
            ["sudo", "test", "-e", str(fullchain)], capture_output=True
        )
        return result.returncode == 0

    def create_reverse_proxy_vhost(self, domain, upstream, *, websocket=True, ssl=None):
        """Create or rewrite the reverse-proxy vhost for ``domain``.

        Args:
            domain: Public hostname (e.g. ``platform.example.com``).
            upstream: ``http(s)://host[:port]`` of the tenant, e.g.
                ``http://<site>-app:8000``.
            websocket: Forward Upgrade/Connection headers (socket.io).
            ssl: Force the https block on/off; ``None`` enables it when a
                certbot certificate for ``domain`` already exists.

        The config is written to sites-available, enabled in sites-enabled and
        validated with ``nginx -t``. On a failed test the previous config is
        restored (or the new one removed) so nginx is never reloaded with a
        broken vhost. Idempotent: rewrites in place. Returns the config path.
        """
        domain = _validate_domain(domain)
        upstream = _validate_upstream(upstream)
        if ssl is None:
            ssl = self.certificate_exists(domain)

        config_name = self.get_rpanel_config_name(domain)
        if self.is_protected_config(config_name):
            raise ValueError(f"Cannot create config '{config_name}' - protected")
        config_path = self.available_path / config_name
        enabled_path = self.enabled_path / config_name
        content = self._generate_reverse_proxy_config(
            domain, upstream, websocket=websocket, ssl=ssl
        )

        previous = _read_text(config_path)
        _write_text(config_path, content)
        _symlink(config_path, enabled_path)
        try:
            test_nginx_config()
        except RuntimeError:
            if previous is None:
                _remove_path(enabled_path)
                _remove_path(config_path)
            else:
                _write_text(config_path, previous)
            raise
        reload_nginx()
        frappe.logger().info(
            f"Nginx reverse-proxy vhost written for {domain} -> {upstream} (ssl={ssl})"
        )
        return str(config_path)

    def remove_vhost(self, domain):
        """Remove the vhost for ``domain`` and reload nginx.

        Idempotent: returns False (and does not reload) when nothing existed.
        """
        domain = _validate_domain(domain)
        config_name = self.get_rpanel_config_name(domain)
        if self.is_protected_config(config_name):
            raise ValueError(f"Cannot delete protected config: {config_name}")
        removed_link = _remove_path(self.enabled_path / config_name)
        removed_conf = _remove_path(self.available_path / config_name)
        if not (removed_link or removed_conf):
            return False
        reload_nginx()
        frappe.logger().info(f"Nginx vhost removed for {domain}")
        return True

    def enable_site(self, config_name):
        """Enable a site by creating symlink in sites-enabled"""
        source = self.available_path / config_name
        target = self.enabled_path / config_name

        if not source.exists():
            # Check existence via sudo/shell just in case, but python check might fail if dir not readable
            # Proceeding assuming path is correct.
            pass

        # Remove existing symlink if it exists
        if target.exists() or target.is_symlink():
            subprocess.run(["sudo", "rm", "-f", str(target)], check=True)

        # Create symlink
        subprocess.run(["sudo", "ln", "-s", str(source), str(target)], check=True)

    def disable_site(self, config_name):
        """Disable a site by removing symlink from sites-enabled"""
        target = self.enabled_path / config_name

        subprocess.run(["sudo", "rm", "-f", str(target)], check=True)

    def delete_site_config(self, domain):
        """Delete Nginx config for a domain"""
        config_name = self.get_rpanel_config_name(domain)

        # Check if protected
        if self.is_protected_config(config_name):
            frappe.throw(f"Cannot delete protected config: {config_name}")

        # Disable first
        self.disable_site(config_name)

        # Delete config file
        config_path = self.available_path / config_name
        subprocess.run(["sudo", "rm", "-f", str(config_path)], check=True)

        # Reload Nginx
        self.test_and_reload()

    def test_and_reload(self):
        """Test Nginx config and reload if valid"""
        try:
            # Test configuration
            result = subprocess.run(
                ["sudo", "nginx", "-t"], capture_output=True, text=True
            )

            if result.returncode != 0:
                error_msg = result.stderr
                frappe.log_error(f"Nginx config test failed: {error_msg}")
                frappe.throw(f"Nginx configuration error: {error_msg}")

            # Reload Nginx (systemd on the host, nginx -s reload in a container)
            reload_nginx()

        except (subprocess.CalledProcessError, RuntimeError) as e:
            frappe.log_error(f"Failed to reload Nginx: {str(e)}")
            frappe.throw(f"Failed to reload Nginx: {str(e)}")

    def setup_rate_limiting(self):
        """
        Setup global rate limiting for RPanel websites
        Only runs once during installation
        """
        rate_limit_config = self.conf_d_path / "rpanel-rate-limits.conf"

        if rate_limit_config.exists():
            return  # Already configured

        config_content = """# RPanel Global Rate Limiting
# Prevents DDoS attacks on hosted websites

# Zone definitions
limit_req_zone $binary_remote_addr zone=rpanel_general:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=rpanel_login:10m rate=5r/m;

# Apply general rate limiting
limit_req zone=rpanel_general burst=20 nodelay;

# Stricter limits for login endpoints
# This is applied in individual site configs for WordPress, etc.
"""

        try:
            subprocess.run(
                ["sudo", "tee", str(rate_limit_config)],
                input=config_content,
                text=True,
                check=True,
                stdout=subprocess.DEVNULL,
            )

            subprocess.run(["sudo", "chmod", "644", str(rate_limit_config)], check=True)

            print("✓ RPanel rate limiting configured")

        except Exception as e:
            frappe.log_error(f"Failed to setup rate limiting: {str(e)}")

    def get_all_rpanel_sites(self):
        """Get list of all RPanel-managed sites"""
        sites = []

        for config_file in self.available_path.glob(f"{RPANEL_PREFIX}*.conf"):
            sites.append(config_file.name)

        return sites

    def check_conflicts(self):
        """
        Check for potential conflicts with Frappe/ROKCT configs
        Returns list of conflicts found
        """
        conflicts = []

        # Check if protected configs exist
        for protected in PROTECTED_CONFIGS:
            config_path = self.available_path / protected
            if config_path.exists():
                # Check if any RPanel config might conflict
                # (This is mainly for documentation/awareness)
                pass

        return conflicts


# Convenience functions for use in DocTypes


def create_nginx_config(domain, site_path, php_version=None):
    """Create Nginx config for a website"""
    manager = NginxManager()
    manager.create_website_config(domain, site_path, php_version)


def delete_nginx_config(domain):
    """Delete Nginx config for a website"""
    manager = NginxManager()
    manager.delete_site_config(domain)


def create_reverse_proxy_vhost(domain, upstream, *, websocket=True, ssl=None):
    """Write, enable, validate and reload the reverse-proxy vhost for ``domain``.

    Called in-process by control's backend-domain job. Returns the config
    path. See ``NginxManager.create_reverse_proxy_vhost``.
    """
    return NginxManager().create_reverse_proxy_vhost(
        domain, upstream, websocket=websocket, ssl=ssl
    )


def remove_vhost(domain):
    """Remove the vhost for ``domain`` (no error if absent) and reload nginx."""
    return NginxManager().remove_vhost(domain)


def issue_certificate(domain, *, include_www=False, email=None, webroot=None):
    """Issue a certbot webroot certificate for ``domain``.

    Unlike hosted websites, no ``www.`` SAN is requested unless
    ``include_www`` is true. The vhost created by
    ``create_reverse_proxy_vhost`` must already serve the ACME location for
    ``domain`` from ``webroot`` (default ``ACME_WEBROOT``). Returns the live
    certificate directory; raises ``RuntimeError`` when certbot fails.
    """
    domain = _validate_domain(domain)
    webroot = webroot or ACME_WEBROOT
    _ensure_dir(webroot)
    ok, message = run_certbot(domain, webroot, include_www=include_www, email=email)
    if not ok:
        raise RuntimeError(message)
    return str(Path(LETSENCRYPT_LIVE) / domain)


def setup_nginx_rate_limiting():
    """Setup global rate limiting (run during installation)"""
    manager = NginxManager()
    manager.setup_rate_limiting()


def _safe_path(base: str, untrusted: str) -> str:
    """Validate that resolved path stays within base directory (Layer 18 ZTNA)."""
    resolved = os.path.realpath(os.path.join(base, untrusted))
    base_real = os.path.realpath(base)
    if not resolved.startswith(base_real + os.sep) and resolved != base_real:
        raise ValueError(f"Path traversal blocked: {untrusted!r}")
    return resolved


def secure_website_permissions(site_path, owner="www-data"):
    """
    Set secure file permissions for a website

    Args:
        site_path: Absolute path to website root
        owner: User/group owner (default: www-data)
    """
    try:
        # Set directory permissions: 755 (rwxr-xr-x)
        subprocess.run(
            ["find", site_path, "-type", "d", "-exec", "chmod", "755", "{}", "+"],
            check=True,
        )

        # Set file permissions: 644 (rw-r--r--)
        subprocess.run(
            ["find", site_path, "-type", "f", "-exec", "chmod", "644", "{}", "+"],
            check=True,
        )

        # Set ownership
        subprocess.run(["chown", "-R", f"{owner}:{owner}", site_path], check=True)

        # Secure upload directories (775 for write access)
        upload_dirs = [
            os.path.join(site_path, "wp-content/uploads"),
            os.path.join(site_path, "uploads"),
        ]

        for upload_dir in upload_dirs:
            if os.path.exists(upload_dir):
                subprocess.run(["chmod", "-R", "775", upload_dir], check=True)

        # Secure config files (600 for sensitive files)
        config_files = [
            os.path.join(site_path, "wp-config.php"),
            os.path.join(site_path, ".htaccess"),
        ]

        for config_file in config_files:
            if os.path.exists(config_file):
                subprocess.run(["chmod", "600", config_file], check=True)

        frappe.logger().info(f"File permissions secured for {site_path}")

    except subprocess.CalledProcessError as e:
        frappe.log_error(f"Failed to secure permissions for {site_path}: {str(e)}")
        frappe.throw(f"Failed to secure file permissions: {str(e)}")
