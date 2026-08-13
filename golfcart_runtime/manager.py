#!/usr/bin/env python3
"""
Golf Cart System Manager
Comprehensive management tool for Golf Cart production deployment
Provides installation, control, and monitoring capabilities
"""

import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

from .common import (
    get_workspace_dir, get_package_share_dir, get_current_user,
    run_command, check_systemd_service_status, setup_logging
)

logger = setup_logging()

# ANSI color codes
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'


class GolfCartManager:
    def __init__(self):
        self.username = get_current_user()
        self.workspace_dir = get_workspace_dir()
        self.service_name = f"golfcart@{self.username}"
        self.health_service_name = f"golfcart-healthcheck@{self.username}"
        self.health_timer_name = f"golfcart-healthcheck@{self.username}.timer"
        self.web_control_service = f"golfcart-web-control@{self.username}"
        
        try:
            self.package_share_dir = get_package_share_dir('golfcart_runtime')
        except RuntimeError:
            logger.warning("Could not locate golfcart_runtime package share directory")
            self.package_share_dir = None

    def log_info(self, message: str):
        print(f"{Colors.BLUE}[INFO]{Colors.NC} {message}")

    def log_success(self, message: str):
        print(f"{Colors.GREEN}[SUCCESS]{Colors.NC} {message}")

    def log_warning(self, message: str):
        print(f"{Colors.YELLOW}[WARNING]{Colors.NC} {message}")

    def log_error(self, message: str):
        print(f"{Colors.RED}[ERROR]{Colors.NC} {message}")

    def check_root(self):
        """Ensure we're not running as root"""
        if os.geteuid() == 0:
            self.log_error("This script should not be run as root for user service management")
            self.log_info("Run as the user who owns the Golf Cart installation")
            sys.exit(1)

    def check_systemd_requirements(self):
        """Check systemd user service requirements"""
        # Check if lingering is enabled
        try:
            result = run_command(['loginctl', 'show-user', self.username, '-p', 'Linger'], check=False)
            if 'Linger=yes' not in result.stdout:
                self.log_warning("User lingering not enabled. Services won't start automatically at boot.")
                self.log_info(f"To enable: sudo loginctl enable-linger {self.username}")
        except:
            self.log_warning("Could not check user lingering status")

        # Check if systemd user directory exists
        user_systemd_dir = Path.home() / '.config/systemd/user'
        if not user_systemd_dir.exists():
            self.log_info(f"Creating user systemd directory: {user_systemd_dir}")
            user_systemd_dir.mkdir(parents=True)

    def install_services(self):
        """Install systemd service files"""
        self.log_info("Installing Golf Cart systemd services...")
        self.check_systemd_requirements()

        if not self.package_share_dir:
            self.log_error("Package share directory not found. Ensure golfcart_runtime package is built.")
            return False

        user_systemd_dir = Path.home() / '.config/systemd/user'
        systemd_source_dir = self.package_share_dir / 'systemd'

        if not systemd_source_dir.exists():
            self.log_error(f"SystemD templates not found at: {systemd_source_dir}")
            return False

        # Service files to install
        service_files = [
            'golfcart.service',
            'golfcart-healthcheck.service', 
            'golfcart-healthcheck.timer',
            'golfcart-web-control.service'
        ]

        for service_file in service_files:
            src_file = systemd_source_dir / service_file
            dst_file = user_systemd_dir / service_file

            if src_file.exists():
                self.log_info(f"Installing {service_file}")
                shutil.copy2(src_file, dst_file)
            else:
                self.log_warning(f"Service file not found: {src_file}")

        # Reload systemd daemon
        try:
            run_command(['systemctl', '--user', 'daemon-reload'])
            self.log_success("SystemD services installed successfully")
            self.log_info(f"Service files installed to: {user_systemd_dir}")
            return True
        except RuntimeError as e:
            self.log_error(f"Failed to reload systemd daemon: {e}")
            return False

    def uninstall_services(self):
        """Uninstall systemd service files"""
        self.log_info("Uninstalling Golf Cart systemd services...")

        # Stop and disable services first
        self.stop_service()
        self.disable_service()

        user_systemd_dir = Path.home() / '.config/systemd/user'
        service_files = [
            'golfcart.service',
            'golfcart-healthcheck.service',
            'golfcart-healthcheck.timer',
            'golfcart-web-control.service'
        ]

        for service_file in service_files:
            service_path = user_systemd_dir / service_file
            if service_path.exists():
                self.log_info(f"Removing {service_file}")
                service_path.unlink()

        # Reload systemd daemon
        try:
            run_command(['systemctl', '--user', 'daemon-reload'])
            run_command(['systemctl', '--user', 'reset-failed'], check=False)
            self.log_success("SystemD services uninstalled successfully")
        except RuntimeError as e:
            self.log_error(f"Failed to reload systemd daemon: {e}")

    def enable_service(self):
        """Enable services for automatic startup"""
        self.log_info("Enabling Golf Cart services for automatic startup...")

        try:
            run_command(['systemctl', '--user', 'enable', self.service_name])
            run_command(['systemctl', '--user', 'enable', self.health_timer_name])
            self.log_success("Services enabled for automatic startup")
            self.log_info("Services will start automatically when the user logs in")
        except RuntimeError as e:
            self.log_error(f"Failed to enable services: {e}")

    def disable_service(self):
        """Disable automatic startup"""
        self.log_info("Disabling Golf Cart services from automatic startup...")

        try:
            run_command(['systemctl', '--user', 'disable', self.service_name], check=False)
            run_command(['systemctl', '--user', 'disable', self.health_timer_name], check=False)
            run_command(['systemctl', '--user', 'disable', self.web_control_service], check=False)
            self.log_success("Services disabled from automatic startup")
        except RuntimeError as e:
            self.log_warning(f"Some services may not have been disabled: {e}")

    def start_service(self):
        """Start the Golf Cart service"""
        self.log_info("Starting Golf Cart service...")

        # Check if workspace is built
        setup_bash = self.workspace_dir / 'install/setup.bash'
        if not setup_bash.exists():
            self.log_error("Golf Cart workspace not built. Run 'make build' first.")
            return False

        try:
            run_command(['systemctl', '--user', 'start', self.service_name])
            run_command(['systemctl', '--user', 'start', self.health_timer_name])
            
            self.log_success("Golf Cart service started")
            self.log_info("System monitor available at: http://localhost:8080/")
            
            # Show initial status after a brief delay
            time.sleep(2)
            self.status_service()
            return True
            
        except RuntimeError as e:
            self.log_error(f"Failed to start service: {e}")
            return False

    def stop_service(self):
        """Stop the Golf Cart service"""
        self.log_info("Stopping Golf Cart service...")

        try:
            run_command(['systemctl', '--user', 'stop', self.service_name], check=False)
            run_command(['systemctl', '--user', 'stop', self.health_timer_name], check=False)
            run_command(['systemctl', '--user', 'stop', self.health_service_name], check=False)
            run_command(['systemctl', '--user', 'stop', self.web_control_service], check=False)
            self.log_success("Golf Cart service stopped")
        except RuntimeError as e:
            self.log_warning(f"Some services may not have stopped cleanly: {e}")

    def restart_service(self):
        """Restart the Golf Cart service"""
        self.log_info("Restarting Golf Cart service...")
        self.stop_service()
        time.sleep(3)
        return self.start_service()

    def status_service(self):
        """Show service status"""
        self.log_info("Golf Cart Service Status:")
        print("=" * 50)

        # Main service status
        is_active, status = check_systemd_service_status(self.service_name)
        
        if is_active:
            print(f"{Colors.GREEN}● Golf Cart Service: RUNNING{Colors.NC}")
        elif status == 'failed':
            print(f"{Colors.RED}● Golf Cart Service: FAILED{Colors.NC}")
        else:
            print(f"{Colors.YELLOW}● Golf Cart Service: {status.upper()}{Colors.NC}")

        # Health monitor status
        is_health_active, health_status = check_systemd_service_status(self.health_timer_name)
        
        if is_health_active:
            print(f"{Colors.GREEN}● Health Monitor: RUNNING{Colors.NC}")
        else:
            print(f"{Colors.YELLOW}● Health Monitor: {health_status.upper()}{Colors.NC}")

        # Show runtime information if active
        if is_active:
            try:
                result = run_command([
                    'systemctl', '--user', 'show', self.service_name,
                    '--property=ActiveEnterTimestamp', '--value'
                ], check=False)
                if result.returncode == 0 and result.stdout.strip():
                    print(f"  Started: {result.stdout.strip()}")

                result = run_command([
                    'systemctl', '--user', 'show', self.service_name,
                    '--property=MemoryCurrent', '--value'
                ], check=False)
                if result.returncode == 0 and result.stdout.strip() and '[not set]' not in result.stdout:
                    try:
                        memory_bytes = int(result.stdout.strip())
                        memory_mb = memory_bytes // (1024 * 1024)
                        print(f"  Memory Usage: {memory_mb}MB")
                    except ValueError:
                        pass
            except:
                pass

        # Show recent logs
        print()
        self.log_info("Recent logs (last 5 lines):")
        try:
            result = run_command([
                'systemctl', '--user', 'status', self.service_name,
                '--no-pager', '-l', '-n', '5'
            ], check=False)
            if result.returncode == 0:
                lines = result.stdout.split('\n')[3:]  # Skip header lines
                for line in lines:
                    if line.strip():
                        print(f"  {line}")
        except:
            pass

    def show_logs(self, lines: int = 50, follow: bool = False):
        """Show service logs"""
        self.log_info(f"Golf Cart Service Logs (last {lines} lines):")

        cmd = ['journalctl', '--user', '-u', self.service_name, '-n', str(lines), '--no-pager']
        if follow:
            self.log_info("Following logs... (Press Ctrl+C to stop)")
            cmd.extend(['-f'])

        try:
            if follow:
                subprocess.run(cmd)
            else:
                result = run_command(cmd)
                print(result.stdout)
        except KeyboardInterrupt:
            pass
        except RuntimeError as e:
            self.log_error(f"Failed to retrieve logs: {e}")

    def run_health_check(self):
        """Run health check manually"""
        self.log_info("Running manual health check...")
        
        try:
            # Try to run health check via the installed command
            result = run_command(['golfcart-healthcheck'], timeout=30)
            print(result.stdout)
            if result.stderr:
                print(result.stderr, file=sys.stderr)
            return result.returncode == 0
        except RuntimeError as e:
            self.log_error(f"Health check failed: {e}")
            return False

    def show_system_info(self):
        """Show system information"""
        self.log_info("Golf Cart System Information:")
        print("=" * 50)
        print(f"Workspace: {self.workspace_dir}")
        print(f"User: {self.username}")
        print(f"Hostname: {subprocess.run(['hostname'], capture_output=True, text=True).stdout.strip()}")
        
        # OS information
        try:
            result = run_command(['lsb_release', '-d'], check=False)
            if result.returncode == 0:
                print(f"OS: {result.stdout.split(':', 1)[1].strip()}")
            else:
                result = run_command(['uname', '-s'])
                print(f"OS: {result.stdout.strip()}")
        except:
            print("OS: Unknown")

        print(f"ROS2 Distribution: {os.environ.get('ROS_DISTRO', 'unknown')}")
        
        try:
            result = run_command(['python3', '--version'])
            print(f"Python: {result.stdout.strip()}")
        except:
            print("Python: Unknown version")

        # Check workspace build status
        setup_bash = self.workspace_dir / 'install/setup.bash'
        if setup_bash.exists():
            print(f"{Colors.GREEN}Workspace Status: Built{Colors.NC}")
            try:
                stat_result = setup_bash.stat()
                build_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(stat_result.st_mtime))
                print(f"Last Built: {build_time}")
            except:
                pass
        else:
            print(f"{Colors.RED}Workspace Status: Not Built{Colors.NC}")

        # Show service installation status
        user_systemd_dir = Path.home() / '.config/systemd/user'
        service_file = user_systemd_dir / 'golfcart.service'
        if service_file.exists():
            print(f"{Colors.GREEN}Service Status: Installed{Colors.NC}")
        else:
            print(f"{Colors.YELLOW}Service Status: Not Installed{Colors.NC}")

        # Show lingering status
        try:
            result = run_command(['loginctl', 'show-user', self.username, '-p', 'Linger'], check=False)
            if 'Linger=yes' in result.stdout:
                print(f"{Colors.GREEN}User Lingering: Enabled{Colors.NC}")
            else:
                print(f"{Colors.YELLOW}User Lingering: Disabled{Colors.NC}")
        except:
            print("User Lingering: Unknown")

    def cleanup(self):
        """Clean up logs and temporary files"""
        self.log_info("Cleaning up Golf Cart logs and temporary files...")

        cleanup_dirs = [
            self.workspace_dir / 'logs/launch',
            self.workspace_dir / 'logs/health',
            self.workspace_dir / 'logs/systemd'
        ]

        for log_dir in cleanup_dirs:
            if log_dir.exists():
                self.log_info(f"Cleaning directory: {log_dir}")
                
                # Remove old log files (older than 7 days)
                try:
                    for log_file in log_dir.glob('*.log'):
                        if log_file.is_file():
                            file_age = time.time() - log_file.stat().st_mtime
                            if file_age > (7 * 24 * 60 * 60):  # 7 days in seconds
                                log_file.unlink()
                    
                    # Remove PID files
                    for pid_file in log_dir.glob('*.pid'):
                        pid_file.unlink()
                        
                except Exception as e:
                    self.log_warning(f"Error cleaning {log_dir}: {e}")

        # Clean journal logs older than 30 days
        try:
            run_command(['journalctl', '--user', '--vacuum-time=30d'], check=False)
        except:
            pass

        self.log_success("Cleanup completed")


