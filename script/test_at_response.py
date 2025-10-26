#!/usr/bin/env python3
"""
Test actual AT command response format
"""

import serial
import time
import sys

def test_at_response(port='/dev/ttyACM0'):
    """Test actual AT+CMGL response"""

    print(f"Opening {port}...")
    try:
        ser = serial.Serial(port, 115200, timeout=2)
        time.sleep(0.5)

        # Clear buffer
        ser.read(ser.in_waiting)

        print("\n=== Setting text mode ===")
        ser.write(b'AT+CMGF=1\r\n')
        time.sleep(0.5)
        response = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
        print(response)

        print("\n=== Verifying text mode ===")
        ser.write(b'AT+CMGF?\r\n')
        time.sleep(0.3)
        response = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
        print(response)

        print("\n=== Setting storage to ME ===")
        ser.write(b'AT+CPMS="ME"\r\n')
        time.sleep(0.5)
        response = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
        print(response)

        print("\n=== Reading all SMS (AT+CMGL) ===")
        ser.write(b'AT+CMGL="ALL"\r\n')
        time.sleep(2.0)
        response = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')

        print("Raw response:")
        print(repr(response))
        print("\n" + "="*80)
        print("Formatted response:")
        print(response)
        print("="*80)

        # Analyze line by line
        print("\n=== Line-by-line analysis ===")
        lines = response.split('\n')
        for idx, line in enumerate(lines):
            print(f"Line {idx}: {repr(line)}")
            if line.strip().startswith('+CMGL:'):
                print(f"  ^ This is a header line")
            elif not line.strip():
                print(f"  ^ This is an empty line")
            elif all(c in '0123456789ABCDEFabcdef \r' for c in line):
                print(f"  ^ This looks like hex data (length={len(line.strip())})")

        ser.close()

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    port = sys.argv[1] if len(sys.argv) > 1 else '/dev/ttyACM0'
    test_at_response(port)
