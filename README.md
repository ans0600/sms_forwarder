# SMS Forwarder for Air 780EPV Devices

A Python application that monitors Air 780EPV LTE modems for incoming SMS and phone calls, forwarding notifications to Telegram in real-time using direct AT commands.

## Features

- 📱 **SMS Forwarding**: Automatically forwards incoming SMS to Telegram
- 📞 **Call Notifications**: Real-time incoming call alerts
- 🔄 **Multi-Device Support**: Monitor multiple Air 780EPV devices simultaneously
- ⚡ **Real-Time Detection**: Dedicated threads for instant call notifications (100ms response)
- 🔧 **Direct AT Commands**: No Gammu dependency, uses pure AT commands for reliability
- 🌍 **UCS2 Support**: Handles international SMS with UCS2 encoding
- 🔒 **Auto-Delete**: Optional SMS deletion after forwarding
- 📊 **Device Monitoring**: Signal strength and device status reporting
- 🐧 **Linux Service**: Systemd integration with auto-start and log rotation

## Project Structure

```
sms_forwarder/
├── main.py                    # Application entry point
├── config.py.example          # Example configuration (copy to config.py)
├── sms_device_at.py           # AT command device handler
├── sms_forwarder_at.py        # Main forwarder logic with threading
├── telegram_notifier.py       # Telegram notification handler
├── requirements.txt           # Python dependencies
├── sms-forwarder.service      # Systemd service file
├── install_service.sh         # Automatic service installation
├── .gitignore                 # Git ignore rules
└── script/                    # Utility and test scripts
    ├── test_incoming_call.py  # Test incoming call detection
    ├── read_single_sms.py     # Debug SMS reading
    └── ...
```

## Prerequisites

### Hardware
- 1-2x Air 780EPV LTE modems
- USB cables
- SIM cards with SMS capability

### Software
- Python 3.7+
- Linux (tested on Ubuntu 22.04+)
- Serial port access (dialout group membership)

## Quick Start

### 1. Clone and Setup

```bash
git clone <your-repo-url>
cd sms_forwarder

# Copy example config
cp config.py.example config.py

# Install dependencies
pip3 install -r requirements.txt
```

### 2. Configure Telegram

1. Create a bot:
   - Open Telegram, search for `@BotFather`
   - Send `/newbot` and follow instructions
   - Save the bot token

2. Get your Chat ID:
   - Search for `@userinfobot` on Telegram
   - Send any message to get your chat ID

3. Update `config.py`:
```python
TELEGRAM_BOT_TOKEN = 'your_bot_token_here'
TELEGRAM_CHAT_ID = 'your_chat_id_here'
```

### 3. Configure Devices

Find your device ports (Air 780EPV uses ttyACM*):
```bash
ls -l /dev/ttyACM*
```

Update `config.py`:
```python
DEVICES = [
    {
        'name': 'Air780EPV-1',
        'port': '/dev/ttyACM0'  # AT command port (port 0)
    }
]
```

**Note**: Air 780EPV creates 3 ports per device:
- `ttyACM0` (or ttyACM3, etc.): AT command port - **use this**
- `ttyACM1`: PPP/Modem port
- `ttyACM2`: Debug port

### 4. Set Permissions

```bash
# Add your user to dialout group
sudo usermod -a -G dialout $USER

# Logout and login for changes to take effect
```

### 5. Run

```bash
# Test run
python3 main.py

# Or install as service
sudo ./install_service.sh
```

## Running as a Service

The easiest way to install and run as a system service:

```bash
sudo ./install_service.sh
```

This script will:
- Install systemd service file
- Set up log rotation (daily, 7 days retention)
- Add user to dialout group
- Enable and start the service

### Manual Service Commands

```bash
# Start service
sudo systemctl start sms-forwarder

# Stop service
sudo systemctl stop sms-forwarder

# Restart service
sudo systemctl restart sms-forwarder

# Check status
sudo systemctl status sms-forwarder

# View logs
sudo journalctl -u sms-forwarder -f
tail -f sms_forwarder.log
```

