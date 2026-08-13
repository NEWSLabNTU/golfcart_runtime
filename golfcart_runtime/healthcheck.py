#!/usr/bin/env python3
"""
Golf Cart System Health Check Script
Performs comprehensive system health monitoring for production deployment
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from .common import get_workspace_dir, get_current_user, run_command, setup_logging

logger = setup_logging()


class GolfCartHealthCheck:
    def __init__(self):
        self.workspace_dir = get_workspace_dir()
        self.username = get_current_user()
        self.log_dir = self.workspace_dir / 'logs/health'
        self.health_log = self.log_dir / f'health-{datetime.now().strftime("%Y%m%d")}.log'
        
        # Create log directory
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def log_health(self, level: str, message: str):
        """Log health message to file and syslog"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_line = f"[{timestamp}] [{level.upper()}] {message}"
        
        # Write to file
        with open(self.health_log, 'a') as f:
            f.write(log_line + '\n')
        
        # Print to stdout
        print(log_line)
        
        # Send to syslog
        try:
            subprocess.run([
                'logger', '-t', 'golfcart-health', 
                '-p', f'daemon.{level.lower()}', message
            ], check=False)
        except:
            pass

    def log_info(self, message: str):
        self.log_health('info', message)

    def log_warn(self, message: str):
        self.log_health('warning', message)

    def log_error(self, message: str):
        self.log_health('error', message)

    def check_ros2_nodes(self):
        """Check ROS2 nodes status"""
        self.log_info("Checking ROS2 nodes status...")
        
        if not shutil.which('ros2'):
            self.log_error("ROS2 command not available")
            return False
        
        # Setup environment
        env = os.environ.copy()
        ros_setup = '/opt/ros/humble/setup.bash'
        workspace_setup = self.workspace_dir / 'install/setup.bash'
        
        if not Path(ros_setup).exists():
            self.log_error("Failed to find ROS2 environment")
            return False
        
        if not workspace_setup.exists():
            self.log_error("Failed to find workspace environment")
            return False
        
        try:
            # Check if daemon is running
            cmd = ['bash', '-c', f'source {ros_setup} && ros2 daemon status']
            result = run_command(cmd, timeout=5, check=False)
            
            if result.returncode != 0:
                self.log_warn("ROS2 daemon not running, attempting to start...")
                start_cmd = ['bash', '-c', f'source {ros_setup} && ros2 daemon start']
                start_result = run_command(start_cmd, timeout=10, check=False)
                if start_result.returncode != 0:
                    self.log_error("Failed to start ROS2 daemon")
                    return False
            
            # Get node list with timeout
            node_cmd = ['bash', '-c', 
                       f'source {ros_setup} && source {workspace_setup} && ros2 node list']
            result = run_command(node_cmd, timeout=10)
            
            node_count = len([line for line in result.stdout.split('\n') if line.strip()])
            self.log_info(f"Active ROS2 nodes: {node_count}")
            
            if node_count < 5:
                self.log_warn(f"Low node count detected ({node_count}) - system may not be fully operational")
                return False
            
            return True
            
        except Exception as e:
            self.log_error(f"Failed to get ROS2 node list: {e}")
            return False

    def check_system_resources(self):
        """Check system resources"""
        self.log_info("Checking system resources...")
        
        try:
            # Memory usage
            with open('/proc/meminfo', 'r') as f:
                meminfo = f.read()
            
            total_mem = None
            available_mem = None
            for line in meminfo.split('\n'):
                if 'MemTotal:' in line:
                    total_mem = int(line.split()[1])
                elif 'MemAvailable:' in line:
                    available_mem = int(line.split()[1])
            
            if total_mem and available_mem:
                mem_usage_percent = ((total_mem - available_mem) / total_mem) * 100
                self.log_info(f"Memory usage: {mem_usage_percent:.1f}%")
                
                if mem_usage_percent > 90:
                    self.log_error(f"Critical memory usage: {mem_usage_percent:.1f}%")
                    return False
                elif mem_usage_percent > 80:
                    self.log_warn(f"High memory usage: {mem_usage_percent:.1f}%")
            
            # Load average
            with open('/proc/loadavg', 'r') as f:
                load_avg = float(f.read().split()[0])
            
            cpu_cores = os.cpu_count()
            self.log_info(f"CPU load (1min): {load_avg} (cores: {cpu_cores})")
            
            if load_avg > cpu_cores * 2:
                self.log_error(f"Critical CPU load: {load_avg} (cores: {cpu_cores})")
                return False
            elif load_avg > cpu_cores:
                self.log_warn(f"High CPU load: {load_avg} (cores: {cpu_cores})")
            
            # Disk usage
            total, used, free = shutil.disk_usage(self.workspace_dir)
            disk_usage_percent = (used / total) * 100
            self.log_info(f"Disk usage (workspace): {disk_usage_percent:.1f}%")
            
            if disk_usage_percent > 90:
                self.log_error(f"Critical disk usage: {disk_usage_percent:.1f}%")
                return False
            elif disk_usage_percent > 80:
                self.log_warn(f"High disk usage: {disk_usage_percent:.1f}%")
            
            return True
            
        except Exception as e:
            self.log_error(f"Error getting system resources: {e}")
            return False

    def check_hardware_interfaces(self):
        """Check hardware interfaces"""
        self.log_info("Checking hardware interfaces...")
        
        issues = 0
        
        # Check USB devices
        try:
            result = run_command(['lsusb'], check=False)
            if result.returncode == 0:
                usb_count = len(result.stdout.strip().split('\n'))
                self.log_info(f"USB devices detected: {usb_count}")
        except:
            pass
        
        # Check serial devices
        tty_count = 0
        usb_serial = list(Path('/dev').glob('ttyUSB*'))
        acm_serial = list(Path('/dev').glob('ttyACM*'))
        
        tty_count = len(usb_serial) + len(acm_serial)
        if usb_serial:
            self.log_info(f"USB serial devices: {len(usb_serial)}")
        if acm_serial:
            self.log_info(f"ACM serial devices: {len(acm_serial)}")
        
        if tty_count == 0:
            self.log_warn("No serial devices found - GPS/IMU may not be connected")
            issues += 1
        
        # Check network interfaces
        try:
            result = run_command(['ip', 'link', 'show'], check=False)
            if result.returncode == 0:
                net_interfaces = result.stdout.count('state UP')
                self.log_info(f"Active network interfaces: {net_interfaces}")
                
                if net_interfaces == 0:
                    self.log_error("No active network interfaces")
                    issues += 1
        except:
            issues += 1
        
        # Check sensor network connectivity
        sensor_ips = ['192.168.1.201', '192.168.3.10']
        for sensor_ip in sensor_ips:
            try:
                result = run_command(['ping', '-c', '1', '-W', '2', sensor_ip], check=False)
                if result.returncode == 0:
                    self.log_info(f"Sensor network reachable: {sensor_ip}")
                else:
                    self.log_warn(f"Sensor network unreachable: {sensor_ip}")
            except:
                pass
        
        return issues == 0

    def check_log_health(self):
        """Check log file health"""
        self.log_info("Checking log file health...")
        
        issues = 0
        
        # Check log directory size
        try:
            log_size_mb = sum(f.stat().st_size for f in (self.workspace_dir / 'logs').rglob('*') if f.is_file()) // (1024 * 1024)
            self.log_info(f"Log directory size: {log_size_mb}MB")
            
            if log_size_mb > 1000:
                self.log_warn(f"Large log directory size: {log_size_mb}MB - consider cleanup")
                issues += 1
        except:
            pass
        
        # Check for recent ROS log errors
        launch_log_dir = self.workspace_dir / 'logs/launch'
        if launch_log_dir.exists():
            try:
                recent_errors = 0
                current_time = time.time()
                day_ago = current_time - (24 * 60 * 60)
                
                for log_file in launch_log_dir.glob('*.log'):
                    if log_file.stat().st_mtime > day_ago:
                        try:
                            with open(log_file, 'r') as f:
                                content = f.read()
                                if 'ERROR' in content or 'FATAL' in content:
                                    recent_errors += 1
                        except:
                            pass
                
                self.log_info(f"Recent log files with errors: {recent_errors}")
                
                if recent_errors > 5:
                    self.log_warn(f"High number of error logs detected: {recent_errors}")
                    issues += 1
            except:
                pass
        
        return issues == 0

    def check_golfcart_service_status(self):
        """Check Golf Cart service status"""
        self.log_info("Checking Golf Cart service status...")
        
        service_name = f"golfcart@{self.username}"
        
        try:
            # Check systemd service status
            result = run_command(['systemctl', '--user', 'is-active', service_name], check=False)
            service_status = result.stdout.strip()
            
            self.log_info(f"SystemD service status: {service_status}")
            
            if service_status != 'active':
                self.log_error(f"Golf Cart service not active: {service_status}")
                return False
            
            # Check service runtime
            try:
                result = run_command([
                    'systemctl', '--user', 'show', service_name,
                    '--property=ActiveEnterTimestamp', '--value'
                ], check=False)
                if result.returncode == 0 and result.stdout.strip():
                    self.log_info(f"Service active since: {result.stdout.strip()}")
            except:
                pass
            
        except Exception as e:
            # Check for running processes as fallback
            pid_file = self.workspace_dir / 'logs/launch/golfcart.pid'
            if pid_file.exists():
                try:
                    with open(pid_file, 'r') as f:
                        pid = int(f.read().strip())
                    
                    # Check if process is running
                    try:
                        os.kill(pid, 0)
                        self.log_info(f"Golf Cart process running with PID: {pid}")
                        return True
                    except ProcessLookupError:
                        self.log_error("Golf Cart PID file exists but process not running")
                        return False
                except:
                    self.log_error("Could not read Golf Cart PID file")
                    return False
            else:
                self.log_warn("Golf Cart not running (no PID file or service)")
                return False
        
        return True

    def run_health_check(self):
        """Run comprehensive health check"""
        overall_status = 0
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        self.log_info(f"=== Golf Cart Health Check Started at {timestamp} ===")
        
        # Define health checks
        checks = [
            ('check_golfcart_service_status', 'Golf Cart Service'),
            ('check_ros2_nodes', 'ROS2 Nodes'),
            ('check_system_resources', 'System Resources'),
            ('check_hardware_interfaces', 'Hardware Interfaces'),
            ('check_log_health', 'Log Health')
        ]
        
        for check_method, check_name in checks:
            self.log_info(f"Running check: {check_name}")
            
            try:
                method = getattr(self, check_method)
                if method():
                    self.log_info(f"✓ {check_name}: PASS")
                else:
                    self.log_error(f"✗ {check_name}: FAIL")
                    overall_status += 1
            except Exception as e:
                self.log_error(f"✗ {check_name}: ERROR - {e}")
                overall_status += 1
            
            print("---")
        
        # Summary
        if overall_status == 0:
            self.log_info("=== Overall Health Status: HEALTHY ===")
        else:
            self.log_error(f"=== Overall Health Status: ISSUES DETECTED ({overall_status} checks failed) ===")
        
        self.log_info("=== Health Check Completed ===")
        
        return overall_status == 0


def main():
    """Main entry point for golfcart-healthcheck command"""
    parser = argparse.ArgumentParser(description='Golf Cart System Health Check')
    
    args = parser.parse_args()
    
    try:
        health_check = GolfCartHealthCheck()
        success = health_check.run_health_check()
        sys.exit(0 if success else 1)
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        logger.exception("Full traceback:")
        sys.exit(1)


if __name__ == '__main__':
    main()