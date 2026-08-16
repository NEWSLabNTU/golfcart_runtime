#!/usr/bin/env python3
"""
Golf Cart SystemD Service Installer
Installs systemd user services for Golf Cart deployment
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

from .common import (
    get_current_user,
    get_package_share_dir,
    get_workspace_dir,
    run_command,
    setup_logging,
)

logger = setup_logging()


class SystemDInstaller:
    def __init__(self):
        self.username = get_current_user()
        self.user_systemd_dir = Path.home() / '.config/systemd/user'
        
        try:
            self.package_share_dir = get_package_share_dir('golfcart_runtime')
            self.systemd_templates_dir = self.package_share_dir / 'systemd'
        except RuntimeError:
            logger.error("Could not locate golfcart_runtime package")
            sys.exit(1)

        try:
            self.workspace_dir = get_workspace_dir()
        except RuntimeError:
            logger.error(
                "Could not locate the Golf Cart workspace. The units need its "
                "path; set GOLFCART_WORKSPACE or run from inside the workspace."
            )
            sys.exit(1)

    def log_info(self, message: str):
        print(f"[INFO] {message}")

    def log_success(self, message: str):
        print(f"[SUCCESS] {message}")

    def log_error(self, message: str):
        print(f"[ERROR] {message}")

    def render_unit(self, text: str) -> str:
        """Fill the workspace path into a unit template.

        The units used to hardcode %h/AutoSDV, which was wrong for every
        checkout not in that exact place — and systemd reports it as a failed
        unit with a path error rather than as a stale assumption. The workspace
        is resolved the same way the rest of the CLI resolves it, so a clone
        anywhere works without editing the units.
        """
        rendered = text.replace("@GOLFCART_WORKSPACE@", str(self.workspace_dir))
        leftover = re.findall(r"@[A-Z_]+@", rendered)
        if leftover:
            raise RuntimeError(
                f"unit template has unsubstituted placeholders: {sorted(set(leftover))}"
            )
        return rendered

    def install_services(self):
        """Install systemd service files"""
        self.log_info("Installing Golf Cart systemd services...")
        
        # Create user systemd directory
        self.user_systemd_dir.mkdir(parents=True, exist_ok=True)
        
        if not self.systemd_templates_dir.exists():
            self.log_error(f"SystemD templates not found at: {self.systemd_templates_dir}")
            return False
        
        # Service files to install
        service_files = [
            'golfcart.service',
            'golfcart-healthcheck.service',
            'golfcart-healthcheck.timer',
            'golfcart-web-control.service'
        ]
        
        installed_files = []
        
        for service_file in service_files:
            src_file = self.systemd_templates_dir / service_file
            dst_file = self.user_systemd_dir / service_file
            
            if src_file.exists():
                self.log_info(f"Installing {service_file}")
                try:
                    dst_file.write_text(self.render_unit(src_file.read_text()))
                except RuntimeError as error:
                    self.log_error(f"{service_file}: {error}")
                    return False
                installed_files.append(service_file)
            else:
                self.log_error(f"Service template not found: {src_file}")
                return False
        
        # Reload systemd daemon
        try:
            run_command(['systemctl', '--user', 'daemon-reload'])
            self.log_success(f"Installed {len(installed_files)} systemd services")
            self.log_info(f"Service files installed to: {self.user_systemd_dir}")
            self.log_info(f"Workspace path baked into the units: {self.workspace_dir}")
            return True
        except RuntimeError as e:
            self.log_error(f"Failed to reload systemd daemon: {e}")
            return False

    def uninstall_services(self):
        """Uninstall systemd service files"""
        self.log_info("Uninstalling Golf Cart systemd services...")
        
        service_files = [
            'golfcart.service',
            'golfcart-healthcheck.service',
            'golfcart-healthcheck.timer',
            'golfcart-web-control.service'
        ]
        
        removed_files = []
        
        for service_file in service_files:
            service_path = self.user_systemd_dir / service_file
            if service_path.exists():
                self.log_info(f"Removing {service_file}")
                service_path.unlink()
                removed_files.append(service_file)
        
        # Reload systemd daemon
        try:
            run_command(['systemctl', '--user', 'daemon-reload'])
            run_command(['systemctl', '--user', 'reset-failed'], check=False)
            
            if removed_files:
                self.log_success(f"Removed {len(removed_files)} systemd services")
            else:
                self.log_info("No systemd services found to remove")
            return True
        except RuntimeError as e:
            self.log_error(f"Failed to reload systemd daemon: {e}")
            return False

    def enable_lingering(self):
        """Enable user lingering for automatic service startup"""
        try:
            run_command(['sudo', 'loginctl', 'enable-linger', self.username])
            self.log_success("User lingering enabled - services will start at boot")
            return True
        except RuntimeError as e:
            self.log_error(f"Failed to enable user lingering: {e}")
            self.log_info("You may need to run: sudo loginctl enable-linger $(whoami)")
            return False

    def disable_lingering(self):
        """Disable user lingering"""
        try:
            run_command(['sudo', 'loginctl', 'disable-linger', self.username])
            self.log_success("User lingering disabled")
            return True
        except RuntimeError as e:
            self.log_error(f"Failed to disable user lingering: {e}")
            return False

    def status(self):
        """Show installation status"""
        self.log_info("Golf Cart SystemD Installation Status")
        print("=" * 50)
        
        # Check if services are installed
        service_files = [
            'golfcart.service',
            'golfcart-healthcheck.service',
            'golfcart-healthcheck.timer',
            'golfcart-web-control.service'
        ]
        
        installed_count = 0
        for service_file in service_files:
            service_path = self.user_systemd_dir / service_file
            if service_path.exists():
                print(f"✓ {service_file}: Installed")
                installed_count += 1
            else:
                print(f"✗ {service_file}: Not installed")
        
        print(f"\nInstalled services: {installed_count}/{len(service_files)}")
        
        # Check lingering status
        try:
            result = run_command(['loginctl', 'show-user', self.username, '-p', 'Linger'], check=False)
            if 'Linger=yes' in result.stdout:
                print("✓ User lingering: Enabled")
            else:
                print("✗ User lingering: Disabled")
        except:
            print("? User lingering: Unknown")


def main():
    """Main entry point for golfcart-install-systemd command"""
    parser = argparse.ArgumentParser(description='Golf Cart SystemD Service Installer')
    parser.add_argument('command', choices=['install', 'uninstall', 'enable-linger', 'disable-linger', 'status'])
    
    args = parser.parse_args()
    
    installer = SystemDInstaller()
    
    try:
        if args.command == 'install':
            success = installer.install_services()
            sys.exit(0 if success else 1)
        elif args.command == 'uninstall':
            success = installer.uninstall_services()
            sys.exit(0 if success else 1)
        elif args.command == 'enable-linger':
            success = installer.enable_lingering()
            sys.exit(0 if success else 1)
        elif args.command == 'disable-linger':
            success = installer.disable_lingering()
            sys.exit(0 if success else 1)
        elif args.command == 'status':
            installer.status()
    except Exception as e:
        logger.error(f"Operation failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()