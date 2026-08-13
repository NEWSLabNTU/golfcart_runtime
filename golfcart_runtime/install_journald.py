#!/usr/bin/env python3
"""
Golf Cart Journald Configuration Installer
Installs optimized journald configuration for autonomous vehicle deployment
"""

import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from .common import get_package_share_dir, run_command, setup_logging

logger = setup_logging()


class JournaldInstaller:
    def __init__(self):
        self.system_config_dir = Path('/etc/systemd/journald.conf.d')
        self.target_config_file = self.system_config_dir / 'golfcart.conf'
        
        try:
            self.package_share_dir = get_package_share_dir('golfcart_runtime')
            self.config_source = self.package_share_dir / 'systemd/journald-golfcart.conf'
        except RuntimeError:
            logger.error("Could not locate golfcart_runtime package")
            sys.exit(1)

    def log_info(self, message: str):
        print(f"[INFO] {message}")

    def log_success(self, message: str):
        print(f"[SUCCESS] {message}")

    def log_error(self, message: str):
        print(f"[ERROR] {message}")

    def log_warning(self, message: str):
        print(f"[WARNING] {message}")

    def check_root(self):
        """Check if running as root"""
        if os.geteuid() != 0:
            self.log_error("This command must be run as root to configure systemd journald")
            self.log_info("Run: sudo golfcart-install-journald <command>")
            sys.exit(1)

    def backup_existing_config(self):
        """Backup existing configuration"""
        if self.target_config_file.exists():
            backup_file = Path(str(self.target_config_file) + f'.backup.{int(time.time())}')
            self.log_info(f"Backing up existing configuration to: {backup_file}")
            shutil.copy2(self.target_config_file, backup_file)

    def install_config(self):
        """Install journald configuration"""
        self.check_root()
        self.log_info("Installing Golf Cart journald configuration...")
        
        # Create config directory if it doesn't exist
        if not self.system_config_dir.exists():
            self.log_info(f"Creating journald config directory: {self.system_config_dir}")
            self.system_config_dir.mkdir(parents=True)
        
        # Check if source config exists
        if not self.config_source.exists():
            self.log_error(f"Source configuration file not found: {self.config_source}")
            return False
        
        # Backup existing config
        self.backup_existing_config()
        
        # Install new configuration
        self.log_info(f"Installing configuration to: {self.target_config_file}")
        shutil.copy2(self.config_source, self.target_config_file)
        
        # Set proper permissions
        os.chmod(self.target_config_file, 0o644)
        shutil.chown(self.target_config_file, 'root', 'root')
        
        self.log_success("Configuration installed successfully")
        return True

    def validate_config(self):
        """Validate configuration"""
        self.log_info("Validating journald configuration...")
        
        try:
            # Check configuration syntax (systemd will parse and validate)
            result = run_command(['systemd-analyze', 'cat-config', 'systemd/journald.conf'], check=False)
            if result.returncode == 0:
                self.log_success("Configuration validation passed")
                return True
            else:
                self.log_error("Configuration validation failed")
                return False
        except Exception as e:
            self.log_error(f"Could not validate configuration: {e}")
            return False

    def restart_journald(self):
        """Restart journald service"""
        self.check_root()
        self.log_info("Restarting systemd-journald service to apply new configuration...")
        
        try:
            # Restart journald
            run_command(['systemctl', 'restart', 'systemd-journald'])
            
            # Check if service is running
            result = run_command(['systemctl', 'is-active', 'systemd-journald'], check=False)
            if result.returncode == 0:
                self.log_success("systemd-journald restarted successfully")
                return True
            else:
                self.log_error("Failed to restart systemd-journald")
                return False
        except Exception as e:
            self.log_error(f"Failed to restart journald: {e}")
            return False

    def setup_storage(self):
        """Create storage directories with proper permissions"""
        self.check_root()
        self.log_info("Setting up journal storage directories...")
        
        journal_dir = Path('/var/log/journal')
        
        if not journal_dir.exists():
            self.log_info(f"Creating persistent journal directory: {journal_dir}")
            journal_dir.mkdir(parents=True)
            
            # Set proper permissions for journal directory
            shutil.chown(journal_dir, 'root', 'systemd-journal')
            os.chmod(journal_dir, 0o2755)
            
            # Create machine-id subdirectory
            try:
                result = run_command(['systemd-machine-id-setup', '--print'], check=False)
                if result.returncode == 0:
                    machine_id = result.stdout.strip()
                else:
                    with open('/etc/machine-id', 'r') as f:
                        machine_id = f.read().strip()
                
                machine_journal_dir = journal_dir / machine_id
                
                if not machine_journal_dir.exists():
                    machine_journal_dir.mkdir(parents=True)
                    shutil.chown(machine_journal_dir, 'root', 'systemd-journal')
                    os.chmod(machine_journal_dir, 0o2755)
                
                self.log_success("Journal storage directories created")
                return True
            except Exception as e:
                self.log_error(f"Failed to setup storage directories: {e}")
                return False
        else:
            self.log_info("Journal storage directory already exists")
            return True

    def uninstall_config(self):
        """Uninstall configuration"""
        self.check_root()
        self.log_info("Uninstalling Golf Cart journald configuration...")
        
        if self.target_config_file.exists():
            # Create backup before removal
            self.backup_existing_config()
            
            # Remove configuration
            self.target_config_file.unlink()
            self.log_success("Configuration removed")
            
            # Restart journald to apply default configuration
            self.restart_journald()
            
            self.log_success("Golf Cart journald configuration uninstalled")
            return True
        else:
            self.log_warning("Golf Cart journald configuration not found - nothing to uninstall")
            return True

    def show_status(self):
        """Show configuration status"""
        self.log_info("Current journald configuration status:")
        print("=" * 50)
        
        # Show active configuration
        self.log_info("Active journald configuration:")
        try:
            result = run_command([
                'systemctl', 'show', 'systemd-journald',
                '-p', 'FragmentPath', '-p', 'LoadState',
                '-p', 'ActiveState', '-p', 'SubState'
            ])
            print(result.stdout)
        except:
            print("Could not retrieve systemd-journald status")
        
        print()
        self.log_info("Journal storage information:")
        try:
            result = run_command(['journalctl', '--disk-usage'], check=False)
            if result.returncode == 0:
                print(result.stdout)
            else:
                self.log_warning("Could not retrieve disk usage information")
        except:
            self.log_warning("Could not retrieve disk usage information")
        
        print()
        self.log_info("Recent journal statistics:")
        try:
            result = run_command(['systemctl', 'status', 'systemd-journald', '--no-pager', '-l'], check=False)
            if result.returncode == 0:
                lines = result.stdout.split('\n')[:15]  # Show first 15 lines
                print('\n'.join(lines))
        except:
            pass


def main():
    """Main entry point for golfcart-install-journald command"""
    parser = argparse.ArgumentParser(description='Golf Cart Journald Configuration Installer')
    parser.add_argument('command', choices=['install', 'uninstall', 'status', 'validate'])
    
    args = parser.parse_args()
    
    installer = JournaldInstaller()
    
    try:
        if args.command == 'install':
            success = (installer.setup_storage() and 
                      installer.install_config() and 
                      installer.validate_config() and 
                      installer.restart_journald())
            
            if success:
                print()
                installer.show_status()
                print()
                installer.log_success("Golf Cart journald configuration installed successfully")
                installer.log_info("Journal logs are now optimized for autonomous vehicle deployment")
            
            sys.exit(0 if success else 1)
            
        elif args.command == 'uninstall':
            success = installer.uninstall_config()
            sys.exit(0 if success else 1)
            
        elif args.command == 'status':
            installer.show_status()
            
        elif args.command == 'validate':
            success = installer.validate_config()
            sys.exit(0 if success else 1)
            
    except Exception as e:
        logger.error(f"Operation failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()