#!/usr/bin/env python3
"""
Golf Cart Production Launch Script
Designed for robust deployment with comprehensive logging and monitoring
"""

import argparse
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

from .common import get_workspace_dir, setup_logging

logger = setup_logging()


class GolfCartLauncher:
    def __init__(self):
        self.workspace_dir = get_workspace_dir()
        self.log_dir = self.workspace_dir / 'logs/launch'
        self.pid_file = self.log_dir / 'golfcart.pid'
        self.config_file = self.workspace_dir / 'config/launch.conf'
        
        # Default configuration
        self.config = {
            'MAX_RESTART_ATTEMPTS': 5,
            'RESTART_DELAY': 10,
            'HEALTH_CHECK_INTERVAL': 30,
            'LOG_LEVEL': 'INFO',
            'ENABLE_SYSTEMD_LOGGING': 'true',
            'SYSTEMD_MODE': os.environ.get('SYSTEMD_MODE', 'false')
        }
        
        # Load configuration
        self.load_config()
        
        # Create log directory
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

    def load_config(self):
        """Load configuration from launch.conf file"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            self.config[key.strip()] = value.strip()
            except Exception as e:
                logger.warning(f"Failed to load config from {self.config_file}: {e}")

    def log_info(self, message: str):
        """Log info message"""
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        log_msg = f"[{timestamp}] [INFO] {message}"
        print(log_msg)
        
        if self.config['ENABLE_SYSTEMD_LOGGING'] == 'true':
            try:
                subprocess.run(['logger', '-t', 'golfcart-launch', '-p', 'info', message], check=False)
            except:
                pass

    def log_error(self, message: str):
        """Log error message"""
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        log_msg = f"[{timestamp}] [ERROR] {message}"
        print(log_msg, file=sys.stderr)
        
        if self.config['ENABLE_SYSTEMD_LOGGING'] == 'true':
            try:
                subprocess.run(['logger', '-t', 'golfcart-launch', '-p', 'error', message], check=False)
            except:
                pass

    def check_system_health(self):
        """Perform basic system health checks"""
        issues = 0
        
        # Check ROS2 environment
        if not shutil.which('ros2'):
            self.log_error("ROS2 command not found in PATH")
            issues += 1
        
        # Check workspace build status
        setup_bash = self.workspace_dir / 'install/setup.bash'
        if not setup_bash.exists():
            self.log_error("Workspace not built - missing install/setup.bash")
            issues += 1
        
        return issues == 0

    def launch_golfcart_core(self):
        """Launch the core Golf Cart system"""
        os.chdir(self.workspace_dir)
        
        self.log_info(f"Starting Golf Cart system from workspace: {self.workspace_dir}")
        
        # Set environment
        env = os.environ.copy()
        env.update({
            'RCUTILS_COLORIZED_OUTPUT': '1',
            'RCUTILS_LOGGING_USE_STDOUT': '1',
            'ROS_LOG_DIR': str(self.log_dir)
        })
        
        # Source ROS2 environment
        ros_setup = Path('/opt/ros/humble/setup.bash')
        if not ros_setup.exists():
            self.log_error("ROS2 Humble not found at /opt/ros/humble/setup.bash")
            return False
        
        workspace_setup = self.workspace_dir / 'install/setup.bash'
        if not workspace_setup.exists():
            self.log_error("Workspace setup not found at install/setup.bash")
            return False
        
        # System health check
        if not self.check_system_health():
            self.log_error("System health check failed")
            return False
        
        self.log_info("System monitor available at http://localhost:8080/")
        self.log_info("Starting ROS2 launch process...")
        
        # Prepare launch command
        cmd = [
            'bash', '-c', 
            f'source {ros_setup} && source {workspace_setup} && '
            'ros2 launch golfcart_launch golfcart.launch.yaml'
        ]
        
        try:
            # Launch process
            process = subprocess.Popen(cmd, env=env)
            
            # Save PID
            with open(self.pid_file, 'w') as f:
                f.write(str(process.pid))
            
            self.log_info(f"Golf Cart launched with PID: {process.pid}")
            
            # Wait for process
            exit_code = process.wait()
            self.log_info(f"Golf Cart process exited with code: {exit_code}")
            
            return exit_code == 0
            
        except Exception as e:
            self.log_error(f"Failed to launch Golf Cart: {e}")
            return False
        finally:
            # Clean up PID file
            if self.pid_file.exists():
                self.pid_file.unlink()

    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.log_info(f"Received signal {signum}, shutting down...")
        self.cleanup()
        sys.exit(0)

    def cleanup(self):
        """Clean up on exit"""
        if self.pid_file.exists():
            try:
                with open(self.pid_file, 'r') as f:
                    pid = int(f.read().strip())
                
                # Try to terminate gracefully
                try:
                    os.kill(pid, signal.SIGTERM)
                    time.sleep(5)
                    os.kill(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                    
            except Exception as e:
                self.log_error(f"Error during cleanup: {e}")
            finally:
                self.pid_file.unlink()

    def run(self):
        """Main run method"""
        self.log_info("Golf Cart Production Launch Script started")
        self.log_info(f"Configuration: MAX_RESTART_ATTEMPTS={self.config['MAX_RESTART_ATTEMPTS']}, "
                     f"RESTART_DELAY={self.config['RESTART_DELAY']}s")
        
        # Check if already running
        if self.pid_file.exists():
            try:
                with open(self.pid_file, 'r') as f:
                    existing_pid = int(f.read().strip())
                
                # Check if process is still running
                try:
                    os.kill(existing_pid, 0)
                    self.log_error(f"Golf Cart is already running with PID: {existing_pid}")
                    return False
                except ProcessLookupError:
                    self.log_info("Stale PID file found, removing...")
                    self.pid_file.unlink()
            except Exception:
                self.pid_file.unlink()
        
        # Launch the system
        success = self.launch_golfcart_core()
        
        if success:
            self.log_info("Golf Cart system completed successfully")
        else:
            self.log_error("Golf Cart system failed")
        
        return success


def main():
    """Main entry point for golfcart-launch command"""
    parser = argparse.ArgumentParser(description='Golf Cart Production Launch Script')
    parser.add_argument('--config', help='Configuration file path')
    
    args = parser.parse_args()
    
    try:
        launcher = GolfCartLauncher()
        
        if args.config:
            launcher.config_file = Path(args.config)
            launcher.load_config()
        
        success = launcher.run()
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        logger.info("Launch interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Launch failed: {e}")
        logger.exception("Full traceback:")
        sys.exit(1)


if __name__ == '__main__':
    main()