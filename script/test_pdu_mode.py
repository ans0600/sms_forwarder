#!/usr/bin/env python3
"""
Test PDU mode for reading SMS - might be more reliable than text mode
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
    print("Comparing Text Mode vs PDU Mode")
    print("="*80)

    print("\n--- TEXT MODE ---")
    send_at(ser, 'AT+CMGF=1')
    send_at(ser, 'AT+CPMS="ME"', 0.3)
    text_response = send_at(ser, 'AT+CMGL="ALL"', 1.0)

    print("\n--- PDU MODE ---")
    send_at(ser, 'AT+CMGF=0')
    send_at(ser, 'AT+CPMS="ME"', 0.3)
    pdu_response = send_at(ser, 'AT+CMGL=4', 1.0)  # 4 = all messages

    print("\n" + "="*80)
    print("Analysis")
    print("="*80)

    print("\nTEXT MODE Response:")
    print(repr(text_response))

    print("\nPDU MODE Response:")
    print(repr(pdu_response))

    # Extract just the first message from each
    print("\n" + "="*80)
    print("First Message Comparison")
    print("="*80)

    text_lines = text_response.strip().split('\n')
    pdu_lines = pdu_response.strip().split('\n')

    print("\nTEXT mode first message:")
    for i, line in enumerate(text_lines[:3]):
        print(f"  Line {i}: {repr(line)}")

    print("\nPDU mode first message:")
    for i, line in enumerate(pdu_lines[:3]):
        print(f"  Line {i}: {repr(line)}")

    # Switch back to text mode
    send_at(ser, 'AT+CMGF=1')

    ser.close()
    print("\nDone!")

if __name__ == "__main__":
    port = sys.argv[1] if len(sys.argv) > 1 else '/dev/ttyACM0'
    main(port)
