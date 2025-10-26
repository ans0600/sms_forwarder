#!/usr/bin/env python3
"""
Clear all SMS messages from the device
"""

import gammu
import sys

def clear_all_sms(port='/dev/ttyACM0'):
    """Delete all SMS messages"""

    print(f"\n⚠️  WARNING: This will delete ALL SMS messages from {port}")
    print("Press Ctrl+C to cancel, or Enter to continue...")
    try:
        input()
    except KeyboardInterrupt:
        print("\nCancelled")
        return

    try:
        sm = gammu.StateMachine()
        sm.SetConfig(0, {'Device': port, 'Connection': 'at'})
        sm.Init()

        print("\nDeleting SMS messages...")
        deleted = 0

        # Check all folders
        for folder in [0, 1, 2, 3]:
            try:
                start = True
                while True:
                    try:
                        if start:
                            sms = sm.GetNextSMS(Start=True, Folder=folder)
                            start = False
                        else:
                            sms = sm.GetNextSMS(Location=sms[0]['Location'], Folder=folder)

                        for message in sms:
                            sm.DeleteSMS(Folder=folder, Location=message['Location'])
                            deleted += 1
                            print(f"  Deleted SMS from folder {folder}, location {message['Location']}")

                    except gammu.ERR_EMPTY:
                        break
            except gammu.ERR_EMPTY:
                pass

        print(f"\n✓ Deleted {deleted} SMS message(s)")
        sm.Terminate()

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    port = sys.argv[1] if len(sys.argv) > 1 else '/dev/ttyACM0'
    clear_all_sms(port)
