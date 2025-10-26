#!/usr/bin/env python3
"""
Live SMS monitoring - shows SMS as they arrive in real-time
Uses AT commands to monitor for incoming SMS
"""

import serial
import time
import sys
from datetime import datetime

def monitor_sms(port='/dev/ttyACM0', baudrate=115200):
    """Monitor for incoming SMS in real-time"""

    print("="*60)
    print("Live SMS Monitor for Air 780EPV")
    print("="*60)
    print()
    print(f"Port: {port}")
    print(f"Press Ctrl+C to stop")
    print()
    print("Waiting for SMS... (send a test SMS now)")
    print("-"*60)
    print()

    try:
        ser = serial.Serial(port, baudrate, timeout=1)
        time.sleep(1)

        # Clear buffer
        ser.read(ser.in_waiting)

        # Set text mode
        ser.write(b'AT+CMGF=1\r\n')
        time.sleep(0.5)
        ser.read(ser.in_waiting)

        # Enable new message notification
        ser.write(b'AT+CNMI=2,1,0,0,0\r\n')
        time.sleep(0.5)
        ser.read(ser.in_waiting)

        print(f"[{datetime.now().strftime('%H:%M:%S')}] Monitoring started...")
        print()

        last_check = time.time()

        while True:
            # Check for unsolicited messages (like +CMTI)
            if ser.in_waiting > 0:
                data = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
                if data.strip():
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Received: {data.strip()}")

                    # Check if it's a new SMS notification
                    if '+CMTI:' in data or '+CMT:' in data:
                        print()
                        print("🎉 NEW SMS NOTIFICATION DETECTED!")
                        print()

                        # Wait a moment for SMS to be fully received
                        time.sleep(1)

                        # Read all SMS
                        ser.write(b'AT+CMGL="ALL"\r\n')
                        time.sleep(2)
                        response = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
                        print("SMS Content:")
                        print(response)
                        print("-"*60)
                        print()

            # Periodically check for SMS manually (every 10 seconds)
            if time.time() - last_check > 10:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Checking for SMS...")

                # Check SIM memory
                ser.write(b'AT+CPMS="SM"\r\n')
                time.sleep(0.5)
                response = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')

                if '+CPMS:' in response:
                    # Parse message count
                    import re
                    match = re.search(r'\+CPMS: "SM",(\d+),', response)
                    if match:
                        count = int(match.group(1))
                        if count > 0:
                            print(f"   Found {count} SMS in SIM memory!")
                            # Read them
                            ser.write(b'AT+CMGL="ALL"\r\n')
                            time.sleep(2)
                            sms_data = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
                            print(sms_data)
                        else:
                            print("   No SMS in SIM memory")

                # Check Phone memory
                ser.write(b'AT+CPMS="ME"\r\n')
                time.sleep(0.5)
                response = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')

                if '+CPMS:' in response:
                    import re
                    match = re.search(r'\+CPMS: "ME",(\d+),', response)
                    if match:
                        count = int(match.group(1))
                        if count > 0:
                            print(f"   Found {count} SMS in Phone memory!")
                            # Read them
                            ser.write(b'AT+CMGL="ALL"\r\n')
                            time.sleep(2)
                            sms_data = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
                            print(sms_data)
                        else:
                            print("   No SMS in Phone memory")

                print()
                last_check = time.time()

            time.sleep(0.1)

    except KeyboardInterrupt:
        print()
        print("Monitoring stopped by user")
    except serial.SerialException as e:
        print(f"Serial Error: {e}")
        print(f"\nTry running with sudo:")
        print(f"  sudo python3 {sys.argv[0]} {port}")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            ser.close()
        except:
            pass

if __name__ == "__main__":
    port = sys.argv[1] if len(sys.argv) > 1 else '/dev/ttyACM0'

    print()
    monitor_sms(port)