def main():
    """Main entry point for golfcart-manager command"""
    parser = argparse.ArgumentParser(
        description='Golf Cart System Manager',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  golfcart-manager install        # Install and enable services
  golfcart-manager start          # Start Golf Cart
  golfcart-manager status         # Check service status
  golfcart-manager logs 100       # Show last 100 log lines
  golfcart-manager logs-follow    # Follow logs in real-time
        """
    )
    
    parser.add_argument('command', choices=[
        'install', 'uninstall', 'enable', 'disable',
        'start', 'stop', 'restart', 'status',
        'logs', 'logs-follow', 'health', 'info', 'cleanup'
    ], help='Command to execute')
    
    parser.add_argument('lines', nargs='?', type=int, default=50,
                        help='Number of log lines to show (for logs command)')
    
    args = parser.parse_args()
    
    manager = GolfCartManager()
    
    # Ensure we're not running as root
    manager.check_root()
    
    try:
        if args.command == 'install':
            if manager.install_services():
                manager.enable_service()
                manager.log_info("Installation complete. Use 'golfcart-manager start' to start the service.")
        elif args.command == 'uninstall':
            manager.uninstall_services()
            manager.log_info("Uninstallation complete.")
        elif args.command == 'enable':
            manager.enable_service()
        elif args.command == 'disable':
            manager.disable_service()
        elif args.command == 'start':
            manager.start_service()
        elif args.command == 'stop':
            manager.stop_service()
        elif args.command == 'restart':
            manager.restart_service()
        elif args.command == 'status':
            manager.status_service()
        elif args.command == 'logs':
            manager.show_logs(args.lines, False)
        elif args.command == 'logs-follow':
            manager.show_logs(args.lines, True)
        elif args.command == 'health':
            success = manager.run_health_check()
            sys.exit(0 if success else 1)
        elif args.command == 'info':
            manager.show_system_info()
        elif args.command == 'cleanup':
            manager.cleanup()
            
    except KeyboardInterrupt:
        manager.log_info("Operation interrupted by user")
        sys.exit(1)
    except Exception as e:
        manager.log_error(f"Unexpected error: {e}")
        logger.exception("Full traceback:")
        sys.exit(1)


if __name__ == '__main__':
    main()