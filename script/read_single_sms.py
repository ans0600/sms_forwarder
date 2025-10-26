#!/usr/bin/env python3
"""
Read a single SMS using AT+CMGR to see full message
Sometimes AT+CMGL truncates but AT+CMGR shows full content
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

def main(port='/dev/ttyACM0', index=0):
    print(f"Opening {port}...")
    ser = serial.Serial(port, 115200, timeout=2)
    time.sleep(0.5)

    print("="*80)
    print(f"Reading Single SMS at index {index}")
    print("="*80)

    # Set text mode
    send_at(ser, 'AT+CMGF=1')

    # Set storage
    send_at(ser, 'AT+CPMS="ME"', 0.3)

    print("\n--- Using AT+CMGL (list all) ---")
    list_response = send_at(ser, 'AT+CMGL="ALL"', 1.0)

    print("\n--- Using AT+CMGR (read single) ---")
    read_response = send_at(ser, f'AT+CMGR={index}', 1.0)

    print("\n" + "="*80)
    print("Comparison")
    print("="*80)

    print("\nAT+CMGL response:")
    print(repr(list_response))

    print("\nAT+CMGR response:")
    print(repr(read_response))

    # Try PDU mode too
    print("\n" + "="*80)
    print("PDU Mode Comparison")
    print("="*80)

    send_at(ser, 'AT+CMGF=0')
    send_at(ser, 'AT+CPMS="ME"', 0.3)

    print("\n--- PDU mode AT+CMGL ---")
    pdu_list = send_at(ser, 'AT+CMGL=4', 1.0)

    print("\n--- PDU mode AT+CMGR ---")
    pdu_read = send_at(ser, f'AT+CMGR={index}', 1.0)

    print("\nPDU CMGL:")
    print(repr(pdu_list))

    print("\nPDU CMGR:")
    print(repr(pdu_read))

    # Switch back
    send_at(ser, 'AT+CMGF=1')

    ser.close()
    print("\nDone!")

if __name__ == "__main__":
    port = sys.argv[1] if len(sys.argv) > 1 else '/dev/ttyACM0'
    index = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    main(port, index)
