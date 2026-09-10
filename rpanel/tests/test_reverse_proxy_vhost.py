"""Unit tests for reverse-proxy vhosts, certificates and nginx reload.

These run under ``bench run-tests`` and under plain pytest/unittest (no
bench, no site): ``frappe`` is stubbed when it is not importable, subprocess
is mocked and nginx directories live in a temporary directory.
"""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

try:
    import frappe  # noqa: F401
except ImportError:  # pragma: no cover - plain pytest without a bench
    sys.modules["frappe"] = MagicMock()

from rpanel.hosting import nginx_manager
from rpanel.hosting.nginx_manager import NginxManager, reload_nginx
from rpanel.hosting.utils import build_certbot_command, run_certbot

DOMAIN = "platform.supacharge.school"
UPSTREAM = "http://supacharge-app:8000"
SUDO_RELOAD = ["sudo", "systemctl", "reload", "nginx"]
SUDO_FALLBACK = ["sudo", "nginx", "-s", "reload"]


def _ok(*args, **kwargs):
    return MagicMock(returncode=0, stdout="", stderr="")


class ReverseProxyVhostTestCase(unittest.TestCase):
    """Base: manager pointed at a temp nginx tree, subprocess mocked."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.available = root / "sites-available"
        self.enabled = root / "sites-enabled"
        self.live = root / "letsencrypt" / "live"
        for d in (self.available, self.enabled, self.live):
            d.mkdir(parents=True)

        self.manager = NginxManager()
        self.manager.available_path = self.available
        self.manager.enabled_path = self.enabled
        self.manager.letsencrypt_live = self.live

        patcher = patch("rpanel.hosting.nginx_manager.subprocess.run", side_effect=_ok)
        self.mock_run = patcher.start()
        self.addCleanup(patcher.stop)

    def commands(self):
        return [list(call.args[0]) for call in self.mock_run.call_args_list]

    def config_path(self):
        return self.available / "rpanel-platform_supacharge_school.conf"


class TestTemplateRendering(ReverseProxyVhostTestCase):
    def test_http_only_vhost_proxies_and_serves_acme(self):
        path = self.manager.create_reverse_proxy_vhost(DOMAIN, UPSTREAM, ssl=False)

        self.assertEqual(path, str(self.config_path()))
        content = Path(path).read_text()
        self.assertIn(f"server_name {DOMAIN};", content)
        self.assertIn(f"proxy_pass {UPSTREAM};", content)
        self.assertIn("listen 80;", content)
        self.assertNotIn("listen 443 ssl;", content)
        self.assertNotIn("return 301 https://", content)
        self.assertIn("location ^~ /.well-known/acme-challenge/", content)
        self.assertIn(f"root {nginx_manager.ACME_WEBROOT};", content)
        self.assertIn("client_max_body_size 50m;", content)
        self.assertNotIn("www.", content)

    def test_forwarding_headers_present(self):
        path = self.manager.create_reverse_proxy_vhost(DOMAIN, UPSTREAM, ssl=False)
        content = Path(path).read_text()
        for header in (
            "proxy_set_header Host $host;",
            "proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;",
            "proxy_set_header X-Forwarded-Proto $scheme;",
            "proxy_set_header X-Forwarded-Host $host;",
            f"proxy_set_header X-Frappe-Site-Name {DOMAIN};",
            "proxy_set_header Upgrade $http_upgrade;",
            "proxy_set_header Connection $http_connection;",
            "proxy_http_version 1.1;",
            "proxy_read_timeout 300s;",
        ):
            self.assertIn(header, content)

    def test_websocket_headers_can_be_disabled(self):
        path = self.manager.create_reverse_proxy_vhost(
            DOMAIN, UPSTREAM, websocket=False, ssl=False
        )
        content = Path(path).read_text()
        self.assertNotIn("Upgrade", content)
        self.assertIn(f"proxy_pass {UPSTREAM};", content)

    def test_ssl_vhost_redirects_http_and_carries_cert_paths(self):
        path = self.manager.create_reverse_proxy_vhost(DOMAIN, UPSTREAM, ssl=True)
        content = Path(path).read_text()
        self.assertIn("listen 443 ssl;", content)
        self.assertIn("return 301 https://$host$request_uri;", content)
        self.assertIn(
            f"ssl_certificate {self.live / DOMAIN / 'fullchain.pem'};", content
        )
        self.assertIn(
            f"ssl_certificate_key {self.live / DOMAIN / 'privkey.pem'};", content
        )
        # ACME challenge stays reachable over http for renewals
        self.assertIn("location ^~ /.well-known/acme-challenge/", content)
        # exactly one proxy block (the https server) once ssl is on
        self.assertEqual(content.count(f"proxy_pass {UPSTREAM};"), 1)
        self.assertEqual(content.count("server {"), 2)

    def test_ssl_auto_detected_from_live_certificate(self):
        cert_dir = self.live / DOMAIN
        cert_dir.mkdir()
        (cert_dir / "fullchain.pem").write_text("cert")

        content = Path(
            self.manager.create_reverse_proxy_vhost(DOMAIN, UPSTREAM)
        ).read_text()
        self.assertIn("listen 443 ssl;", content)

    def test_ssl_auto_detect_without_certificate_is_http_only(self):
        with patch("rpanel.hosting.nginx_manager.os.geteuid", return_value=0):
            content = Path(
                self.manager.create_reverse_proxy_vhost(DOMAIN, UPSTREAM)
            ).read_text()
        self.assertNotIn("listen 443 ssl;", content)

    def test_domain_is_normalised(self):
        path = self.manager.create_reverse_proxy_vhost(
            " Platform.Supacharge.School. ", UPSTREAM, ssl=False
        )
        self.assertEqual(path, str(self.config_path()))
        self.assertIn(f"server_name {DOMAIN};", Path(path).read_text())

    def test_rejects_bad_domain_and_upstream(self):
        for bad in ("", "platform", "bad domain.com", "a;b.com", "x{.com", "-a.com"):
            with self.assertRaises(ValueError):
                self.manager.create_reverse_proxy_vhost(bad, UPSTREAM, ssl=False)
        for bad in (
            "",
            "supacharge-app:8000",
            "http://a b:80",
            "http://x;y",
            "ftp://x",
        ):
            with self.assertRaises(ValueError):
                self.manager.create_reverse_proxy_vhost(DOMAIN, bad, ssl=False)
        self.assertFalse(list(self.available.iterdir()))
        self.mock_run.assert_not_called()


class TestIdempotencyAndLifecycle(ReverseProxyVhostTestCase):
    def test_rewrite_in_place_is_idempotent(self):
        first = self.manager.create_reverse_proxy_vhost(DOMAIN, UPSTREAM, ssl=False)
        second = self.manager.create_reverse_proxy_vhost(DOMAIN, UPSTREAM, ssl=False)

        self.assertEqual(first, second)
        self.assertEqual(
            [p.name for p in self.available.iterdir()], [self.config_path().name]
        )
        link = self.enabled / self.config_path().name
        self.assertTrue(link.is_symlink())
        self.assertEqual(os.readlink(link), str(self.config_path()))
        self.assertFalse(list(self.available.glob("*.tmp")))

    def test_rewrite_updates_upstream(self):
        self.manager.create_reverse_proxy_vhost(DOMAIN, UPSTREAM, ssl=False)
        self.manager.create_reverse_proxy_vhost(
            DOMAIN, "http://other-app:8001", ssl=False
        )
        content = self.config_path().read_text()
        self.assertIn("proxy_pass http://other-app:8001;", content)
        self.assertNotIn(UPSTREAM, content)

    def test_validates_before_reload(self):
        with patch("rpanel.hosting.nginx_manager.os.geteuid", return_value=1000):
            self.manager.create_reverse_proxy_vhost(DOMAIN, UPSTREAM, ssl=False)
        cmds = self.commands()
        self.assertEqual(cmds[0], ["sudo", "nginx", "-t"])
        self.assertEqual(cmds[1], SUDO_RELOAD)
        self.assertEqual(len(cmds), 2)

    def test_failed_nginx_test_rolls_back_new_vhost(self):
        def failing_test(cmd, *args, **kwargs):
            if cmd[-2:] == ["nginx", "-t"]:
                return MagicMock(returncode=1, stderr="unexpected }")
            return _ok()

        self.mock_run.side_effect = failing_test
        with self.assertRaises(RuntimeError):
            self.manager.create_reverse_proxy_vhost(DOMAIN, UPSTREAM, ssl=False)

        self.assertFalse(self.config_path().exists())
        self.assertFalse((self.enabled / self.config_path().name).is_symlink())
        self.assertFalse(
            any(c[-3:] == ["systemctl", "reload", "nginx"] for c in self.commands())
        )

    def test_failed_nginx_test_restores_previous_vhost(self):
        self.manager.create_reverse_proxy_vhost(DOMAIN, UPSTREAM, ssl=False)
        previous = self.config_path().read_text()

        def failing_test(cmd, *args, **kwargs):
            if cmd[-2:] == ["nginx", "-t"]:
                return MagicMock(returncode=1, stderr="bad")
            return _ok()

        self.mock_run.side_effect = failing_test
        with self.assertRaises(RuntimeError):
            self.manager.create_reverse_proxy_vhost(
                DOMAIN, "http://new-app:9000", ssl=False
            )
        self.assertEqual(self.config_path().read_text(), previous)

    def test_remove_vhost(self):
        self.manager.create_reverse_proxy_vhost(DOMAIN, UPSTREAM, ssl=False)
        self.mock_run.reset_mock()

        self.assertTrue(self.manager.remove_vhost(DOMAIN))
        self.assertFalse(self.config_path().exists())
        self.assertFalse((self.enabled / self.config_path().name).is_symlink())
        self.assertTrue(
            any(c[-3:] == ["systemctl", "reload", "nginx"] for c in self.commands())
        )

    def test_remove_vhost_absent_is_noop(self):
        self.assertFalse(self.manager.remove_vhost(DOMAIN))
        self.mock_run.assert_not_called()
        # and a second removal after a real one is equally quiet
        self.manager.create_reverse_proxy_vhost(DOMAIN, UPSTREAM, ssl=False)
        self.manager.remove_vhost(DOMAIN)
        self.mock_run.reset_mock()
        self.assertFalse(self.manager.remove_vhost(DOMAIN))
        self.mock_run.assert_not_called()

    def test_module_level_wrappers(self):
        with patch("rpanel.hosting.nginx_manager.NginxManager") as manager_cls:
            nginx_manager.create_reverse_proxy_vhost(DOMAIN, UPSTREAM, websocket=False)
            manager_cls.return_value.create_reverse_proxy_vhost.assert_called_once_with(
                DOMAIN, UPSTREAM, websocket=False, ssl=None
            )
            nginx_manager.remove_vhost(DOMAIN)
            manager_cls.return_value.remove_vhost.assert_called_once_with(DOMAIN)


class TestReloadNginx(unittest.TestCase):
    @patch("rpanel.hosting.nginx_manager.os.geteuid", return_value=1000)
    @patch("rpanel.hosting.nginx_manager.subprocess.run", side_effect=_ok)
    def test_systemctl_first(self, mock_run, mock_euid):
        self.assertEqual(reload_nginx(), SUDO_RELOAD)
        self.assertEqual(
            [list(c.args[0]) for c in mock_run.call_args_list], [SUDO_RELOAD]
        )

    @patch("rpanel.hosting.nginx_manager.os.geteuid", return_value=1000)
    @patch("rpanel.hosting.nginx_manager.subprocess.run")
    def test_falls_back_when_systemd_refuses(self, mock_run, mock_euid):
        def run(cmd, *args, **kwargs):
            if "systemctl" in cmd:
                raise subprocess.CalledProcessError(
                    1, cmd, stderr="System has not been booted with systemd"
                )
            return _ok()

        mock_run.side_effect = run
        self.assertEqual(reload_nginx(), SUDO_FALLBACK)
        self.assertEqual(
            [list(c.args[0]) for c in mock_run.call_args_list],
            [SUDO_RELOAD, SUDO_FALLBACK],
        )

    @patch("rpanel.hosting.nginx_manager.os.geteuid", return_value=0)
    @patch("rpanel.hosting.nginx_manager.subprocess.run")
    def test_falls_back_when_systemctl_missing_in_container(self, mock_run, mock_euid):
        def run(cmd, *args, **kwargs):
            if cmd[0] == "systemctl":
                raise FileNotFoundError(cmd[0])
            return _ok()

        mock_run.side_effect = run
        # root inside the hub container: no sudo prefix at all
        self.assertEqual(reload_nginx(), ["nginx", "-s", "reload"])
        self.assertEqual(
            [list(c.args[0]) for c in mock_run.call_args_list],
            [["systemctl", "reload", "nginx"], ["nginx", "-s", "reload"]],
        )

    @patch("rpanel.hosting.nginx_manager.os.geteuid", return_value=1000)
    @patch("rpanel.hosting.nginx_manager.subprocess.run")
    def test_raises_when_every_attempt_fails(self, mock_run, mock_euid):
        mock_run.side_effect = subprocess.CalledProcessError(1, "x", stderr="nope")
        with self.assertRaises(RuntimeError) as ctx:
            reload_nginx()
        self.assertIn("systemctl reload nginx", str(ctx.exception))
        self.assertIn("nginx -s reload", str(ctx.exception))

    @patch("rpanel.hosting.nginx_manager.os.geteuid", return_value=1000)
    @patch("rpanel.hosting.nginx_manager.subprocess.run")
    def test_test_and_reload_uses_fallback(self, mock_run, mock_euid):
        def run(cmd, *args, **kwargs):
            if "systemctl" in cmd:
                raise subprocess.CalledProcessError(1, cmd, stderr="no systemd")
            return _ok()

        mock_run.side_effect = run
        NginxManager().test_and_reload()
        self.assertEqual(list(mock_run.call_args_list[-1].args[0]), SUDO_FALLBACK)


class TestCertificates(unittest.TestCase):
    def test_build_certbot_command_default_keeps_www(self):
        cmd = build_certbot_command("example.com", "/var/www/example.com")
        self.assertEqual(cmd.count("-d"), 2)
        self.assertIn("www.example.com", cmd)
        self.assertEqual(cmd[cmd.index("--email") + 1], "admin@example.com")

    def test_build_certbot_command_without_www(self):
        cmd = build_certbot_command(
            DOMAIN, "/var/www/letsencrypt", include_www=False, email="ops@example.com"
        )
        self.assertEqual(cmd[:3], ["sudo", "certbot", "certonly"])
        self.assertEqual(cmd.count("-d"), 1)
        self.assertIn(DOMAIN, cmd)
        self.assertNotIn(f"www.{DOMAIN}", cmd)
        self.assertEqual(cmd[cmd.index("--email") + 1], "ops@example.com")
        self.assertEqual(cmd[cmd.index("-w") + 1], "/var/www/letsencrypt")

    @patch("rpanel.hosting.utils.subprocess.run", side_effect=_ok)
    @patch("rpanel.hosting.utils.os.path.exists", return_value=True)
    def test_run_certbot_existing_callers_unchanged(self, mock_exists, mock_run):
        ok, _ = run_certbot("example.com", "/var/www/example.com")
        self.assertTrue(ok)
        self.assertIn("www.example.com", mock_run.call_args.args[0])

    @patch("rpanel.hosting.nginx_manager._ensure_dir")
    @patch("rpanel.hosting.nginx_manager.run_certbot", return_value=(True, "ok"))
    def test_issue_certificate_no_www(self, mock_certbot, mock_ensure):
        live_dir = nginx_manager.issue_certificate(DOMAIN)
        mock_certbot.assert_called_once_with(
            DOMAIN, nginx_manager.ACME_WEBROOT, include_www=False, email=None
        )
        mock_ensure.assert_called_once_with(nginx_manager.ACME_WEBROOT)
        self.assertEqual(live_dir, f"{nginx_manager.LETSENCRYPT_LIVE}/{DOMAIN}")

    @patch("rpanel.hosting.nginx_manager._ensure_dir")
    @patch("rpanel.hosting.nginx_manager.run_certbot", return_value=(True, "ok"))
    def test_issue_certificate_opt_in_www_and_email(self, mock_certbot, mock_ensure):
        nginx_manager.issue_certificate(
            "example.com",
            include_www=True,
            email="ops@example.com",
            webroot="/srv/acme",
        )
        mock_certbot.assert_called_once_with(
            "example.com", "/srv/acme", include_www=True, email="ops@example.com"
        )

    @patch("rpanel.hosting.nginx_manager._ensure_dir")
    @patch(
        "rpanel.hosting.nginx_manager.run_certbot",
        return_value=(False, "Certbot failed: DNS problem"),
    )
    def test_issue_certificate_raises_on_failure(self, mock_certbot, mock_ensure):
        with self.assertRaises(RuntimeError) as ctx:
            nginx_manager.issue_certificate(DOMAIN)
        self.assertIn("DNS problem", str(ctx.exception))

    def test_issue_certificate_rejects_bad_domain(self):
        with self.assertRaises(ValueError):
            nginx_manager.issue_certificate("not a domain")


if __name__ == "__main__":
    unittest.main()
