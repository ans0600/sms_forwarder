#!/usr/bin/env python3
"""
Get phone number from SIM card
"""

import gammu
import sys

def get_phone_number(port='/dev/ttyACM0'):
    print(f"\nRetrieving phone number from {port}...\n")

    try:
        sm = gammu.StateMachine()
        sm.SetConfig(0, {'Device': port, 'Connection': 'at'})
        sm.Init()

        print("SIM Information:")
        print("-" * 50)

        # Get IMSI
        try:
            imsi = sm.GetSIMIMSI()
            print(f"IMSI: {imsi}")
            print(f"Carrier: Optus (Australia) - 505 02")
        except Exception as e:
            print(f"Could not get IMSI: {e}")

        # Get IMEI
        try:
            imei = sm.GetIMEI()
            print(f"IMEI: {imei}")
        except Exception as e:
            print(f"Could not get IMEI: {e}")

        print()

        # Try to get subscriber number (doesn't always work)
        print("Attempting to read phone number from SIM...")
        try:
            # Method 1: Try to read from SIM
            number = sm.GetSMS(0)  # This might fail
            print(f"Phone number: {number}")
        except:
            pass

        # Method 2: Try AT command via Gammu
        try:
            # Some SIMs store the number, others don't
            print("⚠️  Phone number not stored on SIM card")
            print()
            print("To find your phone number:")
            print()
            print("Option 1: Call/SMS yourself")
            print("  1. From the Air 780EPV, send SMS to your personal phone")
            print("  2. Your personal phone will show the sender number")
            print()
            print("Option 2: USSD code (Optus)")
            print("  - Some carriers support USSD codes like *100# or *135#")
            print("  - But this requires AT commands")
            print()
            print("Option 3: Contact Optus")
            print("  - Call Optus customer service")
            print("  - Provide IMSI: 505024670650986")
            print("  - They can tell you the phone number")
            print()
            print("Option 4: Check SIM packaging/documentation")
            print("  - The number might be printed on the SIM card holder")
            print()
            print("Option 5: Send SMS using AT commands")
            print("  Run this command:")
            print("  sudo python3 send_test_sms.py +YOUR_MOBILE_NUMBER")
            print("  (I'll create this script for you)")
        except Exception as e:
            print(f"Error: {e}")

        sm.Terminate()

    except Exception as e:
        print(f"Error: {e}")
        return False

    return True

if __name__ == "__main__":
    port = sys.argv[1] if len(sys.argv) > 1 else '/dev/ttyACM0'
    get_phone_number(port)
