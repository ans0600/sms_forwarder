#!/usr/bin/env python3
"""
Test pure AT command SMS operations (no Gammu)
"""

from sms_device_at import SMSDeviceAT
import sys

def test_at_commands(port='/dev/ttyACM0'):
    print("="*60)
    print("Testing Pure AT Command SMS Operations")
    print("="*60)
    print()

    # Create AT device
    device = SMSDeviceAT(port)
    device.device_name = "TestDevice"

    # Connect
    print(f"Connecting to {port}...")
    if not device.connect():
        print("Failed to connect!")
        return False

    print("✓ Connected\n")

    # Test basic AT
    print("1. Testing AT communication...")
    response = device.send_command('AT')
    print(f"   {response.strip()}\n")

    # Set text mode
    print("2. Setting SMS text mode...")
    response = device.send_command('AT+CMGF=1')
    print(f"   {response.strip()}\n")

    # Get SMS count from Phone Memory
    print("3. Checking SMS count in Phone Memory (ME)...")
    count_info = device.get_sms_count("ME")
    if count_info:
        print(f"   Used: {count_info['used']}/{count_info['total']}\n")
    else:
        print("   Failed to get count\n")

    # Read all SMS
    print("4. Reading all SMS from Phone Memory...")
    messages = device.read_all_sms("ME")
    print(f"   Found {len(messages)} SMS\n")

    if messages:
        for i, sms in enumerate(messages):
            print(f"   --- SMS {i+1} ---")
            print(f"   Index: {sms['index']}")
            print(f"   From: {sms['number']}")
            print(f"   Date: {sms['date']}")
            print(f"   Text: {sms['text']}")
            print(f"   Status: {sms['status']}")
            print()

        # Test deletion
        if len(messages) > 0:
            test_sms = messages[0]
            print(f"5. Testing deletion of SMS at index {test_sms['index']}...")
            response = input("   Delete this SMS? (y/n): ")
            if response.lower() == 'y':
                if device.delete_sms_at(test_sms['index'], "ME"):
                    print("   ✓ SMS deleted successfully\n")
                else:
                    print("   ✗ Failed to delete SMS\n")

    # Close
    device.close()
    print("="*60)
    print("Test Complete!")
    print("="*60)

    return True

if __name__ == "__main__":
    port = sys.argv[1] if len(sys.argv) > 1 else '/dev/ttyACM0'
    test_at_commands(port)
