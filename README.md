# Golf Cart Runtime

Golf Cart Runtime provides a unified command-line interface and systemd service management for the Golf Cart autonomous vehicle platform.

## Overview

The `golfcart_runtime` package simplifies the deployment and management of Golf Cart systems by providing:
- A single `golfcart` command for all system operations
- Systemd service integration for automatic startup and process management
- Web-based system monitoring interface
- Simplified logging and status reporting

## Installation

After building the Golf Cart workspace with colcon, the `golfcart` command will be available in your system PATH.

```bash
# Build the workspace
colcon build --symlink-install

# Source the workspace
source install/setup.bash

# Install the systemd service
golfcart install
```

## Usage

### Command Overview

The `golfcart` command provides the following operations:

| Command | Description |
|---------|-------------|
| `golfcart install` | Install systemd user service for automatic startup |
| `golfcart start` | Start the Golf Cart system |
| `golfcart stop` | Stop the Golf Cart system |
| `golfcart restart` | Restart the Golf Cart system |
| `golfcart status` | Show current system status and recent logs |
| `golfcart monitor` | Open the web-based system monitor in browser |
| `golfcart uninstall` | Remove the systemd service |

### Basic Workflow

1. **Install the service** (one-time setup):
   ```bash
   golfcart install
   ```
   This creates a systemd user service that can manage the Golf Cart launch process.

2. **Start the system**:
   ```bash
   golfcart start
   ```
   This launches the complete Golf Cart stack including sensors, localization, planning, and control.

3. **Monitor the system**:
   ```bash
   # Check status and logs
   golfcart status
   
   # Open web monitor (http://localhost:8080)
   golfcart monitor
   ```

4. **Stop the system**:
   ```bash
   golfcart stop
   ```

### Systemd Service Features

Once installed, the Golf Cart service provides:
- **Automatic startup** at user login (when enabled)
- **Process supervision** with automatic restart on failure
- **Unified logging** through systemd journal
- **Resource management** and proper shutdown handling

### Enable Boot Startup

To have Golf Cart start automatically at system boot (not just user login):

```bash
# Enable user lingering (allows services to run without login)
sudo loginctl enable-linger $USER

# The service will now start at boot
```

### View Logs

The systemd integration provides centralized logging:

```bash
# View recent logs
journalctl --user -u golfcart -n 50

# Follow logs in real-time
journalctl --user -u golfcart -f

# View logs from specific time
journalctl --user -u golfcart --since "10 minutes ago"
```

## Architecture

The runtime package consists of:

- **golfcart CLI**: Main command-line interface (`/usr/bin/golfcart`)
- **Launch Script**: Generated bash script that sources ROS and launches the system
- **Systemd Service**: User service file for process management
- **Python Module**: Core implementation of CLI commands and service management

## Service Management

The systemd service (`golfcart.service`) is installed to `~/.config/systemd/user/` and provides:
- Proper environment setup (ROS sourcing, workspace paths)
- Working directory configuration
- Restart policies and failure handling
- Integration with systemd journal for logging

## Web Monitor

When the system is running, a web-based monitor is available at:
- **URL**: http://localhost:8080/
- **Features**: Real-time system status, sensor data visualization, performance metrics

Access the monitor using:
```bash
golfcart monitor  # Opens in default browser
```

## Troubleshooting

### Service Won't Start
```bash
# Check service status
golfcart status

# View detailed logs
journalctl --user -u golfcart -n 100

# Check if workspace is built
ls -la ~/AutoSDV/install/
```

### Service Not Found
```bash
# Reinstall the service
golfcart install

# Reload systemd daemon
systemctl --user daemon-reload
```

### Permission Issues
```bash
# Ensure launch script is executable
chmod +x <workspace>/scripts/multi_machine/launch_unit_exec.sh

# Check service file permissions
ls -la ~/.config/systemd/user/golfcart.service
```

## Requirements

- ROS 2 Humble
- Ubuntu 22.04 or compatible
- Python 3.10+
- systemd (for service management)
- Built Golf Cart workspace

## License

Part of the Golf Cart project. See main repository for license information.