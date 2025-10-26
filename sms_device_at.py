"""
Direct AT command interface for SMS operations
More reliable than Gammu for Air 780EPV
"""

import serial
import time
import logging
import re
from typing import List, Dict, Optional
from datetime import datetime
from smspdudecoder.codecs import UCS2

logger = logging.getLogger(__name__)


class SMSDeviceAT:
    """Direct AT command SMS operations"""

    def __init__(self, port: str, baudrate: int = 115200):
        self.port = port
        self.baudrate = baudrate
        self.ser = None
        self.processed_sms_ids = set()
        self.active_call_number = None  # Currently ringing/active call
        self.active_call_notified = False  # Whether we've sent notification for active call

    def connect(self) -> bool:
        """Open serial connection"""
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=2)
            time.sleep(0.5)
            # Clear buffer
            self.ser.read(self.ser.in_waiting)
            return True
        except Exception as e:
            logger.error(f"Failed to open AT connection on {self.port}: {e}")
            return False

    def send_command(self, command: str, wait_time: float = 1.0) -> str:
        """Send AT command and get response"""
        if not self.ser:
            return ""

        try:
            self.ser.write((command + '\r\n').encode())
            time.sleep(wait_time)
            response = self.ser.read(self.ser.in_waiting).decode('utf-8', errors='ignore')
            return response
        except Exception as e:
            logger.error(f"Error sending AT command: {e}")
            return ""

    def delete_sms_at(self, location: int, memory: str = "ME") -> bool:
        """
        Delete SMS using direct AT commands

        Args:
            location: SMS location/index (0-based)
            memory: Storage type - "ME" for Phone Memory, "SM" for SIM

        Returns:
            True if deleted successfully
        """
        if location < 0 or location > 1000:
            logger.error(f"Invalid location {location}")
            return False

        try:
            # Set storage location
            response = self.send_command(f'AT+CPMS="{memory}"', wait_time=0.5)
            if 'OK' not in response:
                logger.error(f"Failed to set storage to {memory}: {response}")
                return False

            # Delete SMS at location (using index, delflag=0 for single message)
            response = self.send_command(f'AT+CMGD={location},0', wait_time=1.0)

            if 'OK' in response:
                logger.info(f"Deleted SMS at {memory} location {location} using AT")

                # IMPORTANT: Remove from processed cache so new SMS at this index will be read
                sms_id = f"{memory}_{location}"
                if sms_id in self.processed_sms_ids:
                    self.processed_sms_ids.remove(sms_id)
                    logger.debug(f"Removed {sms_id} from processed cache")

                return True
            else:
                logger.warning(f"AT delete failed: {response.strip()}")
                return False

        except Exception as e:
            logger.error(f"Error in AT delete: {e}")
            return False

    def get_signal_strength(self) -> Optional[int]:
        """
        Get signal strength using AT+CSQ command

        Returns:
            Signal strength percentage (0-100) or None if failed
        """
        try:
            response = self.send_command('AT+CSQ', wait_time=0.5)

            # Response format: +CSQ: <rssi>,<ber>
            # rssi: 0-31 (99 = unknown), ber: bit error rate
            match = re.search(r'\+CSQ:\s*(\d+),(\d+)', response)
            if match:
                rssi = int(match.group(1))
                if rssi == 99:
                    return None  # Unknown signal
                # Convert rssi (0-31) to percentage (0-100)
                percentage = int((rssi / 31.0) * 100)
                return percentage

            return None
        except Exception as e:
            logger.error(f"Error getting signal strength: {e}")
            return None

    def get_network_registration(self) -> Optional[Dict]:
        """
        Get network registration information using AT+CREG? command

        Temporarily sets AT+CREG=2 to get full info, then resets to AT+CREG=0
        to avoid unwanted URCs

        Response formats:
        - n=0 or 1: +CREG: <n>,<stat>
        - n=2: +CREG: <n>,<stat>,<lac>,<ci>,<act>

        Returns:
            Dict with network registration info or None if failed
        """
        try:
            # Set to mode 2 to get full info (lac, ci, act)
            self.send_command('AT+CREG=2', wait_time=0.3)

            # Query registration status
            response = self.send_command('AT+CREG?', wait_time=0.5)

            # Reset to mode 0 to disable URCs
            self.send_command('AT+CREG=0', wait_time=0.3)

            # Try to match full format with lac, ci, act (n=2)
            match = re.search(r'\+CREG:\s*(\d+),(\d+),"([^"]+)","([^"]+)",(\d+)', response)
            if match:
                # Full format response
                n = int(match.group(1))
                stat = int(match.group(2))
                lac = match.group(3)
                ci = match.group(4)
                act = int(match.group(5))
            else:
                # Try to match simple format (n=0 or 1)
                match = re.search(r'\+CREG:\s*(\d+),(\d+)', response)
                if match:
                    n = int(match.group(1))
                    stat = int(match.group(2))
                    lac = None
                    ci = None
                    act = None
                else:
                    return None

            # Status mapping
            stat_map = {
                0: 'Not registered',
                1: 'Registered (home)',
                2: 'Searching',
                3: 'Registration denied',
                4: 'Unknown',
                5: 'Registered (roaming)',
                6: 'Registered (home, SMS only)',
                7: 'Registered (roaming, SMS only)',
                8: 'Emergency only',
                9: 'Registered (home, CSFB not preferred)',
                10: 'Registered (roaming, CSFB not preferred)',
                11: 'Emergency only'
            }

            # Access technology mapping
            act_map = {
                0: 'GSM',
                1: 'GSM Compact',
                2: 'UTRAN',
                3: 'GSM w/EGPRS',
                4: 'UTRAN w/HSDPA',
                5: 'UTRAN w/HSUPA',
                6: 'UTRAN w/HSDPA and HSUPA',
                7: 'E-UTRAN (LTE)',
                8: 'UTRAN HSPA+/EC-GSM-IoT'
            }

            return {
                'stat': stat,
                'stat_str': stat_map.get(stat, f'Unknown ({stat})'),
                'lac': lac,
                'ci': ci,
                'act': act,
                'act_str': act_map.get(act, f'Unknown ({act})') if act is not None else None
            }
        except Exception as e:
            logger.error(f"Error getting network registration: {e}")
            return None

    def check_incoming_call(self) -> Optional[Dict]:
        """
        Check for incoming call by reading serial buffer for RING unsolicited result code

        Returns:
            Dict with call info or None
        """
        if not self.ser or not self.ser.is_open:
            return None

        try:
            # Check if there's data in buffer
            if self.ser.in_waiting > 0:
                data = self.ser.read(self.ser.in_waiting).decode('utf-8', errors='ignore')

                # Check for call ended (NO CARRIER)
                if 'NO CARRIER' in data:
                    if self.active_call_number:
                        logger.info(f"Call ended from {self.active_call_number}")
                        self.active_call_number = None
                        self.active_call_notified = False

                # Check for RING unsolicited result code
                if 'RING' in data:
                    logger.debug(f"RING detected on {self.port}")

                    # Query call information with AT+CLCC
                    time.sleep(0.2)
                    response = self.send_command('AT+CLCC', wait_time=0.5)

                    # Parse CLCC response
                    # Format: +CLCC:<ccid>,<dir>,<stat>,<mode>,<mpty>[,<number>,<type>[,<alpha>]]
                    for line in response.split('\n'):
                        line = line.strip()
                        if line.startswith('+CLCC:'):
                            match = re.match(r'\+CLCC:\s*(\d+),(\d+),(\d+),(\d+),(\d+)(?:,"([^"]+)",(\d+))?', line)
                            if match:
                                call_id = int(match.group(1))
                                direction = int(match.group(2))  # 1=incoming
                                status = int(match.group(3))      # 4=incoming
                                mode = int(match.group(4))        # 0=voice
                                number = match.group(6) if match.group(6) else 'Unknown'

                                # Only process incoming calls
                                if direction == 1:
                                    # If this is the same call we already notified about, ignore
                                    if self.active_call_number == number and self.active_call_notified:
                                        logger.debug(f"Ignoring duplicate RING from {number} (already notified)")
                                        return None

                                    # New call - set as active and mark as notified
                                    self.active_call_number = number
                                    self.active_call_notified = True

                                    status_map = {0: 'Active', 1: 'Held', 2: 'Dialing', 3: 'Alerting', 4: 'Incoming', 5: 'Waiting'}
                                    mode_map = {0: 'Voice', 1: 'Data', 2: 'Fax', 9: 'Unknown'}

                                    call_info = {
                                        'call_id': call_id,
                                        'number': number,
                                        'status': status_map.get(status, 'Unknown'),
                                        'mode': mode_map.get(mode, 'Unknown'),
                                        'timestamp': datetime.now()
                                    }

                                    logger.info(f"Incoming call from {number}")
                                    return call_info

            return None

        except Exception as e:
            logger.error(f"Error checking for incoming call: {e}")
            return None

    def delete_all_read_sms(self, memory: str = "ME") -> bool:
        """
        Delete all read SMS using AT+CMGD with delflag=1

        Args:
            memory: Storage type - "ME" or "SM"

        Returns:
            True if successful
        """
        try:
            # Set storage
            response = self.send_command(f'AT+CPMS="{memory}"', wait_time=0.5)
            if 'OK' not in response:
                return False

            # Delete all read messages (delflag=1)
            # Index is ignored when delflag > 0
            response = self.send_command('AT+CMGD=0,1', wait_time=2.0)

            if 'OK' in response:
                logger.info(f"Deleted all read SMS from {memory} using AT")
                return True
            else:
                logger.warning(f"AT bulk delete failed: {response.strip()}")
                return False

        except Exception as e:
            logger.error(f"Error in AT bulk delete: {e}")
            return False

    def read_single_sms(self, index: int, memory: str = "ME") -> Optional[Dict]:
        """
        Read a single SMS using AT+CMGR command
        This is more reliable than AT+CMGL for getting full message content (AT+CMGL truncates UCS2)

        Args:
            index: Message index
            memory: Storage type - "ME" or "SM"

        Returns:
            SMS dictionary or None
        """
        try:
            # Read single message
            response = self.send_command(f'AT+CMGR={index}', wait_time=1.0)

            if 'OK' not in response or '+CMGR:' not in response:
                return None

            # Parse response
            # Format: +CMGR: "<status>","<sender>",,"<date>,<time><timezone>"
            # Next line: <message text>

            lines = response.split('\n')
            for i, line in enumerate(lines):
                line = line.strip()
                if line.startswith('+CMGR:'):
                    # Parse header
                    match = re.match(r'\+CMGR:\s*"([^"]+)","([^"]+)"[,\s]+"?([^"]*)"?', line)
                    if not match:
                        logger.error(f"Failed to parse +CMGR line: {line}")
                        return None

                    status = match.group(1)
                    sender = match.group(2)
                    timestamp_str = match.group(3) if len(match.groups()) >= 3 else ""

                    # Get message text from next line(s)
                    i += 1
                    text_lines = []
                    while i < len(lines):
                        text_line = lines[i].strip()
                        if text_line.startswith('+CMGR:') or text_line == 'OK':
                            break
                        if text_line:
                            text_lines.append(text_line)
                        i += 1

                    # Join and clean text
                    text = ''.join(text_lines)
                    text = text.strip().strip('"').strip("'")

                    # Decode UCS2 encoding
                    sender = UCS2.decode(sender)
                    text = UCS2.decode(text)

                    # Parse timestamp
                    try:
                        timestamp = self.parse_timestamp(timestamp_str) if timestamp_str else datetime.now()
                    except:
                        timestamp = datetime.now()

                    return {
                        'index': index,
                        'number': sender,
                        'text': text,
                        'status': status,
                        'date': timestamp
                    }

        except Exception as e:
            logger.error(f"Error reading SMS {index}: {e}")
            return None

        return None

    def read_all_sms(self, memory: str = "ME") -> List[Dict]:
        """
        Read all SMS using two-step approach:
        1. AT+CMGL to get list of indices
        2. AT+CMGR for each index to get full content (CMGL truncates UCS2 messages!)

        Args:
            memory: Storage type - "ME" for Phone Memory, "SM" for SIM

        Returns:
            List of SMS dictionaries
        """
        messages = []

        try:
            # Set text mode
            response = self.send_command('AT+CMGF=1', wait_time=0.5)
            if 'OK' not in response:
                logger.error("Failed to set text mode")
                return messages

            # Set storage
            response = self.send_command(f'AT+CPMS="{memory}"', wait_time=0.5)
            if 'OK' not in response:
                logger.error(f"Failed to set storage to {memory}")
                return messages

            # Step 1: Get list of message indices using AT+CMGL
            response = self.send_command('AT+CMGL="ALL"', wait_time=2.0)
            logger.info(f"AT+CMGL response (first 200 chars): {response[:200]}")

            # Extract indices from CMGL response
            indices = []
            for line in response.split('\n'):
                line = line.strip()
                if line.startswith('+CMGL:'):
                    match = re.match(r'\+CMGL:\s*(\d+),', line)
                    if match:
                        indices.append(int(match.group(1)))

            logger.info(f"Found {len(indices)} message(s) in {memory}: {indices}")

            # Step 2: Read each message individually using AT+CMGR
            for index in indices:
                # Create SMS ID
                sms_id = f"{memory}_{index}"

                # Skip if already processed
                if sms_id in self.processed_sms_ids:
                    logger.debug(f"Skipping already processed SMS {sms_id}")
                    continue

                # Read full message content
                sms = self.read_single_sms(index, memory)
                if sms and sms.get('text'):
                    # Add to processed set
                    self.processed_sms_ids.add(sms_id)

                    # Add memory and sms_id to the dictionary
                    sms['memory'] = memory
                    sms['sms_id'] = sms_id

                    messages.append(sms)
                    logger.info(f"Read SMS {index}: from {sms['from']}, text: {sms['text'][:50]}...")
                else:
                    logger.warning(f"Failed to read SMS at index {index} or empty message")

            logger.info(f"Read {len(messages)} SMS from {memory} using AT")
            return messages

        except Exception as e:
            logger.error(f"Error reading SMS: {e}")
            return messages

    # def decode_pdu_simple(self, pdu_hex: str) -> Optional[str]:
    #     """
    #     Simple PDU decoder for SMS

    #     Args:
    #         pdu_hex: Hex string of PDU data

    #     Returns:
    #         Decoded text or None
    #     """
    #     try:
    #         # Remove any spaces
    #         pdu_hex = pdu_hex.replace(' ', '').upper()

    #         # Convert hex to bytes
    #         pdu_bytes = bytes.fromhex(pdu_hex)

    #         # PDU format (simplified):
    #         # SMSC length (1 byte) + SMSC (variable) + PDU type (1 byte) + ...
    #         # Sender length (1 byte) + Sender type (1 byte) + Sender (variable)
    #         # ... protocol, coding, timestamp ...
    #         # User data length (1 byte) + User data

    #         # Skip SMSC
    #         smsc_len = pdu_bytes[0]
    #         pos = 1 + smsc_len

    #         if pos >= len(pdu_bytes):
    #             return None

    #         # PDU type
    #         pdu_type = pdu_bytes[pos]
    #         pos += 1

    #         # Sender address length
    #         if pos >= len(pdu_bytes):
    #             return None
    #         sender_len = pdu_bytes[pos]
    #         pos += 1

    #         # Sender type
    #         pos += 1

    #         # Sender address (skip it)
    #         sender_bytes = (sender_len + 1) // 2
    #         pos += sender_bytes

    #         # Protocol identifier
    #         pos += 1

    #         # Data coding scheme
    #         if pos >= len(pdu_bytes):
    #             return None
    #         dcs = pdu_bytes[pos]
    #         pos += 1

    #         # Timestamp (7 bytes)
    #         pos += 7

    #         # User data length
    #         if pos >= len(pdu_bytes):
    #             return None
    #         udl = pdu_bytes[pos]
    #         pos += 1

    #         # User data
    #         if pos >= len(pdu_bytes):
    #             return None

    #         user_data = pdu_bytes[pos:]

    #         # Decode based on coding scheme
    #         if dcs == 0 or dcs == 0xF6:  # 7-bit GSM alphabet
    #             # Decode 7-bit packed data
    #             text = self.decode_7bit(user_data, udl)
    #             return text
    #         elif dcs == 8:  # UCS2 (16-bit)
    #             text = user_data.decode('utf-16-be', errors='ignore')
    #             return text
    #         else:
    #             # Try as ASCII
    #             return user_data.decode('ascii', errors='ignore')

    #     except Exception as e:
    #         logger.error(f"PDU decode error: {e}")
    #         return None

    # def decode_7bit(self, data: bytes, length: int) -> str:
    #     """
    #     Decode 7-bit GSM alphabet

    #     Args:
    #         data: Packed 7-bit data
    #         length: Number of characters

    #     Returns:
    #         Decoded string
    #     """
    #     try:
    #         result = []
    #         byte_index = 0
    #         bit_offset = 0

    #         for i in range(length):
    #             if byte_index >= len(data):
    #                 break

    #             # Extract 7 bits
    #             if bit_offset == 0:
    #                 char = data[byte_index] & 0x7F
    #             else:
    #                 char = ((data[byte_index] >> bit_offset) |
    #                        (data[byte_index + 1] << (8 - bit_offset))) & 0x7F
    #                 byte_index += 1

    #             bit_offset = (bit_offset + 7) % 8
    #             if bit_offset == 0:
    #                 byte_index += 1

    #             # Basic GSM 7-bit to ASCII
    #             if 32 <= char <= 126:
    #                 result.append(chr(char))
    #             else:
    #                 result.append(chr(char) if char < 128 else '?')

    #         return ''.join(result)

    #     except Exception as e:
    #         logger.error(f"7-bit decode error: {e}")
    #         return ""

    # def decode_pdu(self, pdu_hex: str) -> Optional[str]:
        """
        Try to decode PDU format SMS

        Args:
            pdu_hex: Hex string of PDU data

        Returns:
            Decoded text or None
        """
        # Use simple PDU decoder
        text = self.decode_pdu_simple(pdu_hex)
        return text

    def parse_timestamp(self, timestamp_str: str) -> datetime:
        """
        Parse Air 780EP timestamp format: 25/10/25,19:33:13+44

        Args:
            timestamp_str: Timestamp string from SMS

        Returns:
            datetime object
        """
        # Remove timezone offset
        timestamp_str = re.sub(r'[+-]\d+$', '', timestamp_str)

        # Parse: 25/10/25,19:33:13
        try:
            return datetime.strptime(timestamp_str, '%y/%m/%d,%H:%M:%S')
        except:
            # Try alternative format
            return datetime.now()

    def get_sms_count(self, memory: str = "ME") -> Optional[Dict]:
        """
        Get SMS count from storage

        Args:
            memory: Storage type

        Returns:
            Dict with used/total counts
        """
        try:
            response = self.send_command(f'AT+CPMS="{memory}"', wait_time=0.5)

            # Parse: +CPMS: "ME",2,10,"ME",2,10,"ME",2,10
            match = re.search(r'\+CPMS: "' + memory + r'",(\d+),(\d+)', response)
            if match:
                return {
                    'used': int(match.group(1)),
                    'total': int(match.group(2))
                }

        except Exception as e:
            logger.error(f"Error getting SMS count: {e}")

        return None

    def close(self):
        """Close serial connection"""
        if self.ser:
            try:
                self.ser.close()
            except:
                pass
