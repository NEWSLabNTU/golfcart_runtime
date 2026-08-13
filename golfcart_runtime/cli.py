#!/usr/bin/env python3
"""
Golf Cart Unified Command Line Interface
Provides a simple, unified interface for managing Golf Cart in production
"""

import argparse
import os
import shutil
import subprocess
import sys
import time
import webbrowser
from pathlib import Path
from typing import Optional

from .common import get_workspace_dir, get_package_share_dir, get_current_user, setup_logging

logger = setup_logging()

# ANSI color codes for pretty output
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'


class GolfCart:
    """Main Golf Cart command line interface"""

    def __init__(self):
        self.username = get_current_user()
        self.workspace_dir = get_workspace_dir()
        self.user_systemd_dir = Path.home() / '.config/systemd/user'

        # Service names
        self.service_name = f"golfcart@{self.username}"

        # Try to get package share directory
        try:
            self.package_share_dir = get_package_share_dir('golfcart_runtime')
            self.launch_script = self.package_share_dir / 'scripts' / 'golfcart-launch.sh'
        except RuntimeError:
            # Fallback: try to find it relative to the workspace
            install_dir = self.workspace_dir / 'install' / 'golfcart_runtime'
            if install_dir.exists():
                self.package_share_dir = install_dir / 'share' / 'golfcart_runtime'
                self.launch_script = self.package_share_dir / 'scripts' / 'golfcart-launch.sh'
            else:
                self.package_share_dir = None
                self.launch_script = None

    def print_success(self, message: str):
        """Print success message in green"""
        print(f"{Colors.GREEN}✓{Colors.END} {message}")

    def print_error(self, message: str):
        """Print error message in red"""
        print(f"{Colors.RED}✗{Colors.END} {message}")

    def print_info(self, message: str):
        """Print info message in blue"""
        print(f"{Colors.BLUE}ℹ{Colors.END} {message}")

    def print_warning(self, message: str):
        """Print warning message in yellow"""
        print(f"{Colors.YELLOW}⚠{Colors.END} {message}")

    def install(self, args):
        """Install Golf Cart systemd services"""
        self.print_info("Installing Golf Cart systemd services...")

        # Create user systemd directory if it doesn't exist
        self.user_systemd_dir.mkdir(parents=True, exist_ok=True)

        # Check if launch script exists
        if not self.launch_script or not self.launch_script.exists():
            self.print_error(f"Launch script not found. Please build the workspace first.")
            return False

        # Load and process the systemd template
        systemd_template = self.package_share_dir / 'systemd' / 'golfcart.service'
        if not systemd_template.exists():
            self.print_error(f"Service template not found: {systemd_template}")
            return False

        # Read template and substitute variables
        with open(systemd_template, 'r') as f:
            service_content = f.read()

        # Replace template variables
        service_content = service_content.replace('%i', self.username)
        service_content = service_content.replace('%h', str(Path.home()))
        service_content = service_content.replace('%h/AutoSDV', str(self.workspace_dir))

        # Write service file
        service_file = self.user_systemd_dir / 'golfcart.service'
        with open(service_file, 'w') as f:
            f.write(service_content)

        # Reload systemd daemon
        subprocess.run(['systemctl', '--user', 'daemon-reload'], check=True)

        self.print_success(f"Golf Cart service installed to {service_file}")
        self.print_info("Service is installed but NOT enabled for automatic startup")
        self.print_info("To enable automatic startup at login: golfcart enable")
        self.print_info("To start now, run: golfcart start")

        # Check and suggest lingering
        result = subprocess.run(
            ['loginctl', 'show-user', self.username, '-p', 'Linger'],
            capture_output=True, text=True
        )
        if 'Linger=no' in result.stdout:
            self.print_warning("User lingering is disabled. Service won't start at boot.")
            self.print_info(f"To enable: sudo loginctl enable-linger {self.username}")

        return True

    def start(self, args):
        """Start Golf Cart system"""
        self.print_info("Starting Golf Cart system...")

        try:
            # Check if already running
            result = subprocess.run(
                ['systemctl', '--user', 'is-active', 'golfcart'],
                capture_output=True, text=True
            )
            if result.stdout.strip() == 'active':
                self.print_warning("Golf Cart is already running")
                return True

            # Start the service
            subprocess.run(['systemctl', '--user', 'start', 'golfcart'], check=True)

            # Wait a moment for service to start
            time.sleep(2)

            # Check if started successfully
            result = subprocess.run(
                ['systemctl', '--user', 'is-active', 'golfcart'],
                capture_output=True, text=True
            )

            if result.stdout.strip() == 'active':
                self.print_success("Golf Cart started successfully")
                self.print_info("System monitor: http://localhost:8080/")
                self.print_info("View logs: golfcart status")
                return True
            else:
                self.print_error("Failed to start Golf Cart")
                self.print_info("Check logs: journalctl --user -u golfcart -n 50")
                return False

        except subprocess.CalledProcessError as e:
            self.print_error(f"Failed to start service: {e}")
            return False

    def stop(self, args):
        """Stop Golf Cart system"""
        self.print_info("Stopping Golf Cart system...")

        try:
            subprocess.run(['systemctl', '--user', 'stop', 'golfcart'], check=True)
            self.print_success("Golf Cart stopped")
            return True
        except subprocess.CalledProcessError as e:
            self.print_error(f"Failed to stop service: {e}")
            return False

    def restart(self, args):
        """Restart Golf Cart system"""
        self.print_info("Restarting Golf Cart system...")

        try:
            subprocess.run(['systemctl', '--user', 'restart', 'golfcart'], check=True)

            # Wait for restart
            time.sleep(3)

            # Check status
            result = subprocess.run(
                ['systemctl', '--user', 'is-active', 'golfcart'],
                capture_output=True, text=True
            )

            if result.stdout.strip() == 'active':
                self.print_success("Golf Cart restarted successfully")
                return True
            else:
                self.print_error("Golf Cart failed to restart")
                return False

        except subprocess.CalledProcessError as e:
            self.print_error(f"Failed to restart service: {e}")
            return False

    def status(self, args):
        """Show Golf Cart system status"""
        print(f"\n{Colors.BOLD}Golf Cart System Status{Colors.END}")
        print("=" * 50)

        # Check service status
        result = subprocess.run(
            ['systemctl', '--user', 'is-active', 'golfcart'],
            capture_output=True, text=True
        )
        service_status = result.stdout.strip()

        # Color code the status
        if service_status == 'active':
            status_display = f"{Colors.GREEN}● RUNNING{Colors.END}"
        elif service_status == 'failed':
            status_display = f"{Colors.RED}● FAILED{Colors.END}"
        elif service_status == 'inactive':
            status_display = f"{Colors.YELLOW}● STOPPED{Colors.END}"
        else:
            status_display = f"{Colors.YELLOW}● {service_status.upper()}{Colors.END}"

        print(f"Service Status: {status_display}")

        # Get additional service info
        if service_status == 'active':
            # Get runtime
            result = subprocess.run(
                ['systemctl', '--user', 'show', 'golfcart', '--property=ActiveEnterTimestamp'],
                capture_output=True, text=True
            )
            if '=' in result.stdout:
                timestamp = result.stdout.split('=')[1].strip()
                if timestamp:
                    print(f"Started: {timestamp}")

            # Get PID
            result = subprocess.run(
                ['systemctl', '--user', 'show', 'golfcart', '--property=MainPID'],
                capture_output=True, text=True
            )
            if '=' in result.stdout:
                pid = result.stdout.split('=')[1].strip()
                if pid and pid != '0':
                    print(f"Process ID: {pid}")

        # Show recent logs
        print(f"\n{Colors.BOLD}Recent Logs:{Colors.END}")
        print("-" * 50)

        # Try journalctl first, but fall back to systemctl if needed
        result = subprocess.run(
            ['journalctl', '--user', '-u', 'golfcart', '-n', '10', '--no-pager'],
            capture_output=True, text=True, check=False
        )

        if 'No journal files were found' in result.stderr or not result.stdout.strip():
            # Fallback to systemctl status to get logs
            subprocess.run(
                ['systemctl', '--user', 'status', 'golfcart', '--no-pager', '-n', '10'],
                check=False
            )
        else:
            print(result.stdout)

        # Show available commands
        print(f"\n{Colors.BOLD}Available Commands:{Colors.END}")
        if service_status == 'active':
            print("  golfcart stop     - Stop the system")
            print("  golfcart restart  - Restart the system")
            print("  golfcart monitor  - Open web monitor")
        else:
            print("  golfcart start    - Start the system")
            print("  golfcart install  - Install systemd service")

        return True

    def monitor(self, args):
        """Open the web monitor in browser"""
        url = "http://localhost:8080/"

        self.print_info(f"Opening web monitor at {url}")

        # Check if service is running
        result = subprocess.run(
            ['systemctl', '--user', 'is-active', 'golfcart'],
            capture_output=True, text=True
        )

        if result.stdout.strip() != 'active':
            self.print_warning("Golf Cart is not running. Starting it first...")
            if not self.start(args):
                return False
            time.sleep(3)  # Give it time to start the web server

        # Try to open in browser
        try:
            webbrowser.open(url)
            self.print_success(f"Web monitor opened in browser")
        except:
            self.print_info(f"Please open your browser and navigate to: {url}")

        return True

    def enable(self, args):
        """Enable Golf Cart to start automatically at login"""
        self.print_info("Enabling Golf Cart automatic startup at login...")

        try:
            # Check if service exists
            service_file = self.user_systemd_dir / 'golfcart.service'
            if not service_file.exists():
                self.print_error("Golf Cart service not installed. Run 'golfcart install' first.")
                return False

            # Enable the service
            subprocess.run(['systemctl', '--user', 'enable', 'golfcart'], check=True)
            self.print_success("Golf Cart enabled for automatic startup at login")

            # Check lingering status
            result = subprocess.run(
                ['loginctl', 'show-user', self.username, '-p', 'Linger'],
                capture_output=True, text=True
            )
            if 'Linger=no' in result.stdout:
                self.print_warning("User lingering is disabled. Service will only start when you log in.")
                self.print_info(f"To enable startup at boot (without login): sudo loginctl enable-linger {self.username}")
            else:
                self.print_info("Service will start at system boot (lingering enabled)")

            return True

        except subprocess.CalledProcessError as e:
            self.print_error(f"Failed to enable service: {e}")
            return False

    def disable(self, args):
        """Disable Golf Cart automatic startup"""
        self.print_info("Disabling Golf Cart automatic startup...")

        try:
            # Check if service exists
            service_file = self.user_systemd_dir / 'golfcart.service'
            if not service_file.exists():
                self.print_error("Golf Cart service not installed")
                return False

            # Disable the service
            subprocess.run(['systemctl', '--user', 'disable', 'golfcart'], check=True)
            self.print_success("Golf Cart automatic startup disabled")
            self.print_info("Service can still be started manually with: golfcart start")

            return True

        except subprocess.CalledProcessError as e:
            self.print_error(f"Failed to disable service: {e}")
            return False

    def uninstall(self, args):
        """Uninstall Golf Cart systemd service"""
        self.print_info("Uninstalling Golf Cart systemd service...")

        # Stop the service first
        subprocess.run(['systemctl', '--user', 'stop', 'golfcart'], check=False)

        # Disable the service
        subprocess.run(['systemctl', '--user', 'disable', 'golfcart'], check=False)

        # Remove service file
        service_file = self.user_systemd_dir / 'golfcart.service'
        if service_file.exists():
            service_file.unlink()
            self.print_success("Service file removed")

        # Reload systemd
        subprocess.run(['systemctl', '--user', 'daemon-reload'], check=False)
        subprocess.run(['systemctl', '--user', 'reset-failed'], check=False)

        self.print_success("Golf Cart service uninstalled")
        return True


