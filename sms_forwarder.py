"""
Main SMS forwarder application logic
"""

import logging
import time
from typing import List, Dict
from datetime import datetime

from telegram_notifier import TelegramNotifier
from sms_device import SMSDevice


logger = logging.getLogger(__name__)


class SMSForwarder:
    """Main SMS forwarding application"""

    def __init__(self, telegram_token: str, telegram_chat_id: str,
                 devices: List[Dict], poll_interval: int = 10,
                 delete_after_forward: bool = True):
        """
        Initialize SMS forwarder

        Args:
            telegram_token: Telegram bot token
            telegram_chat_id: Telegram chat ID
            devices: List of device configurations
            poll_interval: Polling interval in seconds (default: 10)
            delete_after_forward: Delete SMS after forwarding (default: True)
        """
        self.telegram = TelegramNotifier(telegram_token, telegram_chat_id)
        self.devices = []
        self.poll_interval = poll_interval
        self.delete_after_forward = delete_after_forward
        self.running = False

        # Initialize devices
        for dev_config in devices:
            device = SMSDevice(
                device_name=dev_config['name'],
                device_port=dev_config['port'],
                device_connection=dev_config.get('connection', 'at')
            )
            self.devices.append(device)

    def connect_all_devices(self) -> Dict:
        """
        Connect to all configured devices

        Returns:
            Dictionary with connection results and device info
        """
        results = {
            'connected': [],
            'failed': [],
            'device_info': {}
        }

        for device in self.devices:
            if not device.connect():
                logger.warning(f"Failed to connect to {device.device_name}")
                results['failed'].append({
                    'name': device.device_name,
                    'port': device.device_port,
                    'reason': 'Device not found or connection failed'
                })
            else:
                # Get device info
                info = device.get_device_info()
                signal = device.get_signal_strength()
                sim_info = device.get_sim_info()

                device_data = {
                    'name': device.device_name,
                    'port': device.device_port,
                    'manufacturer': info.get('manufacturer', 'Unknown') if info else 'Unknown',
                    'model': info.get('model', 'Unknown') if info else 'Unknown',
                    'imei': info.get('imei', 'Unknown') if info else 'Unknown',
                    'signal': signal if signal is not None else 'N/A',
                    'sim_imsi': sim_info.get('imsi', 'Unknown') if sim_info else 'Unknown',
                    'sim_operator': sim_info.get('operator', 'Unknown') if sim_info else 'Unknown'
                }

                results['connected'].append(device_data)
                results['device_info'][device.device_name] = device_data

                logger.info(f"Device {device.device_name}: {device_data['manufacturer']} "
                           f"{device_data['model']} (IMEI: {device_data['imei']})")
                logger.info(f"Signal strength for {device.device_name}: {device_data['signal']}%")
                if sim_info:
                    logger.info(f"SIM card for {device.device_name}: {device_data['sim_operator']} "
                               f"(IMSI: {device_data['sim_imsi']})")

        return results

    def disconnect_all_devices(self):
        """Disconnect from all devices"""
        for device in self.devices:
            device.disconnect()

    def format_sms_message(self, sms: Dict) -> str:
        """
        Format SMS for Telegram message

        Args:
            sms: SMS message dictionary

        Returns:
            Formatted message string
        """
        timestamp = sms['date'].strftime('%Y-%m-%d %H:%M:%S')
        message = f"""📱 <b>New SMS Received</b>

<b>Device:</b> {sms['device']}
<b>From:</b> {sms['number']}
<b>Date:</b> {timestamp}

<b>Message:</b>
{sms['text']}"""
        return message

    def process_device_sms(self, device: SMSDevice):
        """
        Process SMS from a single device with timeout protection

        Args:
            device: SMSDevice instance to process
        """
        import signal

        def timeout_handler(signum, frame):
            raise TimeoutError(f"Device {device.device_name} timed out")

        try:
            # Set a 30-second timeout for processing this device
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(30)

            messages = device.read_sms()

            if messages:
                logger.info(f"Found {len(messages)} new message(s) from {device.device_name}")

            for sms in messages:
                try:
                    # Format and send to Telegram
                    telegram_message = self.format_sms_message(sms)

                    if self.telegram.send_message(telegram_message):
                        logger.info(f"Forwarded SMS from {sms['number']} via {sms['device']}")

                        # Delete SMS if configured (this prevents duplicates)
                        if self.delete_after_forward:
                            if not device.delete_sms(sms['location'], sms['folder']):
                                # If deletion failed, log it but don't retry
                                logger.warning(f"Failed to delete SMS {sms['sms_id']}, may be forwarded again next cycle")

                                # Check if deletion was disabled
                                if device.deletion_disabled:
                                    error_msg = (f"⚠️ <b>Deletion Disabled for {device.device_name}</b>\n\n"
                                                f"Automatic SMS deletion has been disabled due to repeated errors. "
                                                f"SMS will still be forwarded but not deleted.\n\n"
                                                f"This prevents device crashes from corrupted data.\n\n"
                                                f"To clear SMS manually:\n"
                                                f"<code>sudo python3 clear_sms.py {device.device_port}</code>")
                                    self.telegram.send_message(error_msg)
                    else:
                        logger.warning(f"Failed to forward SMS from {sms['device']}")
                        # Don't delete if forward failed - will retry next cycle

                except Exception as e:
                    logger.error(f"Error processing individual SMS: {e}")
                    continue

            # Cancel the timeout
            signal.alarm(0)

        except TimeoutError as e:
            logger.error(f"Timeout processing {device.device_name}: {e}")
            # Try to reconnect
            logger.info(f"Attempting to reconnect to {device.device_name}...")
            device.disconnect()
            time.sleep(2)
            device.connect()
        except Exception as e:
            logger.error(f"Error processing SMS from {device.device_name}: {e}")
        finally:
            # Always cancel alarm
            signal.alarm(0)

    def poll_devices(self):
        """Poll all devices for new SMS"""
        logger.info("Starting SMS polling loop...")

        while self.running:
            for device in self.devices:
                # Only process devices that are connected
                if device.state_machine is not None:
                    self.process_device_sms(device)

            time.sleep(self.poll_interval)

    def send_startup_notification(self, connection_results: Dict):
        """
        Send startup notification to Telegram with device details

        Args:
            connection_results: Results from connect_all_devices()
        """
        # Build connected devices section
        connected_section = ""
        if connection_results['connected']:
            for dev in connection_results['connected']:
                signal_str = f"{dev['signal']}%" if isinstance(dev['signal'], int) else dev['signal']
                connected_section += f"""
<b>✅ {dev['name']}</b>
  • Port: {dev['port']}
  • Model: {dev['manufacturer']} {dev['model']}
  • IMEI: {dev['imei']}
  • Signal: {signal_str}
  • SIM Operator: {dev['sim_operator']}
  • SIM IMSI: {dev['sim_imsi']}
"""

        # Build failed devices section
        failed_section = ""
        if connection_results['failed']:
            for dev in connection_results['failed']:
                failed_section += f"""
<b>❌ {dev['name']}</b>
  • Port: {dev['port']}
  • Status: {dev['reason']}
"""

        # Build status message
        if connection_results['connected']:
            status = f"✅ {len(connection_results['connected'])} device(s) connected"
            if connection_results['failed']:
                status += f"\n⚠️ {len(connection_results['failed'])} device(s) failed"
        else:
            status = "❌ No devices connected"

        message = f"""🚀 <b>SMS Forwarder Started</b>

<b>Configuration:</b>
  • Poll Interval: {self.poll_interval} seconds
  • Delete After Forward: {'Yes' if self.delete_after_forward else 'No'}

<b>Status:</b> {status}
{connected_section}{failed_section}
<b>Monitoring for incoming SMS...</b>"""

        self.telegram.send_message(message)

    def send_shutdown_notification(self):
        """Send shutdown notification to Telegram"""
        message = "🛑 <b>SMS Forwarder Stopped</b>"
        self.telegram.send_message(message)

    def send_error_notification(self, error_message: str):
        """
        Send error notification to Telegram

        Args:
            error_message: Error message to send
        """
        message = f"""⚠️ <b>SMS Forwarder Error</b>

{error_message}"""
        self.telegram.send_message(message)

    def start(self):
        """Start the SMS forwarder"""
        logger.info("Starting SMS Forwarder...")

        # Test Telegram connection first
        if not self.telegram.test_connection():
            logger.error("Failed to connect to Telegram. Please check your bot token and chat ID.")
            return

        # Connect to all devices
        connection_results = self.connect_all_devices()

        # Send startup notification with device info
        self.send_startup_notification(connection_results)

        # Check if at least one device is connected
        if not connection_results['connected']:
            error_msg = "No devices connected. Cannot start SMS monitoring."
            logger.error(error_msg)
            logger.info("Please check your device connections and try again.")
            return

        # Warn if some devices failed
        if connection_results['failed']:
            logger.warning(f"{len(connection_results['failed'])} device(s) failed to connect, "
                          f"but continuing with {len(connection_results['connected'])} device(s)")

        # Start polling
        self.running = True
        try:
            self.poll_devices()
        except KeyboardInterrupt:
            logger.info("Received shutdown signal (Ctrl+C)")
        except Exception as e:
            error_msg = f"Unexpected error in polling loop: {e}"
            logger.error(error_msg)
            self.send_error_notification(error_msg)
        finally:
            self.stop()

    def stop(self):
        """Stop the SMS forwarder"""
        logger.info("Stopping SMS Forwarder...")
        self.running = False

        # Send shutdown notification
        self.send_shutdown_notification()

        # Disconnect all devices
        self.disconnect_all_devices()

        logger.info("SMS Forwarder stopped successfully")
