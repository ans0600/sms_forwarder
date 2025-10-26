#!/usr/bin/env python3
"""
Debug script - Show RAW AT command responses
"""

import serial
import time
import sys

def debug_sms(port='/dev/ttyACM0'):
    print("="*60)
    print("Raw SMS Debug Script")
    print("="*60)
    print()

    try:
        ser = serial.Serial(port, 115200, timeout=2)
        time.sleep(0.5)
        ser.read(ser.in_waiting)  # Clear buffer

        # Test AT
        print("1. Testing AT...")
        ser.write(b'AT\r\n')
        time.sleep(0.5)
        response = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
        print(f"Response: {response.strip()}\n")

        # Check current mode
        print("2. Checking current SMS mode...")
        ser.write(b'AT+CMGF?\r\n')
        time.sleep(0.5)
        response = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
        print(f"Response: {response.strip()}")
        print()

        # Try setting text mode
        print("3. Setting text mode (AT+CMGF=1)...")
        ser.write(b'AT+CMGF=1\r\n')
        time.sleep(0.5)
        response = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
        print(f"Response: {response.strip()}\n")

        # Verify
        print("4. Verifying mode...")
        ser.write(b'AT+CMGF?\r\n')
        time.sleep(0.5)
        response = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
        print(f"Response: {response.strip()}\n")

        # Set storage
        print("5. Setting storage to ME...")
        ser.write(b'AT+CPMS="ME"\r\n')
        time.sleep(0.5)
        response = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
        print(f"Response: {response.strip()}\n")

        # List all SMS
        print("6. Listing ALL SMS (AT+CMGL=\"ALL\")...")
        print("-"*60)
        ser.write(b'AT+CMGL="ALL"\r\n')
        time.sleep(2.0)
        response = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
        print("RAW RESPONSE:")
        print(response)
        print("-"*60)
        print()

        # Show line by line
        print("7. Line-by-line breakdown:")
        print("-"*60)
        lines = response.split('\n')
        for i, line in enumerate(lines):
            print(f"Line {i}: {repr(line)}")
        print("-"*60)
        print()

        # Try PDU mode
        print("8. Trying PDU mode (AT+CMGF=0)...")
        ser.write(b'AT+CMGF=0\r\n')
        time.sleep(0.5)
        response = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
        print(f"Response: {response.strip()}\n")

        print("9. Listing SMS in PDU mode...")
        print("-"*60)
        ser.write(b'AT+CMGL=4\r\n')  # 4 = all messages in PDU mode
        time.sleep(2.0)
        response = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
        print("RAW PDU RESPONSE:")
        print(response)
        print("-"*60)

        ser.close()

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    port = sys.argv[1] if len(sys.argv) > 1 else '/dev/ttyACM0'
    debug_sms(port)
