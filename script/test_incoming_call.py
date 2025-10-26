#!/usr/bin/env python3
"""
Test script for incoming call detection on Air 780EPV

This script monitors for incoming calls using:
1. RING unsolicited result code
2. AT+CLCC command to get call details

Test by calling the SIM card number from another phone.
"""

import serial
import time
import sys
import re
from datetime import datetime


def send_at(ser, command, wait=0.5):
    """Send AT command and get response"""
    ser.write(f'{command}\r\n'.encode())
    time.sleep(wait)
    response = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
    return response


def parse_clcc_response(response):
    """
    Parse AT+CLCC response to get call information

    Format: +CLCC:<ccid>,<dir>,<stat>,<mode>,<mpty>[,<number>,<type>[,<alpha>]]

    <ccid>: call ID (1-7)
    <dir>: 0=mobile originated, 1=mobile terminated (incoming)
    <stat>: 0=active, 1=held, 2=dialing, 3=alerting, 4=incoming, 5=waiting
    <mode>: 0=voice, 1=data, 2=fax, 9=unknown
    <mpty>: 0=not multiparty, 1=multiparty
    <number>: phone number
    <type>: type of number (129=national, 145=international)
    """
    calls = []

    for line in response.split('\n'):
        line = line.strip()
        if line.startswith('+CLCC:'):
            # Parse the CLCC line
            match = re.match(r'\+CLCC:\s*(\d+),(\d+),(\d+),(\d+),(\d+)(?:,"([^"]+)",(\d+))?', line)
            if match:
                call_info = {
                    'call_id': int(match.group(1)),
                    'direction': int(match.group(2)),  # 0=outgoing, 1=incoming
                    'status': int(match.group(3)),     # 4=incoming, 0=active
                    'mode': int(match.group(4)),       # 0=voice
                    'multiparty': int(match.group(5)),
                    'number': match.group(6) if match.group(6) else 'Unknown',
                    'type': int(match.group(7)) if match.group(7) else 0
                }

                # Add human-readable fields
                call_info['direction_str'] = 'Incoming' if call_info['direction'] == 1 else 'Outgoing'

                status_map = {
                    0: 'Active',
                    1: 'Held',
                    2: 'Dialing',
                    3: 'Alerting',
                    4: 'Incoming',
                    5: 'Waiting'
                }
                call_info['status_str'] = status_map.get(call_info['status'], 'Unknown')

                mode_map = {
                    0: 'Voice',
                    1: 'Data',
                    2: 'Fax',
                    9: 'Unknown'
                }
                call_info['mode_str'] = mode_map.get(call_info['mode'], 'Unknown')

                calls.append(call_info)

    return calls


def monitor_incoming_calls(port='/dev/ttyACM0', duration=300):
    """
    Monitor for incoming calls

    Args:
        port: Serial port
        duration: How long to monitor (seconds), default 5 minutes
    """
    print(f"Opening {port}...")
    ser = serial.Serial(port, 115200, timeout=0.1)
    time.sleep(0.5)

    # Clear buffer
    ser.read(ser.in_waiting)

    print("\n" + "="*80)
    print("Incoming Call Monitor")
    print("="*80)
    print(f"Monitoring port: {port}")
    print(f"Duration: {duration} seconds")
    print("\nWaiting for incoming calls...")
    print("(Call the SIM card number from another phone to test)")
    print("\nPress Ctrl+C to stop\n")

    start_time = time.time()
    last_check = time.time()
    ring_count = 0

    try:
        while time.time() - start_time < duration:
            # Check for data from serial port
            if ser.in_waiting > 0:
                data = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')

                # Check for RING unsolicited result code
                if 'RING' in data:
                    ring_count += 1
                    timestamp = datetime.now().strftime('%H:%M:%S')

                    print(f"\n[{timestamp}] 🔔 RING detected! (Ring #{ring_count})")
                    print(f"Raw data: {repr(data)}")

                    # Query call information
                    print("\nQuerying call details with AT+CLCC...")
                    time.sleep(0.2)
                    response = send_at(ser, 'AT+CLCC', wait=0.5)

                    print(f"AT+CLCC Response:")
                    print(response)

                    # Parse call info
                    calls = parse_clcc_response(response)

                    if calls:
                        print("\n" + "-"*80)
                        print("INCOMING CALL DETAILS:")
                        print("-"*80)
                        for call in calls:
                            print(f"  Call ID:      {call['call_id']}")
                            print(f"  Direction:    {call['direction_str']}")
                            print(f"  Status:       {call['status_str']}")
                            print(f"  Mode:         {call['mode_str']}")
                            print(f"  Phone Number: {call['number']}")
                            print(f"  Number Type:  {'International' if call['type'] == 145 else 'National/Unknown'}")

                            # This is what we'd send to Telegram
                            print("\n  Telegram Message Preview:")
                            print("  " + "─"*50)
                            telegram_msg = f"""📞 Incoming Call

  From: {call['number']}
  Status: {call['status_str']}
  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
  Device: Air780EPV"""
                            print("  " + telegram_msg.replace('\n', '\n  '))
                            print("  " + "─"*50)
                        print("-"*80)
                    else:
                        print("  No active calls found in response")

                    print("\nWaiting for next call...\n")

                # Show any other unsolicited codes
                elif data.strip() and not data.strip() == 'OK':
                    # Filter out common noise
                    if not any(x in data for x in ['\r\n\r\n', 'AT+', '+CMGL']):
                        timestamp = datetime.now().strftime('%H:%M:%S')
                        print(f"[{timestamp}] Other data: {repr(data.strip())}")

            # Periodic status update
            if time.time() - last_check > 30:
                elapsed = int(time.time() - start_time)
                remaining = duration - elapsed
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Still monitoring... ({remaining}s remaining, {ring_count} calls detected)")
                last_check = time.time()

            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\n\nMonitoring stopped by user")

    finally:
        ser.close()
        print(f"\nMonitoring complete!")
        print(f"Total RING events detected: {ring_count}")
        print(f"Total time: {int(time.time() - start_time)} seconds")


def test_clcc_parser():
    """Test the CLCC response parser with sample data"""
    print("="*80)
    print("Testing CLCC Parser")
    print("="*80)

    # Test case 1: Incoming call
    sample1 = '+CLCC: 1,1,4,0,0,"+61412345678",145\r\n\r\nOK\r\n'
    print("\nTest 1: Incoming call from international number")
    print(f"Input: {repr(sample1)}")
    calls = parse_clcc_response(sample1)
    print(f"Parsed: {calls}")

    # Test case 2: Active call
    sample2 = '+CLCC: 1,1,0,0,0,"0412345678",129\r\n\r\nOK\r\n'
    print("\nTest 2: Active call from national number")
    print(f"Input: {repr(sample2)}")
    calls = parse_clcc_response(sample2)
    print(f"Parsed: {calls}")

    # Test case 3: No calls
    sample3 = 'OK\r\n'
    print("\nTest 3: No active calls")
    print(f"Input: {repr(sample3)}")
    calls = parse_clcc_response(sample3)
    print(f"Parsed: {calls}")

    print("\n" + "="*80)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == '--test-parser':
        # Test the parser
        test_clcc_parser()
    else:
        # Monitor for real calls
        port = sys.argv[1] if len(sys.argv) > 1 else '/dev/ttyACM0'
        duration = int(sys.argv[2]) if len(sys.argv) > 2 else 300

        print("\nUsage:")
        print(f"  {sys.argv[0]} [port] [duration_seconds]")
        print(f"  {sys.argv[0]} --test-parser  (test parser only)")
        print()

        monitor_incoming_calls(port, duration)
