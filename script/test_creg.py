#!/usr/bin/env python3
"""
Debug script to test AT+CREG? command and parsing
"""

import sys
import os
import re
import serial
import time

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sms_device_at import SMSDeviceAT


def send_at(ser, command, wait=1.0):
    """Send AT command and return response"""
    ser.write((command + '\r\n').encode('utf-8'))
    time.sleep(wait)
    response = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
    return response


def test_creg_raw(port='/dev/ttyACM0'):
    """Test AT+CREG? command directly"""
    print(f"\n{'='*80}")
    print(f"RAW AT+CREG? TEST on {port}")
    print(f"{'='*80}\n")

    try:
        ser = serial.Serial(port, baudrate=115200, timeout=1)
        print(f"✅ Opened serial port: {port}\n")

        # Test AT command
        print("Testing basic AT command...")
        response = send_at(ser, 'AT')
        print(f"AT response: {repr(response)}\n")

        # Test the temporary mode change approach
        print("Step 1: Setting AT+CREG=2 to enable full info...")
        response = send_at(ser, 'AT+CREG=2', wait=0.3)
        print(f"Response: {repr(response)}\n")

        print("Step 2: Querying AT+CREG?...")
        response = send_at(ser, 'AT+CREG?', wait=0.5)
        print(f"Raw response:\n{repr(response)}\n")
        print(f"Formatted response:")
        print(response)
        print()

        # Save response for parsing
        creg_response = response

        print("Step 3: Resetting AT+CREG=0 to disable URCs...")
        response = send_at(ser, 'AT+CREG=0', wait=0.3)
        print(f"Response: {repr(response)}\n")

        # Parse the response
        print("Parsing CREG response...")

        # Try full format first (n=2)
        match = re.search(r'\+CREG:\s*(\d+),(\d+),"([^"]+)","([^"]+)",(\d+)', creg_response)
        if match:
            print(f"✅ Matched FULL format (n=2)")
            print(f"   n = {match.group(1)}")
            print(f"   stat = {match.group(2)}")
            print(f"   lac = {match.group(3)}")
            print(f"   ci = {match.group(4)}")
            print(f"   act = {match.group(5)}")
        else:
            # Try simple format (n=0 or 1)
            match = re.search(r'\+CREG:\s*(\d+),(\d+)', creg_response)
            if match:
                print(f"✅ Matched SIMPLE format (n=0 or 1)")
                print(f"   n = {match.group(1)}")
                print(f"   stat = {match.group(2)}")
                print(f"   lac = None")
                print(f"   ci = None")
                print(f"   act = None")
            else:
                print(f"❌ Failed to parse response")

        ser.close()
        print(f"\n✅ Closed serial port")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


def test_creg_parsed(port='/dev/ttyACM0'):
    """Test using SMSDeviceAT class"""
    print(f"\n{'='*80}")
    print(f"PARSED AT+CREG? TEST using SMSDeviceAT on {port}")
    print(f"{'='*80}\n")

    try:
        device = SMSDeviceAT(port)
        device.device_name = "TestDevice"

        if not device.connect():
            print(f"❌ Failed to connect to device")
            return

        print(f"✅ Connected to device\n")

        # Get network registration
        print("Calling get_network_registration()...")
        network_reg = device.get_network_registration()

        if network_reg:
            print(f"✅ Got network registration info:\n")
            print(f"   stat: {network_reg.get('stat')}")
            print(f"   stat_str: {network_reg.get('stat_str')}")
            print(f"   lac: {network_reg.get('lac')}")
            print(f"   ci: {network_reg.get('ci')}")
            print(f"   act: {network_reg.get('act')}")
            print(f"   act_str: {network_reg.get('act_str')}")
            print()

            # Show how it would appear in status message
            print("Status message format:")
            network_info = f"\n  • Network: {network_reg['stat_str']}"
            if network_reg.get('act_str'):
                network_info += f"\n  • Technology: {network_reg['act_str']}"
            if network_reg.get('lac'):
                network_info += f"\n  • LAC: {network_reg['lac']}, CI: {network_reg['ci']}"
            print(network_info)
        else:
            print(f"❌ Failed to get network registration")

        device.close()
        print(f"\n✅ Closed device")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Test AT+CREG? command")
    parser.add_argument('port', nargs='?', default='/dev/ttyACM0', help='Serial port (default: /dev/ttyACM0)')
    parser.add_argument('--raw', action='store_true', help='Test raw AT command only')
    parser.add_argument('--parsed', action='store_true', help='Test parsed result only')

    args = parser.parse_args()

    if args.raw:
        test_creg_raw(args.port)
    elif args.parsed:
        test_creg_parsed(args.port)
    else:
        # Run both tests
        test_creg_raw(args.port)
        test_creg_parsed(args.port)
