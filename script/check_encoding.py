#!/usr/bin/env python3
"""
Check and test different character encoding settings on Air 780EPV
"""

import serial
import time
import sys

def send_at(ser, command, wait=0.5):
    """Send AT command and get response"""
    ser.read(ser.in_waiting)  # Clear buffer
    print(f"\n> {command}")
    ser.write(f'{command}\r\n'.encode())
    time.sleep(wait)
    response = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
    print(response)
    return response

def main(port='/dev/ttyACM0'):
    print(f"Opening {port}...")
    ser = serial.Serial(port, 115200, timeout=2)
    time.sleep(0.5)

    print("="*80)
    print("Checking Current Encoding Configuration")
    print("="*80)

    # Check message format
    send_at(ser, 'AT+CMGF?')

    # Check character set
    send_at(ser, 'AT+CSCS?')

    # List supported character sets
    send_at(ser, 'AT+CSCS=?')

    print("\n" + "="*80)
    print("Testing Different Character Sets")
    print("="*80)

    # Try different character sets
    for charset in ['GSM', 'IRA', 'UCS2', 'HEX', 'PCCP936']:
        print(f"\n--- Testing charset: {charset} ---")
        response = send_at(ser, f'AT+CSCS="{charset}"', 0.3)

        if 'OK' in response:
            print(f"✓ Set to {charset}, reading SMS...")
            send_at(ser, 'AT+CPMS="ME"', 0.3)
            send_at(ser, 'AT+CMGL="ALL"', 1.0)
        else:
            print(f"✗ {charset} not supported")

    print("\n" + "="*80)
    print("Testing PDU Mode")
    print("="*80)

    # Switch to PDU mode
    send_at(ser, 'AT+CMGF=0')
    send_at(ser, 'AT+CPMS="ME"', 0.3)
    send_at(ser, 'AT+CMGL=4', 1.0)  # All messages in PDU mode

    # Switch back to text mode
    print("\n" + "="*80)
    print("Switching back to Text Mode + UCS2")
    print("="*80)
    send_at(ser, 'AT+CMGF=1')
    send_at(ser, 'AT+CSCS="UCS2"')

    ser.close()
    print("\nDone!")

if __name__ == "__main__":
    port = sys.argv[1] if len(sys.argv) > 1 else '/dev/ttyACM0'
    main(port)
