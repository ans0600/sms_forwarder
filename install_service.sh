#!/bin/bash
# Installation script for SMS Forwarder systemd service

set -e

echo "=========================================="
echo "SMS Forwarder Service Installation"
echo "=========================================="

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Error: This script must be run as root (use sudo)"
    exit 1
fi

# Get the actual user (not root when using sudo)
ACTUAL_USER=${SUDO_USER:-$USER}
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo ""
echo "Installation directory: $SCRIPT_DIR"
echo "Running as user: $ACTUAL_USER"
echo ""

# Step 1: Install systemd service file with user customization
echo "1. Installing systemd service file..."

# Detect Python path (prefer pyenv if available, otherwise system python3)
if command -v pyenv &> /dev/null && [ -f "$HOME/.pyenv/shims/python3" ]; then
    PYTHON_PATH="$HOME/.pyenv/shims/python3"
elif [ -f "/home/$ACTUAL_USER/.pyenv/shims/python3" ]; then
    PYTHON_PATH="/home/$ACTUAL_USER/.pyenv/shims/python3"
else
    PYTHON_PATH=$(which python3)
fi

# Create customized service file
sed -e "s|YOUR_USERNAME|$ACTUAL_USER|g" \
    -e "s|/path/to/sms_forwarder|$SCRIPT_DIR|g" \
    -e "s|/usr/bin/python3|$PYTHON_PATH|g" \
    "$SCRIPT_DIR/sms-forwarder.service" > /etc/systemd/system/sms-forwarder.service

chmod 644 /etc/systemd/system/sms-forwarder.service
echo "   ✓ Service file installed and customized for user: $ACTUAL_USER"
echo "   ✓ Working directory: $SCRIPT_DIR"
echo "   ✓ Python path: $PYTHON_PATH"

# Step 2: Install logrotate configuration with customization
echo "2. Installing logrotate configuration..."

# Create customized logrotate file
sed -e "s|YOUR_USERNAME|$ACTUAL_USER|g" \
    -e "s|/path/to/sms_forwarder|$SCRIPT_DIR|g" \
    "$SCRIPT_DIR/sms-forwarder.logrotate.template" > /etc/logrotate.d/sms-forwarder

chmod 644 /etc/logrotate.d/sms-forwarder
echo "   ✓ Logrotate config installed and customized"

# Step 3: Ensure user is in dialout group
echo "3. Checking user permissions..."
if groups $ACTUAL_USER | grep -q dialout; then
    echo "   ✓ User $ACTUAL_USER already in dialout group"
else
    echo "   Adding user $ACTUAL_USER to dialout group..."
    usermod -a -G dialout $ACTUAL_USER
    echo "   ✓ User added to dialout group (logout/login required)"
fi

# Step 4: Create log file with proper permissions
echo "4. Creating log file..."
touch "$SCRIPT_DIR/sms_forwarder.log"
chown $ACTUAL_USER:dialout "$SCRIPT_DIR/sms_forwarder.log"
chmod 644 "$SCRIPT_DIR/sms_forwarder.log"
echo "   ✓ Log file created"

# Step 5: Reload systemd
echo "5. Reloading systemd daemon..."
systemctl daemon-reload
echo "   ✓ Systemd reloaded"

# Step 6: Enable service to start on boot
echo "6. Enabling service to start on boot..."
systemctl enable sms-forwarder
echo "   ✓ Service enabled"

# Step 7: Start the service
echo "7. Starting SMS forwarder service..."
systemctl start sms-forwarder
sleep 2
echo "   ✓ Service started"

# Step 8: Check service status
echo "8. Checking service status..."
if systemctl is-active --quiet sms-forwarder; then
    echo "   ✓ Service is running"
else
    echo "   ✗ Service failed to start"
    echo ""
    echo "Check logs with:"
    echo "   sudo journalctl -u sms-forwarder -n 50"
    exit 1
fi

echo ""
echo "=========================================="
echo "Installation Complete!"
echo "=========================================="
echo ""
echo "✓ Service installed and running"
echo "✓ Auto-start on boot enabled"
echo "✓ Log rotation configured (daily, 7 days retention)"
echo ""
echo "Useful commands:"
echo ""
echo "  View live logs:"
echo "    sudo journalctl -u sms-forwarder -f"
echo "    tail -f $SCRIPT_DIR/sms_forwarder.log"
echo ""
echo "  Service status:"
echo "    sudo systemctl status sms-forwarder"
echo ""
echo "  Restart service:"
echo "    sudo systemctl restart sms-forwarder"
echo ""
echo "  Stop service:"
echo "    sudo systemctl stop sms-forwarder"
echo ""
echo "  Disable auto-start:"
echo "    sudo systemctl disable sms-forwarder"
echo ""
echo "=========================================="
