#!/usr/bin/env python3
"""
Send a test SMS from the Air 780EPV to discover its phone number
"""

import gammu
import sys

def send_sms(to_number, port='/dev/ttyACM0'):
    """Send SMS and the recipient will see the sender's number"""

    if not to_number:
        print("Usage: sudo python3 send_test_sms.py +61412345678")
        print()
        print("This will send a test SMS from the Air 780EPV to your phone.")
        print("Your phone will display the sender's number (the SIM card number).")
        return False

    # Ensure number has country code
    if not to_number.startswith('+'):
        print(f"⚠️  Adding +61 (Australia) prefix to {to_number}")
        to_number = '+61' + to_number.lstrip('0')

    print(f"\nSending test SMS to: {to_number}")
    print(f"Using device: {port}")
    print()

    try:
        sm = gammu.StateMachine()
        sm.SetConfig(0, {'Device': port, 'Connection': 'at'})
        sm.Init()

        # Create SMS message
        message = {
            'Text': 'Test SMS from Air 780EPV. Reply to this message or check the sender number!',
            'SMSC': {'Location': 1},
            'Number': to_number,
        }

        print("Sending SMS...")
        sm.SendSMS(message)
        print("✓ SMS sent successfully!")
        print()
        print("Check your phone:")
        print("1. You should receive the SMS in a few seconds")
        print("2. The sender number is the Air 780EPV's phone number")
        print("3. Save that number and send SMS to it for testing")
        print()

        sm.Terminate()
        return True

    except gammu.GSMError as e:
        print(f"✗ Gammu Error: {e}")
        print()
        print("Troubleshooting:")
        print("- Check signal strength (should be > 20%)")
        print("- Verify SMS Center is configured: +61411990001")
        print("- Check network registration")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("=" * 60)
        print("Air 780EPV - Send Test SMS to Discover Phone Number")
        print("=" * 60)
        print()
        print("Usage:")
        print("  sudo python3 send_test_sms.py +61412345678")
        print("  sudo python3 send_test_sms.py 0412345678")
        print()
        print("This will send a test SMS from your Air 780EPV to your")
        print("personal phone. You'll see the sender's number, which is")
        print("the Air 780EPV's phone number.")
        print()
        sys.exit(1)

    to_number = sys.argv[1]
    port = sys.argv[2] if len(sys.argv) > 2 else '/dev/ttyACM0'

    send_sms(to_number, port)
