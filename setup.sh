#!/bin/bash
# Setup script for SMS Forwarder

echo "==================================="
echo "SMS Forwarder Setup Script"
echo "==================================="
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo "Please do NOT run this script as root/sudo"
    exit 1
fi

# Add user to dialout group
echo "1. Adding user to dialout group..."
sudo usermod -a -G dialout $USER
echo "   ✓ User added to dialout group"
echo "   NOTE: You need to LOGOUT and LOGIN again for this to take effect!"
echo ""

# Install system dependencies
echo "2. Installing system dependencies..."
sudo apt-get update
sudo apt-get install -y python3-pip gammu libgammu-dev python3-gammu
echo "   ✓ System dependencies installed"
echo ""

# Install Python dependencies
echo "3. Installing Python dependencies..."
pip3 install --user python-gammu requests
echo "   ✓ Python dependencies installed"
echo ""

# Check device ports
echo "4. Checking connected devices..."
echo ""
echo "Available ACM ports:"
ls -l /dev/ttyACM* 2>/dev/null || echo "   No ACM devices found"
echo ""

echo "USB devices with vendor ID 19d1 (Air 780EPV):"
lsusb | grep "19d1" || echo "   No Air 780EPV devices found"
echo ""

# Test permissions
echo "5. Testing port permissions..."
if [ -e "/dev/ttyACM0" ]; then
    if [ -r "/dev/ttyACM0" ] && [ -w "/dev/ttyACM0" ]; then
        echo "   ✓ /dev/ttyACM0 is accessible"
    else
        echo "   ✗ /dev/ttyACM0 is not accessible"
        echo "   Run: sudo chmod 666 /dev/ttyACM0 (temporary fix)"
        echo "   OR logout/login after adding to dialout group (permanent fix)"
    fi
else
    echo "   ⚠ /dev/ttyACM0 does not exist"
fi
echo ""

echo "==================================="
echo "Setup Complete!"
echo "==================================="
echo ""
echo "Next steps:"
echo "1. LOGOUT and LOGIN again (for dialout group to take effect)"
echo "2. Edit config.py with your Telegram credentials"
echo "3. Run: python3 main.py"
echo ""
