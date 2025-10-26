"""
SMS device handler module for Air 780EPV devices
"""

import logging
import gammu
from typing import List, Dict, Optional

try:
    from sms_device_at import SMSDeviceAT
    AT_COMMANDS_AVAILABLE = True
except ImportError:
    AT_COMMANDS_AVAILABLE = False


logger = logging.getLogger(__name__)


class SMSDevice:
    """Handle SMS operations for a single device"""

    def __init__(self, device_name: str, device_port: str, device_connection: str = "at"):
        """
        Initialize SMS device handler

        Args:
            device_name: Friendly name for the device
            device_port: Serial port for the device (e.g., /dev/ttyUSB0)
            device_connection: Connection type (default: "at")
        """
        self.device_name = device_name
        self.device_port = device_port
        self.device_connection = device_connection
        self.state_machine = None
        self.processed_sms_ids = set()
        self.delete_errors = 0  # Track consecutive delete errors
        self.deletion_disabled = False  # Safety flag
        self.at_interface = None  # Direct AT command interface
        self.use_at_for_deletion = True  # Prefer AT commands for deletion (more reliable)

    def connect(self) -> bool:
        """
        Connect to the device

        Returns:
            True if connected successfully, False otherwise
        """
        try:
            self.state_machine = gammu.StateMachine()
            self.state_machine.SetConfig(0, {
                'Device': self.device_port,
                'Connection': self.device_connection,
            })
            self.state_machine.Init()
            logger.info(f"Connected to device: {self.device_name} on {self.device_port}")
            return True
        except gammu.GSMError as e:
            logger.error(f"Gammu error connecting to {self.device_name}: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to connect to {self.device_name}: {e}")
            return False

    def disconnect(self):
        """Disconnect from the device"""
        try:
            if self.state_machine:
                self.state_machine.Terminate()
                logger.info(f"Disconnected from {self.device_name}")
        except Exception as e:
            logger.error(f"Error disconnecting from {self.device_name}: {e}")

    def get_signal_strength(self) -> Optional[int]:
        """
        Get signal strength percentage

        Returns:
            Signal strength percentage or None if failed
        """
        try:
            signal_info = self.state_machine.GetSignalQuality()
            return signal_info.get('SignalPercent', -1)
        except Exception as e:
            logger.error(f"Failed to get signal strength for {self.device_name}: {e}")
            return None

    def get_device_info(self) -> Optional[Dict]:
        """
        Get device information

        Returns:
            Dictionary with device info or None if failed
        """
        try:
            manufacturer = self.state_machine.GetManufacturer()
            model = self.state_machine.GetModel()
            imei = self.state_machine.GetIMEI()

            return {
                'manufacturer': manufacturer,
                'model': model[0] if isinstance(model, tuple) else model,
                'imei': imei
            }
        except Exception as e:
            logger.error(f"Failed to get device info for {self.device_name}: {e}")
            return None

    def get_sim_info(self) -> Optional[Dict]:
        """
        Get SIM card information

        Returns:
            Dictionary with SIM info or None if failed
        """
        try:
            # Get IMSI (International Mobile Subscriber Identity)
            imsi = self.state_machine.GetSIMIMSI()

            # Try to get network info for operator name
            operator = "Unknown"
            try:
                network_info = self.state_machine.GetNetworkInfo()
                if network_info and 'NetworkName' in network_info:
                    operator = network_info['NetworkName']
                elif network_info and 'NetworkCode' in network_info:
                    operator = network_info['NetworkCode']
            except Exception:
                # Network info might not be available
                pass

            return {
                'imsi': imsi,
                'operator': operator
            }
        except gammu.GSMError as e:
            logger.error(f"Gammu error getting SIM info for {self.device_name}: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to get SIM info for {self.device_name}: {e}")
            return None

    def read_sms(self) -> List[Dict]:
        """
        Read all SMS messages from the device
        Checks all folders: SIM Inbox, SIM Outbox, Phone Inbox, Phone Outbox

        Returns:
            List of SMS messages with metadata
        """
        messages = []

        # Check if device is connected
        if not self.state_machine:
            logger.warning(f"Device {self.device_name} not connected, skipping SMS read")
            return messages

        try:
            # Get SMS status
            status = self.state_machine.GetSMSStatus()
            remaining = status['SIMUsed'] + status['PhoneUsed']

            if remaining == 0:
                return messages

            # Check all folders (0=SM Inbox, 1=SM Outbox, 2=ME Inbox, 3=ME Outbox)
            # Focus on inbox folders (0 and 2) for receiving SMS
            inbox_folders = [0, 2]  # SIM Inbox and Phone Memory Inbox

            for folder in inbox_folders:
                try:
                    start = True
                    read_attempts = 0
                    max_attempts = 50  # Prevent infinite loops from corrupted data

                    while read_attempts < max_attempts:
                        try:
                            read_attempts += 1

                            if start:
                                sms = self.state_machine.GetNextSMS(Start=True, Folder=folder)
                                start = False
                            else:
                                sms = self.state_machine.GetNextSMS(Location=sms[0]['Location'], Folder=folder)

                            # Process each SMS part
                            for message in sms:
                                # Validate location is reasonable (not corrupted)
                                location = message.get('Location', 0)
                                if location < 0 or location > 1000:
                                    logger.error(f"CORRUPTED SMS location {location} in folder {folder} on {self.device_name}")
                                    logger.error(f"Device state may be corrupted, clearing processed SMS cache")
                                    # Clear cache to avoid processing corrupted data
                                    self.processed_sms_ids.clear()
                                    # Disable deletion immediately
                                    self.deletion_disabled = True
                                    logger.error(f"Deletion DISABLED for {self.device_name} due to data corruption")
                                    # Stop reading from this folder
                                    break

                                sms_id = f"{self.device_name}_F{folder}_{location}"

                                # Skip if already processed
                                if sms_id in self.processed_sms_ids:
                                    continue

                                # Validate message data
                                if not message.get('Number') or not message.get('Text'):
                                    logger.warning(f"Invalid SMS data at location {location}, skipping")
                                    continue

                                messages.append({
                                    'device': self.device_name,
                                    'number': message['Number'],
                                    'text': message['Text'],
                                    'date': message.get('DateTime'),
                                    'location': location,
                                    'folder': folder,
                                    'sms_id': sms_id,
                                    'state': message.get('State', 'Unknown')
                                })

                                # Mark as processed
                                self.processed_sms_ids.add(sms_id)

                        except gammu.ERR_EMPTY:
                            # No more messages in this folder
                            break

                    if read_attempts >= max_attempts:
                        logger.warning(f"Reached max read attempts for folder {folder}, possible corruption")

                except gammu.ERR_EMPTY:
                    # Folder is empty
                    pass
                except Exception as e:
                    logger.debug(f"Error reading from folder {folder}: {e}")

        except gammu.ERR_EMPTY:
            # No messages at all
            pass
        except gammu.GSMError as e:
            logger.error(f"Gammu error reading SMS from {self.device_name}: {e}")
        except Exception as e:
            logger.error(f"Error reading SMS from {self.device_name}: {e}")

        return messages

    def delete_sms(self, location: int, folder: int = 0) -> bool:
        """
        Delete SMS at specific location and folder with safety checks

        Args:
            location: SMS location/index
            folder: Folder number (0=SIM Inbox, 2=Phone Inbox, etc.)

        Returns:
            True if deleted successfully
        """
        # Safety: If deletion is disabled due to errors, skip
        if self.deletion_disabled:
            logger.warning(f"Deletion disabled for {self.device_name} due to previous errors")
            return False

        # Validate inputs
        if not self.state_machine:
            logger.warning(f"Device {self.device_name} not connected, cannot delete SMS")
            self.delete_errors += 1
            return False

        if location < 0 or location > 1000:
            logger.error(f"Invalid location {location}, refusing to delete")
            self.delete_errors += 1
            # Disable deletion if we see invalid locations (sign of corruption)
            if self.delete_errors >= 3:
                self.deletion_disabled = True
                logger.error(f"DISABLING DELETION for {self.device_name} due to repeated invalid locations")
            return False

        if folder not in [0, 1, 2, 3]:
            logger.error(f"Invalid folder {folder}, refusing to delete")
            self.delete_errors += 1
            return False

        try:
            # Determine storage type from folder
            # Folder 0,1 = SIM (SM), Folder 2,3 = Phone Memory (ME)
            memory = "ME" if folder in [2, 3] else "SM"

            # Try AT commands first if available and enabled (more reliable)
            if self.use_at_for_deletion and AT_COMMANDS_AVAILABLE:
                if not self.at_interface:
                    self.at_interface = SMSDeviceAT(self.device_port)
                    if not self.at_interface.connect():
                        logger.warning("AT interface failed, falling back to Gammu")
                        self.at_interface = None
                        self.use_at_for_deletion = False

                if self.at_interface:
                    success = self.at_interface.delete_sms_at(location, memory)
                    if success:
                        logger.info(f"Deleted SMS at {memory} location {location} from {self.device_name} (AT)")
                        self.delete_errors = 0
                        return True
                    else:
                        logger.warning("AT delete failed, trying Gammu")

            # Fallback to Gammu
            self.state_machine.DeleteSMS(Folder=folder, Location=location)
            logger.info(f"Deleted SMS at folder {folder}, location {location} from {self.device_name} (Gammu)")
            # Reset error counter on success
            self.delete_errors = 0
            return True
        except gammu.GSMError as e:
            # Track consecutive errors
            self.delete_errors += 1

            # Don't treat certain errors as critical
            error_code = e.args[0].get('Code', 0) if isinstance(e.args[0], dict) else 0
            if error_code in [14, 22, 33]:  # Timeout, Empty, Not connected
                logger.warning(f"Could not delete SMS from {self.device_name} (Folder={folder}, Location={location}): {e}")
            else:
                logger.error(f"Gammu error deleting SMS from {self.device_name} (Folder={folder}, Location={location}): {e}")

            # Disable deletion after 5 consecutive errors (device may be crashing)
            if self.delete_errors >= 5:
                self.deletion_disabled = True
                logger.error(f"DISABLING DELETION for {self.device_name} due to {self.delete_errors} consecutive errors")
                logger.error(f"Device may be unstable. SMS will still be forwarded but not deleted.")

            return False
        except Exception as e:
            self.delete_errors += 1
            logger.error(f"Failed to delete SMS from {self.device_name}: {e}")
            return False

    def delete_all_sms(self) -> int:
        """
        Delete all SMS messages from the device

        Returns:
            Number of messages deleted
        """
        deleted_count = 0
        try:
            status = self.state_machine.GetSMSStatus()
            remaining = status['SIMUsed'] + status['PhoneUsed']

            start = True
            while remaining > 0:
                try:
                    if start:
                        sms = self.state_machine.GetNextSMS(Start=True, Folder=0)
                        start = False
                    else:
                        sms = self.state_machine.GetNextSMS(Location=sms[0]['Location'], Folder=0)

                    remaining -= len(sms)

                    for message in sms:
                        if self.delete_sms(message['Location']):
                            deleted_count += 1

                except gammu.ERR_EMPTY:
                    break

        except gammu.ERR_EMPTY:
            pass
        except Exception as e:
            logger.error(f"Error deleting all SMS from {self.device_name}: {e}")

        logger.info(f"Deleted {deleted_count} messages from {self.device_name}")
        return deleted_count
