#!/usr/bin/env python3
"""
Test script to debug SMS reception on Air 780EPV
"""

import gammu
import sys
import time

def test_device(port='/dev/ttyACM0'):
    """Test SMS reception on the device"""

    print(f"=" * 60)
    print(f"Testing SMS Reception on {port}")
    print(f"=" * 60)
    print()

    try:
        # Connect to device
        print("1. Connecting to device...")
        sm = gammu.StateMachine()
        sm.SetConfig(0, {
            'Device': port,
            'Connection': 'at',
        })
        sm.Init()
        print("   ✓ Connected successfully")
        print()

        # Get device info
        print("2. Getting device information...")
        try:
            manufacturer = sm.GetManufacturer()
            model = sm.GetModel()
            imei = sm.GetIMEI()
            print(f"   Manufacturer: {manufacturer}")
            print(f"   Model: {model[0] if isinstance(model, tuple) else model}")
            print(f"   IMEI: {imei}")
        except Exception as e:
            print(f"   ✗ Error getting device info: {e}")
        print()

        # Get SIM info
        print("3. Getting SIM card information...")
        try:
            imsi = sm.GetSIMIMSI()
            print(f"   SIM IMSI: {imsi}")

            network_info = sm.GetNetworkInfo()
            print(f"   Network State: {network_info.get('State', 'Unknown')}")
            print(f"   Network Code: {network_info.get('NetworkCode', 'Unknown')}")
            print(f"   Network Name: {network_info.get('NetworkName', 'Unknown')}")
        except Exception as e:
            print(f"   ✗ Error getting SIM info: {e}")
        print()

        # Get signal strength
        print("4. Getting signal strength...")
        try:
            signal = sm.GetSignalQuality()
            print(f"   Signal Strength: {signal.get('SignalPercent', -1)}%")
            print(f"   Signal dBm: {signal.get('SignalStrength', 'N/A')}")
        except Exception as e:
            print(f"   ✗ Error getting signal: {e}")
        print()

        # Check SMS storage
        print("5. Checking SMS storage...")
        try:
            status = sm.GetSMSStatus()
            print(f"   SIM Used: {status['SIMUsed']}/{status['SIMSize']}")
            print(f"   Phone Used: {status['PhoneUsed']}/{status['PhoneSize']}")
            print(f"   Total SMS: {status['SIMUsed'] + status['PhoneUsed']}")
        except Exception as e:
            print(f"   ✗ Error getting SMS status: {e}")
        print()

        # Read all SMS
        print("6. Reading all SMS messages...")
        try:
            # Try reading from all folders
            total_found = 0
            for folder_idx in range(4):  # 0=SM Inbox, 1=SM Outbox, 2=ME Inbox, 3=ME Outbox
                try:
                    start = True
                    count = 0
                    while True:
                        try:
                            if start:
                                sms = sm.GetNextSMS(Start=True, Folder=folder_idx)
                                start = False
                            else:
                                sms = sm.GetNextSMS(Location=sms[0]['Location'], Folder=folder_idx)

                            for message in sms:
                                if count == 0:
                                    print(f"   Found SMS in Folder {folder_idx}:")
                                count += 1
                                total_found += 1
                                print(f"   --- SMS #{count} ---")
                                print(f"   From: {message['Number']}")
                                print(f"   Date: {message['DateTime']}")
                                print(f"   Text: {message['Text']}")
                                print(f"   State: {message.get('State', 'Unknown')}")
                                print()
                        except gammu.ERR_EMPTY:
                            break
                except:
                    pass

            if total_found == 0:
                print("   ℹ No SMS messages found in any folder")
                print()
                print("   DEBUGGING:")
                print("   - Check if SIM card is inserted properly")
                print("   - Verify the SIM card number is correct")
                print("   - Try sending a test SMS to this number")
                print()
                print("   To find your SIM card phone number:")
                print("   sudo python3 send_test_sms.py +61YOUR_MOBILE")
        except gammu.ERR_EMPTY:
            print("   ℹ No SMS messages found (ERR_EMPTY)")
        except Exception as e:
            print(f"   ✗ Error reading SMS: {e}")
        print()

        # Test SMS folders
        print("7. Checking SMS folders/locations...")
        try:
            folders = sm.GetSMSFolders()
            print(f"   Available folders: {len(folders)}")
            for i, folder in enumerate(folders):
                print(f"   Folder {i}: {folder}")
        except Exception as e:
            print(f"   ✗ Error getting folders: {e}")
        print()

        # Get SMS settings
        print("8. Checking SMS settings...")
        try:
            # Try to get SMSC (SMS Center) number
            smsc = sm.GetSMSC()
            print(f"   SMS Center Number: {smsc.get('Number', 'Unknown')}")
            print(f"   SMS Center Name: {smsc.get('Name', 'Unknown')}")
        except Exception as e:
            print(f"   ✗ Error getting SMSC: {e}")
        print()

        print("=" * 60)
        print("Test Complete!")
        print("=" * 60)

        # Disconnect
        sm.Terminate()

    except gammu.GSMError as e:
        print(f"\n✗ Gammu Error: {e}")
        print(f"\nTroubleshooting:")
        print(f"- Check if device is connected: ls -l {port}")
        print(f"- Check permissions: Run with sudo or fix permissions")
        print(f"- Verify device is not being used by another program")
        return False
    except Exception as e:
        print(f"\n✗ Unexpected Error: {e}")
        return False

    return True


if __name__ == "__main__":
    port = sys.argv[1] if len(sys.argv) > 1 else '/dev/ttyACM0'

    print()
    print("Air 780EPV SMS Reception Test")
    print()

    if not test_device(port):
        sys.exit(1)

    print()
    print("TIP: If no SMS found, try:")
    print("1. Verify SIM card phone number")
    print("2. Send a test SMS from your phone")
    print("3. Wait 30 seconds and run this script again")
    print("4. Check if SMS Center (SMSC) number is configured")
    print()
