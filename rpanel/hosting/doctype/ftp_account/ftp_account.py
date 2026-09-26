# Copyright (c) 2025, Rokct Holdings and contributors
# For license information, please see license.txt

import sys
import frappe
from frappe.model.document import Document
import subprocess
import os


class FTPAccount(Document):
    def on_insert(self):
        """Create FTP user on system"""
        self.create_ftp_user()

    def on_trash(self):
        """Delete FTP user from system"""
        self.delete_ftp_user()

    def create_ftp_user(self):
        """Create system FTP user"""
        try:
            # A home that already exists is shared (normally the site
            # docroot): never let useradd take it over and never chown it
            # away from the site user / php-fpm. Give the FTP user access
            # through the directory's group instead.
            shared_home = os.path.exists(self.home_directory)

            # 1. Create user
            # Avoid shell=False to prevent injection and separate args safely
            cmd = ["useradd", "-d", self.home_directory, "-s", "/bin/bash"]
            if shared_home:
                import grp

                group = grp.getgrgid(os.stat(self.home_directory).st_gid).gr_name
                cmd += ["-M", "-G", group]
            else:
                cmd += ["-m"]
            subprocess.run(cmd + [self.username], check=True)

            # 2. Set password SECURELY
            # Pass data via stdin (input=...) instead of echo.
            # This keeps the password hidden from process lists (ps aux)
            payload = f"{self.username}:{self.get_password('password')}"
            subprocess.run(["chpasswd"], input=payload, text=True, check=True)

            # 3. Set permissions (only on a home created for this user)
            if not shared_home:
                subprocess.run(
                    ["chown", "-R", f"{self.username}:www-data", self.home_directory],
                    check=True,
                )
                subprocess.run(["chmod", "755", self.home_directory], check=True)

            # 4. Add to vsftpd user list
            with open("/etc/vsftpd.userlist", "a") as f:
                f.write(f"{self.username}\n")

            # 5. Restart FTP service
            subprocess.run(["systemctl", "restart", "vsftpd"], check=True)

        except subprocess.CalledProcessError as e:
            frappe.log_error(f"System command failed: {e}")
            frappe.throw("Failed to setup FTP user. Check logs.")
        except Exception as e:
            frappe.log_error(f"FTP user creation failed: {str(e)}")
            frappe.throw("An error occurred while creating the FTP account.")

    def delete_ftp_user(self):
        """Delete system FTP user"""
        try:
            # Delete the user but never with -r: the home may be a site
            # docroot shared with the website. Only remove a home that is
            # not any website's path and is owned by this FTP user.
            import pwd
            import shutil

            home = self.home_directory
            try:
                uid = pwd.getpwnam(self.username).pw_uid
            except KeyError:
                uid = None
            subprocess.run(["userdel", self.username], check=True)
            if home and uid is not None and os.path.isdir(home):
                real = os.path.realpath(home)
                site_paths = [
                    os.path.realpath(p)
                    for p in frappe.get_all(
                        "Hosted Website",
                        filters={"site_path": ["is", "set"]},
                        pluck="site_path",
                    )
                ]
                overlaps_site = any(
                    real == sp
                    or sp.startswith(real + os.sep)
                    or real.startswith(sp + os.sep)
                    for sp in site_paths
                )
                if (
                    not overlaps_site
                    and os.stat(real).st_uid == uid
                    and real not in ("/", "/home", "/var/www")
                ):
                    shutil.rmtree(real)

            # Remove from vsftpd user list
            if os.path.exists("/etc/vsftpd.userlist"):
                with open("/etc/vsftpd.userlist", "r") as f:
                    lines = f.readlines()
                with open("/etc/vsftpd.userlist", "w") as f:
                    for line in lines:
                        if line.strip() != self.username:
                            f.write(line)

            # Restart FTP service
            subprocess.run(["systemctl", "restart", "vsftpd"], check=True)

        except Exception as e:
            frappe.log_error(f"FTP user deletion failed: {str(e)}")


@frappe.whitelist()
def get_ftp_logs(username: str, lines: str = 50) -> dict:
    """Get FTP connection logs for user"""
    sys.stderr.write(
        f"[TRACE] get_ftp_logs trace_id={getattr(getattr(__import__('frappe'), 'local', object()), 'trace_id', 'n/a')}\n"
    )
    try:
        # Pure Python file read — eliminates shell injection risk entirely
        log_path = "/var/log/vsftpd.log"
        if not os.path.exists(log_path):
            return {"success": True, "logs": ""}
        with open(log_path, "r") as f:
            matching = [line for line in f if username in line]
        output = "".join(matching[-int(lines) :])
        return {"success": True, "logs": output}
    except Exception as e:
        return {"success": False, "error": str(e)}


@frappe.whitelist()
def test_ftp_connection(username: str, password: str) -> dict:
    """Test FTP connection"""
    sys.stderr.write(
        f"[TRACE] test_ftp_connection trace_id={getattr(getattr(__import__('frappe'), 'local', object()), 'trace_id', 'n/a')}\n"
    )
    try:
        import ftplib  # nosec B402 — FTP is the intentional purpose of this module

        ftp = ftplib.FTP("localhost")  # nosec B321
        ftp.login(username, password)
        ftp.quit()

        return {"success": True, "message": "Connection successful"}
    except Exception as e:
        return {"success": False, "error": str(e)}