## Configuration

All settings in `config.py`:

| Setting | Description | Default |
|---------|-------------|---------|
| `TELEGRAM_BOT_TOKEN` | Telegram bot token | Required |
| `TELEGRAM_CHAT_ID` | Telegram chat ID | Required |
| `DEVICES` | List of device configurations | Required |
| `POLL_INTERVAL` | SMS check interval (seconds) | 10 |
| `DELETE_AFTER_FORWARD` | Delete SMS after forwarding | True |
| `LOG_LEVEL` | Logging level | INFO |
| `LOG_FILE` | Log file path | sms_forwarder.log |

## Message Formats

### SMS Notification
```
📱 New SMS Received

Device: Air780EPV-1
From: +61412345678
Date: 2025-10-25 15:30:45

Message:
Hello, this is a test!
```

### Call Notification
```
📞 Incoming Call

Device: Air780EPV-1
From: +61412345678
Status: Incoming
Type: Voice
Time: 2025-10-25 15:32:10
```

## How It Works

### Architecture

```
Device Monitor Thread (per device):
├─ Every 100ms: Check serial buffer for RING
├─ Every 10s: Check for new SMS via AT+CMGL
└─ Single serial connection (no conflicts)

Call detected → AT+CLCC → Parse → Telegram
SMS detected → AT+CMGR → Decode UCS2 → Telegram → AT+CMGD (optional)
```

### Key Technologies

- **Direct AT Commands**: No Gammu, pure serial communication
- **UCS2 Decoding**: Handles international SMS (smspdudecoder library)
- **Threading**: One monitor thread per device for real-time responsiveness
- **PDU Fallback**: Supports both text mode and PDU mode SMS

## Troubleshooting

### Device Not Detected

```bash
# Check USB connection
lsusb | grep 19d1

# Check ports
ls -l /dev/ttyACM*

# Check permissions
groups  # Should show 'dialout'
```

### Permission Denied

```bash
# Temporary fix
sudo chmod 666 /dev/ttyACM0

# Permanent fix
sudo usermod -a -G dialout $USER
# Then logout/login
```

### SMS Not Received

1. Check device signal: Look for "Signal:" in startup notification
2. Verify SIM card is inserted and active
3. Test: Send SMS to the SIM number
4. Check logs: `tail -f sms_forwarder.log`
5. Ensure phone is sending SMS (not RCS)

### Multiple Call Notifications

Fixed in latest version - uses call state tracking to send only one notification per call.

### Serial Port Conflicts

The app uses one thread per device with a single serial connection. If you see "Failed to set text mode" errors, ensure no other program is using the port.

## Testing Scripts

```bash
# Test incoming call detection
python3 script/test_incoming_call.py /dev/ttyACM0

# Read a specific SMS
python3 script/read_single_sms.py /dev/ttyACM0 0

# Test UCS2 decoding
python3 script/test_ucs2_fix.py
```

## Development

### Dependencies

- `pyserial>=3.5` - Serial port communication
- `smspdudecoder>=2.2.0` - UCS2/PDU SMS decoding
- `requests>=2.31.0` - Telegram API
- `urllib3>=2.0.0` - HTTP library

### Adding Features

The modular design makes it easy to extend:

- Add new notification channels: Modify `telegram_notifier.py`
- Custom SMS processing: Edit `process_device_sms()` in `sms_forwarder_at.py`
- Additional AT commands: Extend `sms_device_at.py`

## License

Open source - free for personal and educational use.

## Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Test thoroughly
4. Submit a pull request

## Acknowledgments

- Air 780EPV AT Command Reference: https://docs.openluat.com/air780ep/at/
- smspdudecoder library for UCS2 handling
- Telegram Bot API

## Support

For issues:

1. Check logs: `tail -f sms_forwarder.log`
2. Review this README's troubleshooting section
3. Open an issue on GitHub with logs and details
