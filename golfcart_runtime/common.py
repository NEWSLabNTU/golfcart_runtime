"""Common utilities for Golf Cart deployment tools"""

import os
import subprocess
from pathlib import Path
from typing import Optional, Tuple


def get_workspace_dir() -> Path:
    """Get the Golf Cart workspace directory"""
    # Try to find workspace from ROS package share directory
    try:
        result = subprocess.run(
            ['ros2', 'pkg', 'prefix', 'golfcart_runtime'],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            pkg_prefix = Path(result.stdout.strip())
            # Navigate from install/golfcart_runtime to workspace root
            workspace = pkg_prefix.parent.parent
            if (workspace / 'src').exists():
                return workspace
    except:
        pass
    
    # Fallback: try to find from current location
    current = Path.cwd()
    while current != current.parent:
        if (current / 'src' / 'launcher' / 'golfcart_launch').exists():
            return current
        current = current.parent
    
    # Final fallback: use environment variable or default
    # AUTOSDV_WORKSPACE is the pre-rename name, still honoured so an existing
    # deployment keeps working until its environment is updated.
    workspace_env = os.environ.get('GOLFCART_WORKSPACE') or os.environ.get(
        'AUTOSDV_WORKSPACE'
    )
    if workspace_env:
        return Path(workspace_env)
    
    raise RuntimeError("Could not locate Golf Cart workspace directory")


def get_host_role(workspace_dir: Path) -> str:
    """The host role from the config/host marker, or '' when there is none.

    scripts/env.sh and launch_unit_exec.sh both key off this: without a role,
    launch_unit_exec.sh defaults to master, which is right on one machine and
    wrong on the other. The marker is the same file .envrc reads, so a shell and
    a service agree about which machine they are on.
    """
    for name in ('config/host', '.golfcart-host'):
        marker = workspace_dir / name
        if not marker.is_file():
            continue
        for raw in marker.read_text().splitlines():
            token = raw.split('#', 1)[0].split()
            if token:
                return token[0]
    return ''


def get_package_share_dir(package_name: str) -> Path:
    """Get the share directory for a ROS package"""
    try:
        result = subprocess.run(
            ['ros2', 'pkg', 'prefix', package_name],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            return Path(result.stdout.strip()) / 'share' / package_name
    except:
        pass
    
    raise RuntimeError(f"Could not locate package share directory for {package_name}")


def get_current_user() -> str:
    """Get current username"""
    import getpass
    return getpass.getuser()


def run_command(cmd: list, timeout: Optional[int] = None, check: bool = True) -> subprocess.CompletedProcess:
    """Run a command with error handling"""
    try:
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=check
        )
    except subprocess.TimeoutExpired as e:
        raise RuntimeError(f"Command timed out after {timeout}s: {' '.join(cmd)}") from e
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Command failed with exit code {e.returncode}: {' '.join(cmd)}") from e


def check_systemd_service_status(service_name: str) -> Tuple[bool, str]:
    """Check if a systemd user service is active"""
    try:
        result = subprocess.run(
            ['systemctl', '--user', 'is-active', service_name],
            capture_output=True,
            text=True
        )
        status = result.stdout.strip()
        return result.returncode == 0, status
    except:
        return False, "unknown"


def setup_logging():
    """Setup consistent logging for all deployment tools"""
    import logging
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    return logging.getLogger('golfcart_runtime')