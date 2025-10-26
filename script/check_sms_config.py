#!/usr/bin/env python3
"""
Deep dive into SMS configuration using AT commands
Based on Air 780EP AT command reference
"""

import serial
import time
import sys

def send_at_command(ser, command, wait_time=1):
    """Send AT command and get response"""
    ser.write((command + '\r\n').encode())
    time.sleep(wait_time)
    response = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
    return response

def check_sms_configuration(port='/dev/ttyACM0', baudrate=115200):
    """Check SMS configuration using AT commands"""

    print("="*60)
    print("Air 780EPV SMS Configuration Check")
    print("="*60)
    print()

    try:
        # Open serial connection
        print(f"Opening serial port: {port}")
        ser = serial.Serial(port, baudrate, timeout=2)
        time.sleep(1)

        # Clear buffer
        ser.read(ser.in_waiting)

        print("✓ Connected\n")

        # Test basic AT
        print("1. Testing AT communication...")
        response = send_at_command(ser, 'AT')
        print(f"   AT -> {response.strip()}")
        if 'OK' not in response:
            print("   ✗ Device not responding properly")
            return False
        print()

        # Check SIM status
        print("2. Checking SIM card status...")
        response = send_at_command(ser, 'AT+CPIN?')
        print(f"   {response.strip()}")
        if 'READY' not in response:
            print("   ✗ SIM card not ready!")
            return False
        print()

        # Check network registration
        print("3. Checking network registration...")
        response = send_at_command(ser, 'AT+CREG?')
        print(f"   {response.strip()}")
        if ',1' in response or ',5' in response:
            print("   ✓ Registered on network")
        else:
            print("   ⚠ Not registered on network")
        print()

        # Check signal quality
        print("4. Checking signal quality...")
        response = send_at_command(ser, 'AT+CSQ')
        print(f"   {response.strip()}")
        print()

        # Check SMS format
        print("5. Checking SMS format...")
        response = send_at_command(ser, 'AT+CMGF?')
        print(f"   Current: {response.strip()}")

        # Set to text mode
        response = send_at_command(ser, 'AT+CMGF=1')
        print(f"   Setting to text mode: {response.strip()}")
        print()

        # Check SMS storage
        print("6. Checking SMS storage configuration...")
        response = send_at_command(ser, 'AT+CPMS?')
        print(f"   {response.strip()}")
        print()

        # Set SMS storage to read from all locations
        print("7. Setting SMS storage to SIM and Phone memory...")
        response = send_at_command(ser, 'AT+CPMS="SM","SM","SM"')
        print(f"   SIM: {response.strip()}")
        response = send_at_command(ser, 'AT+CPMS="ME","ME","ME"')
        print(f"   Phone: {response.strip()}")
        print()

        # Check SMS parameters
        print("8. Checking SMS parameters...")
        response = send_at_command(ser, 'AT+CSMP?')
        print(f"   {response.strip()}")
        print()

        # Check SMS service center
        print("9. Checking SMS Service Center (SMSC)...")
        response = send_at_command(ser, 'AT+CSCA?')
        print(f"   {response.strip()}")
        print()

        # Check new message indication
        print("10. Checking new SMS indication settings...")
        response = send_at_command(ser, 'AT+CNMI?')
        print(f"   Current: {response.strip()}")

        # Set to get SMS indication
        print("   Setting new message indication...")
        response = send_at_command(ser, 'AT+CNMI=2,1,0,0,0')
        print(f"   {response.strip()}")
        print()

        # List all SMS messages in text mode
        print("11. Listing ALL SMS messages (text mode)...")
        response = send_at_command(ser, 'AT+CMGL="ALL"', wait_time=3)
        print(f"   {response.strip()}")

        if '+CMGL:' in response:
            print("   ✓ Found SMS messages!")
        else:
            print("   ℹ No SMS messages found")
        print()

        # Check preferred message storage
        print("12. Checking preferred message storage...")
        response = send_at_command(ser, 'AT+CPMS="SM"')
        print(f"   SIM Memory: {response.strip()}")

        response = send_at_command(ser, 'AT+CMGL="ALL"', wait_time=3)
        if '+CMGL:' in response:
            print("   ✓ Found messages in SIM!")
            print(f"   {response}")
        else:
            print("   No messages in SIM")

        response = send_at_command(ser, 'AT+CPMS="ME"')
        print(f"\n   Phone Memory: {response.strip()}")

        response = send_at_command(ser, 'AT+CMGL="ALL"', wait_time=3)
        if '+CMGL:' in response:
            print("   ✓ Found messages in Phone memory!")
            print(f"   {response}")
        else:
            print("   No messages in Phone memory")
        print()

        # Check SMS status
        print("13. Getting detailed SMS status...")
        response = send_at_command(ser, 'AT+CPMS="SM"')
        print(f"   {response.strip()}")
        print()

        # Check if SMS reception is enabled
        print("14. Checking SMS reception status...")
        response = send_at_command(ser, 'AT+CNMA?')
        print(f"   {response.strip()}")
        print()

        # Check SMS overflow
        print("15. Checking for memory full condition...")
        response = send_at_command(ser, 'AT+CPMS?')
        if response:
            # Parse to see if memory is full
            print(f"   {response.strip()}")
            if 'FULL' in response.upper():
                print("   ⚠ SMS storage is full!")
            print()

        print("="*60)
        print("Configuration Check Complete!")
        print("="*60)
        print()
        print("Next steps:")
        print("1. Send a test SMS to your SIM card number")
        print("2. Wait 30 seconds")
        print("3. Run this script again to see if SMS appears")
        print("4. If still no SMS, check:")
        print("   - SMS not expired (sent recently)")
        print("   - Sender number is not blocked")
        print("   - SIM has SMS capability enabled")
        print()

        ser.close()
        return True

    except serial.SerialException as e:
        print(f"\n✗ Serial Error: {e}")
        print("\nTry running with sudo:")
        print(f"  sudo python3 {sys.argv[0]} {port}")
        return False
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    port = sys.argv[1] if len(sys.argv) > 1 else '/dev/ttyACM0'

    print()
    check_sms_configuration(port)
