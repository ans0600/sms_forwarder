"""
SMS Forwarder using pure AT commands (no Gammu)
Much more reliable for Air 780EPV devices
"""

import logging
import time
import threading
from typing import List, Dict
from datetime import datetime

from telegram_notifier import TelegramNotifier
from sms_device_at import SMSDeviceAT


logger = logging.getLogger(__name__)


class SMSForwarderAT:
    """SMS forwarding application using AT commands only"""

    def __init__(self, telegram_token: str, telegram_chat_id: str,
                 devices: List[Dict], poll_interval: int = 10,
                 delete_after_forward: bool = True):
        """
        Initialize SMS forwarder with AT commands

        Args:
            telegram_token: Telegram bot token
            telegram_chat_id: Telegram chat ID
            devices: List of device configurations
            poll_interval: Polling interval in seconds
            delete_after_forward: Delete SMS after forwarding
        """
        self.telegram = TelegramNotifier(telegram_token, telegram_chat_id)
        self.devices = []
        self.poll_interval = poll_interval
        self.delete_after_forward = delete_after_forward
        self.running = False
        self.monitor_threads = []  # Threads for monitoring incoming calls

        # Initialize AT command devices
        for dev_config in devices:
            device = SMSDeviceAT(dev_config['port'])
            device.device_name = dev_config['name']
            self.devices.append(device)

    def connect_all_devices(self) -> Dict:
        """Connect to all configured devices"""
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
                    'port': device.port,
                    'reason': 'Device not found or connection failed'
                })
            else:
                # Get SMS count
                count_info = device.get_sms_count("ME")
                used = count_info['used'] if count_info else 0
                total = count_info['total'] if count_info else 0

                # Get signal strength
                signal = device.get_signal_strength()

                device_data = {
                    'name': device.device_name,
                    'port': device.port,
                    'sms_count': f"{used}/{total}",
                    'signal': signal if signal is not None else 'N/A'
                }

                results['connected'].append(device_data)
                results['device_info'][device.device_name] = device_data

                logger.info(f"Connected to {device.device_name} on {device.port} (AT)")
                logger.info(f"SMS count: {used}/{total}")
                logger.info(f"Signal strength: {signal}%" if signal is not None else "Signal strength: N/A")

        return results

    def disconnect_all_devices(self):
        """Disconnect from all devices"""
        for device in self.devices:
            device.close()

    def format_sms_message(self, sms: Dict) -> str:
        """Format SMS for Telegram"""
        timestamp = sms['date'].strftime('%Y-%m-%d %H:%M:%S')
        device_name = getattr(sms.get('device_obj'), 'device_name', 'Unknown')

        message = f"""📱 <b>New SMS Received</b>

<b>Device:</b> {device_name}
<b>From:</b> {sms['number']}
<b>Date:</b> {timestamp}

<b>Message:</b>
{sms['text']}"""
        return message

    def process_device_sms(self, device: SMSDeviceAT):
        """Process SMS from a single device"""
        try:
            # Read from Phone Memory (ME) - where Air 780EPV stores SMS
            messages = device.read_all_sms(memory="ME")

            if messages:
                logger.info(f"Found {len(messages)} new message(s) from {device.device_name}")

            for sms in messages:
                try:
                    # Add device reference
                    sms['device_obj'] = device

                    # Format and send to Telegram
                    telegram_message = self.format_sms_message(sms)

                    if self.telegram.send_message(telegram_message):
                        logger.info(f"Forwarded SMS from {sms['number']} via {device.device_name}")

                        # Delete SMS if configured
                        if self.delete_after_forward:
                            if device.delete_sms_at(sms['index'], sms['memory']):
                                logger.info(f"Deleted SMS index {sms['index']} from {device.device_name}")
                            else:
                                logger.warning(f"Failed to delete SMS {sms['sms_id']}")
                    else:
                        logger.warning(f"Failed to forward SMS from {device.device_name}")

                except Exception as e:
                    logger.error(f"Error processing individual SMS: {repr(e)}")
                    continue

        except Exception as e:
            logger.error(f"Error processing SMS from {device.device_name}: {e}")

    def process_incoming_call(self, device, call_info: Dict):
        """Process incoming call and send Telegram notification"""
        try:
            timestamp = call_info['timestamp'].strftime('%Y-%m-%d %H:%M:%S')

            message = f"""📞 <b>Incoming Call</b>

<b>Device:</b> {device.device_name}
<b>From:</b> {call_info['number']}
<b>Status:</b> {call_info['status']}
<b>Type:</b> {call_info['mode']}
<b>Time:</b> {timestamp}"""

            success = self.telegram.send_message(message)
            if success:
                logger.info(f"Sent call notification for {call_info['number']} from {device.device_name}")
            else:
                logger.warning(f"Failed to send call notification to Telegram")

        except Exception as e:
            logger.error(f"Error processing incoming call: {e}")

    def monitor_device(self, device):
        """
        Monitor a single device for both incoming calls and SMS in a dedicated thread
        Uses a single serial connection to avoid conflicts
        """
        logger.info(f"Starting monitor thread for {device.device_name}")

        sms_check_counter = 0

        while self.running:
            try:
                if device.ser and device.ser.is_open:
                    # Always check for incoming calls (time-sensitive, just reads buffer)
                    call_info = device.check_incoming_call()
                    if call_info:
                        self.process_incoming_call(device, call_info)

                    # Check for SMS less frequently (requires AT commands)
                    if sms_check_counter == 0:
                        self.process_device_sms(device)

                    # Sleep 100ms for responsive call detection
                    time.sleep(0.1)

                    # Increment counter: check SMS every poll_interval seconds
                    # (100ms * poll_interval * 10 = poll_interval seconds)
                    sms_check_counter += 1
                    if sms_check_counter >= (self.poll_interval * 10):
                        sms_check_counter = 0

                else:
                    logger.warning(f"Device {device.device_name} not connected")
                    time.sleep(5)  # Wait before retrying

            except Exception as e:
                logger.error(f"Error in monitor for {device.device_name}: {e}")
                time.sleep(1)

        logger.info(f"Monitor thread stopped for {device.device_name}")

    def send_startup_notification(self, connection_results: Dict):
        """Send startup notification to Telegram"""
        connected_section = ""
        if connection_results['connected']:
            for dev in connection_results['connected']:
                signal_str = f"{dev['signal']}%" if isinstance(dev['signal'], int) else dev['signal']
                connected_section += f"""
<b>✅ {dev['name']}</b>
  • Port: {dev['port']}
  • Signal: {signal_str}
  • SMS Storage: {dev['sms_count']}
"""

        failed_section = ""
        if connection_results['failed']:
            for dev in connection_results['failed']:
                failed_section += f"""
<b>❌ {dev['name']}</b>
  • Port: {dev['port']}
  • Status: {dev['reason']}
"""

        if connection_results['connected']:
            status = f"✅ {len(connection_results['connected'])} device(s) connected"
            if connection_results['failed']:
                status += f"\n⚠️ {len(connection_results['failed'])} device(s) failed"
        else:
            status = "❌ No devices connected"

        message = f"""🚀 <b>SMS Forwarder Started (AT Mode)</b>

<b>Configuration:</b>
  • Method: Direct AT Commands (No Gammu)
  • Poll Interval: {self.poll_interval} seconds
  • Delete After Forward: {'Yes' if self.delete_after_forward else 'No'}

<b>Status:</b> {status}
{connected_section}{failed_section}
<b>✅ Monitoring for incoming SMS and calls...</b>"""

        self.telegram.send_message(message)

    def send_shutdown_notification(self):
        """Send shutdown notification to Telegram"""
        message = "🛑 <b>SMS Forwarder Stopped</b>"
        self.telegram.send_message(message)

    def start(self):
        """Start the SMS forwarder"""
        logger.info("Starting SMS Forwarder (AT Commands mode)...")

        # Test Telegram connection
        if not self.telegram.test_connection():
            logger.error("Failed to connect to Telegram")
            return

        # Connect to devices
        connection_results = self.connect_all_devices()

        # Send startup notification
        self.send_startup_notification(connection_results)

        # Check if at least one device connected
        if not connection_results['connected']:
            logger.error("No devices connected. Cannot start.")
            return

        # Start monitoring
        self.running = True

        # Start a monitor thread for each connected device
        # Each thread monitors both calls (100ms) and SMS (poll_interval)
        for device in self.devices:
            if device.ser and device.ser.is_open:
                thread = threading.Thread(
                    target=self.monitor_device,
                    args=(device,),
                    daemon=True,
                    name=f"Monitor-{device.device_name}"
                )
                thread.start()
                self.monitor_threads.append(thread)
                logger.info(f"Started monitor thread for {device.device_name}")

        # Main thread just waits for shutdown signal
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Received shutdown signal (Ctrl+C)")
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
        finally:
            self.stop()

    def stop(self):
        """Stop the SMS forwarder"""
        logger.info("Stopping SMS Forwarder...")
        self.running = False

        # Wait for monitor threads to finish (they check self.running)
        logger.info("Waiting for call monitor threads to stop...")
        for thread in self.monitor_threads:
            thread.join(timeout=2)

        # Send shutdown notification
        self.send_shutdown_notification()

        # Disconnect devices
        self.disconnect_all_devices()

        logger.info("SMS Forwarder stopped successfully")
