#!/usr/bin/env bash

# Golf Cart Journald Configuration Installer
# Installs optimized journald configuration for autonomous vehicle deployment

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
CONFIG_FILE="${SCRIPT_DIR}/journald-golfcart.conf"
SYSTEM_CONFIG_DIR="/etc/systemd/journald.conf.d"
TARGET_CONFIG_FILE="${SYSTEM_CONFIG_DIR}/golfcart.conf"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $*"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $*"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*"
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root to configure systemd journald"
        log_info "Run: sudo $0"
        exit 1
    fi
}

# Backup existing configuration
backup_existing_config() {
    if [[ -f "$TARGET_CONFIG_FILE" ]]; then
        local backup_file="${TARGET_CONFIG_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
        log_info "Backing up existing configuration to: $backup_file"
        cp "$TARGET_CONFIG_FILE" "$backup_file"
    fi
}

# Install journald configuration
install_config() {
    log_info "Installing Golf Cart journald configuration..."
    
    # Create config directory if it doesn't exist
    if [[ ! -d "$SYSTEM_CONFIG_DIR" ]]; then
        log_info "Creating journald config directory: $SYSTEM_CONFIG_DIR"
        mkdir -p "$SYSTEM_CONFIG_DIR"
    fi
    
    # Check if source config exists
    if [[ ! -f "$CONFIG_FILE" ]]; then
        log_error "Source configuration file not found: $CONFIG_FILE"
        exit 1
    fi
    
    # Backup existing config
    backup_existing_config
    
    # Install new configuration
    log_info "Installing configuration to: $TARGET_CONFIG_FILE"
    cp "$CONFIG_FILE" "$TARGET_CONFIG_FILE"
    
    # Set proper permissions
    chmod 644 "$TARGET_CONFIG_FILE"
    chown root:root "$TARGET_CONFIG_FILE"
    
    log_success "Configuration installed successfully"
}

# Validate configuration
validate_config() {
    log_info "Validating journald configuration..."
    
    # Check configuration syntax (systemd will parse and validate)
    if systemd-analyze cat-config systemd/journald.conf &>/dev/null; then
        log_success "Configuration validation passed"
    else
        log_error "Configuration validation failed"
        return 1
    fi
}

# Restart journald service
restart_journald() {
    log_info "Restarting systemd-journald service to apply new configuration..."
    
    # Restart journald
    systemctl restart systemd-journald
    
    # Check if service is running
    if systemctl is-active systemd-journald &>/dev/null; then
        log_success "systemd-journald restarted successfully"
    else
        log_error "Failed to restart systemd-journald"
        return 1
    fi
}

# Show configuration status
show_status() {
    log_info "Current journald configuration status:"
    echo "======================================"
    
    # Show active configuration
    log_info "Active journald configuration:"
    systemctl show systemd-journald -p FragmentPath -p LoadState -p ActiveState -p SubState
    
    echo ""
    log_info "Journal storage information:"
    journalctl --disk-usage 2>/dev/null || log_warning "Could not retrieve disk usage information"
    
    echo ""
    log_info "Recent journal statistics:"
    systemctl status systemd-journald --no-pager -l || true
}

# Uninstall configuration
uninstall_config() {
    log_info "Uninstalling Golf Cart journald configuration..."
    
    if [[ -f "$TARGET_CONFIG_FILE" ]]; then
        # Create backup before removal
        backup_existing_config
        
        # Remove configuration
        rm -f "$TARGET_CONFIG_FILE"
        log_success "Configuration removed"
        
        # Restart journald to apply default configuration
        restart_journald
        
        log_success "Golf Cart journald configuration uninstalled"
    else
        log_warning "Golf Cart journald configuration not found - nothing to uninstall"
    fi
}

# Create storage directories with proper permissions
setup_storage() {
    log_info "Setting up journal storage directories..."
    
    local journal_dir="/var/log/journal"
    
    if [[ ! -d "$journal_dir" ]]; then
        log_info "Creating persistent journal directory: $journal_dir"
        mkdir -p "$journal_dir"
        
        # Set proper permissions for journal directory
        chown root:systemd-journal "$journal_dir"
        chmod 2755 "$journal_dir"
        
        # Create machine-id subdirectory
        local machine_id
        machine_id=$(systemd-machine-id-setup --print 2>/dev/null || cat /etc/machine-id)
        local machine_journal_dir="${journal_dir}/${machine_id}"
        
        if [[ ! -d "$machine_journal_dir" ]]; then
            mkdir -p "$machine_journal_dir"
            chown root:systemd-journal "$machine_journal_dir"
            chmod 2755 "$machine_journal_dir"
        fi
        
        log_success "Journal storage directories created"
    else
        log_info "Journal storage directory already exists"
    fi
}

# Show usage information
usage() {
    echo "Golf Cart Journald Configuration Installer"
    echo "========================================"
    echo ""
    echo "USAGE: sudo $0 <command>"
    echo ""
    echo "COMMANDS:"
    echo "  install           Install Golf Cart journald configuration"
    echo "  uninstall         Remove Golf Cart journald configuration"
    echo "  status            Show current configuration status"
    echo "  validate          Validate configuration without installing"
    echo ""
    echo "EXAMPLES:"
    echo "  sudo $0 install   # Install optimized journald config for Golf Cart"
    echo "  sudo $0 status    # Show current journald status and usage"
    echo "  sudo $0 uninstall # Remove Golf Cart configuration and restore defaults"
}

# Main function
main() {
    # Check root privileges
    check_root
    
    case "${1:-}" in
        install)
            setup_storage
            install_config
            validate_config
            restart_journald
            echo ""
            show_status
            echo ""
            log_success "Golf Cart journald configuration installed successfully"
            log_info "Journal logs are now optimized for autonomous vehicle deployment"
            ;;
        uninstall)
            uninstall_config
            ;;
        status)
            show_status
            ;;
        validate)
            validate_config
            ;;
        help|--help|-h)
            usage
            ;;
        "")
            log_error "No command specified"
            echo ""
            usage
            exit 1
            ;;
        *)
            log_error "Unknown command: $1"
            echo ""
            usage
            exit 1
            ;;
    esac
}

# Execute main function
main "$@"