def main():
    """Main entry point for golfcart command"""
    parser = argparse.ArgumentParser(
        description='Golf Cart - Unified management interface for autonomous vehicle system',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  golfcart install   # Install systemd service
  golfcart start     # Start the system
  golfcart status    # Check system status
  golfcart monitor   # Open web monitor in browser
  golfcart stop      # Stop the system
  golfcart restart   # Restart the system
        """
    )

    # Add subcommands
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    subparsers.add_parser('install', help='Install Golf Cart systemd service')
    subparsers.add_parser('uninstall', help='Uninstall Golf Cart systemd service')
    subparsers.add_parser('enable', help='Enable automatic startup at login')
    subparsers.add_parser('disable', help='Disable automatic startup')
    subparsers.add_parser('start', help='Start Golf Cart system')
    subparsers.add_parser('stop', help='Stop Golf Cart system')
    subparsers.add_parser('restart', help='Restart Golf Cart system')
    subparsers.add_parser('status', help='Show system status and logs')
    subparsers.add_parser('monitor', help='Open web monitor in browser')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Create Golf Cart instance and run command
    golfcart = GolfCart()

    # Map commands to methods
    commands = {
        'install': golfcart.install,
        'uninstall': golfcart.uninstall,
        'enable': golfcart.enable,
        'disable': golfcart.disable,
        'start': golfcart.start,
        'stop': golfcart.stop,
        'restart': golfcart.restart,
        'status': golfcart.status,
        'monitor': golfcart.monitor,
    }

    # Execute the command
    try:
        success = commands[args.command](args)
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        return 1
    except Exception as e:
        print(f"{Colors.RED}Error:{Colors.END} {e}")
        logger.exception("Unexpected error")
        return 1


if __name__ == '__main__':
    sys.exit(main())
