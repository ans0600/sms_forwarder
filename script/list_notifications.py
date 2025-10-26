#!/usr/bin/env python3
"""
Test script to list all notifications from the database
"""
import sys
import os
from datetime import datetime

# Add parent directory to path to import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from notification_db import NotificationDB


def format_timestamp(ts):
    """Format timestamp for display"""
    if isinstance(ts, str):
        try:
            dt = datetime.fromisoformat(ts)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except:
            return ts
    elif isinstance(ts, datetime):
        return ts.strftime("%Y-%m-%d %H:%M:%S")
    return str(ts)


def list_all_notifications(db_path='data/notifications.db', limit=None):
    """List all notifications from the database"""

    if not os.path.exists(db_path):
        print(f"❌ Database not found at: {db_path}")
        return

    db = NotificationDB(db_path)

    # Get statistics
    stats = db.get_stats()
    print("\n" + "="*80)
    print("📊 DATABASE STATISTICS")
    print("="*80)
    print(f"Total Notifications: {stats.get('total', 0)}")
    print(f"  • SMS: {stats.get('total_sms', 0)}")
    print(f"  • Calls: {stats.get('total_calls', 0)}")
    print(f"Recent (24h): {stats.get('recent_24h', 0)}")

    # Get additional stats
    cursor = db.conn.cursor()
    cursor.execute("SELECT COUNT(DISTINCT phone_number) FROM notifications")
    unique_numbers = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(DISTINCT device_name) FROM notifications")
    devices_count = cursor.fetchone()[0]
    cursor.execute("SELECT MAX(timestamp) FROM notifications")
    latest = cursor.fetchone()[0]

    print(f"Unique Phone Numbers: {unique_numbers}")
    print(f"Active Devices: {devices_count}")
    if latest:
        print(f"Latest Notification: {format_timestamp(latest)}")
    print()

    # Get all notifications
    cursor = db.conn.cursor()

    if limit:
        query = """
            SELECT id, device_name, notification_type, phone_number, message, timestamp, created_at
            FROM notifications
            ORDER BY timestamp DESC
            LIMIT ?
        """
        cursor.execute(query, (limit,))
    else:
        query = """
            SELECT id, device_name, notification_type, phone_number, message, timestamp, created_at
            FROM notifications
            ORDER BY timestamp DESC
        """
        cursor.execute(query)

    notifications = cursor.fetchall()

    if not notifications:
        print("📭 No notifications in database")
        db.close()
        return

    print("="*80)
    print(f"📋 ALL NOTIFICATIONS ({len(notifications)} total)")
    print("="*80)
    print()

    for notif in notifications:
        id_num, device_name, notif_type, phone_number, message, timestamp, created_at = notif

        # Format the notification type
        type_emoji = "📧" if notif_type == "SMS" else "📞"

        print(f"{type_emoji} [{notif_type}] ID: {id_num}")
        print(f"   Device: {device_name}")
        print(f"   From: {phone_number}")
        print(f"   Time: {format_timestamp(timestamp)}")

        if message:
            # Truncate long messages for display
            display_msg = message[:100] + "..." if len(message) > 100 else message
            print(f"   Message: {display_msg}")

        print(f"   Created: {format_timestamp(created_at)}")
        print()

    db.close()


def list_by_device(db_path='data/notifications.db'):
    """List notifications grouped by device"""

    if not os.path.exists(db_path):
        print(f"❌ Database not found at: {db_path}")
        return

    db = NotificationDB(db_path)
    cursor = db.conn.cursor()

    # Get devices
    cursor.execute("""
        SELECT DISTINCT device_name
        FROM notifications
        ORDER BY device_name
    """)
    devices = [row[0] for row in cursor.fetchall()]

    print("\n" + "="*80)
    print("📱 NOTIFICATIONS BY DEVICE")
    print("="*80)
    print()

    for device in devices:
        cursor.execute("""
            SELECT notification_type, COUNT(*)
            FROM notifications
            WHERE device_name = ?
            GROUP BY notification_type
        """, (device,))

        counts = dict(cursor.fetchall())
        sms_count = counts.get('SMS', 0)
        call_count = counts.get('CALL', 0)

        print(f"📱 {device}")
        print(f"   SMS: {sms_count}, Calls: {call_count}, Total: {sms_count + call_count}")
        print()

    db.close()


def list_by_number(db_path='data/notifications.db'):
    """List notifications grouped by phone number"""

    if not os.path.exists(db_path):
        print(f"❌ Database not found at: {db_path}")
        return

    db = NotificationDB(db_path)
    cursor = db.conn.cursor()

    cursor.execute("""
        SELECT phone_number, notification_type, COUNT(*) as count
        FROM notifications
        GROUP BY phone_number, notification_type
        ORDER BY count DESC, phone_number
    """)

    results = cursor.fetchall()

    print("\n" + "="*80)
    print("📞 NOTIFICATIONS BY PHONE NUMBER")
    print("="*80)
    print()

    current_number = None
    for phone_number, notif_type, count in results:
        if phone_number != current_number:
            if current_number is not None:
                print()
            print(f"📞 {phone_number}")
            current_number = phone_number

        type_str = "SMS" if notif_type == "SMS" else "Calls"
        print(f"   {type_str}: {count}")

    print()
    db.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="List notifications from the database")
    parser.add_argument('--db', default='data/notifications.db', help='Path to database file')
    parser.add_argument('--limit', type=int, help='Limit number of notifications shown')
    parser.add_argument('--by-device', action='store_true', help='Group by device')
    parser.add_argument('--by-number', action='store_true', help='Group by phone number')

    args = parser.parse_args()

    if args.by_device:
        list_by_device(args.db)
    elif args.by_number:
        list_by_number(args.db)
    else:
        list_all_notifications(args.db, args.limit)
