"""
SQLite database for storing notification history
"""

import sqlite3
import logging
import os
from datetime import datetime
from typing import Optional, List, Dict
from pathlib import Path

logger = logging.getLogger(__name__)


class NotificationDB:
    """SQLite database for notification history"""

    def __init__(self, db_path: str = "data/notifications.db"):
        """
        Initialize database connection

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path

        # Ensure data directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        self.conn = None
        self._connect()
        self._create_tables()

    def _connect(self):
        """Connect to SQLite database"""
        try:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row  # Enable column access by name
            logger.info(f"Connected to notification database: {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    def _create_tables(self):
        """Create tables if they don't exist"""
        try:
            cursor = self.conn.cursor()

            # Notifications table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_name TEXT NOT NULL,
                    notification_type TEXT NOT NULL,
                    phone_number TEXT,
                    message TEXT,
                    timestamp DATETIME NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create indexes for common queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_device_name
                ON notifications(device_name)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp
                ON notifications(timestamp)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_notification_type
                ON notifications(notification_type)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_phone_number
                ON notifications(phone_number)
            """)

            self.conn.commit()
            logger.info("Database tables initialized")

        except Exception as e:
            logger.error(f"Failed to create tables: {e}")
            raise

    def log_sms(self, device_name: str, phone_number: str, message: str, timestamp: datetime) -> Optional[int]:
        """
        Log an SMS notification

        Args:
            device_name: Name of the device that received the SMS
            phone_number: Sender's phone number
            message: SMS message content
            timestamp: When the SMS was received

        Returns:
            Row ID of inserted record, or None if failed
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO notifications (device_name, notification_type, phone_number, message, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (device_name, 'SMS', phone_number, message, timestamp))

            self.conn.commit()
            row_id = cursor.lastrowid
            logger.debug(f"Logged SMS from {phone_number} on {device_name} (ID: {row_id})")
            return row_id

        except Exception as e:
            logger.error(f"Failed to log SMS: {e}")
            return None

    def log_call(self, device_name: str, phone_number: str, timestamp: datetime) -> Optional[int]:
        """
        Log an incoming call notification

        Args:
            device_name: Name of the device that received the call
            phone_number: Caller's phone number
            timestamp: When the call was received

        Returns:
            Row ID of inserted record, or None if failed
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO notifications (device_name, notification_type, phone_number, message, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (device_name, 'CALL', phone_number, None, timestamp))

            self.conn.commit()
            row_id = cursor.lastrowid
            logger.debug(f"Logged call from {phone_number} on {device_name} (ID: {row_id})")
            return row_id

        except Exception as e:
            logger.error(f"Failed to log call: {e}")
            return None

    def get_recent_notifications(self, limit: int = 100, notification_type: Optional[str] = None) -> List[Dict]:
        """
        Get recent notifications

        Args:
            limit: Maximum number of records to return
            notification_type: Filter by type ('SMS' or 'CALL'), or None for all

        Returns:
            List of notification dictionaries
        """
        try:
            cursor = self.conn.cursor()

            if notification_type:
                cursor.execute("""
                    SELECT id, device_name, notification_type, phone_number, message, timestamp, created_at
                    FROM notifications
                    WHERE notification_type = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (notification_type, limit))
            else:
                cursor.execute("""
                    SELECT id, device_name, notification_type, phone_number, message, timestamp, created_at
                    FROM notifications
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (limit,))

            rows = cursor.fetchall()
            return [dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Failed to get recent notifications: {e}")
            return []

    def get_notifications_by_number(self, phone_number: str, limit: int = 50) -> List[Dict]:
        """
        Get all notifications from a specific phone number

        Args:
            phone_number: Phone number to search for
            limit: Maximum number of records to return

        Returns:
            List of notification dictionaries
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT id, device_name, notification_type, phone_number, message, timestamp, created_at
                FROM notifications
                WHERE phone_number = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (phone_number, limit))

            rows = cursor.fetchall()
            return [dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Failed to get notifications by number: {e}")
            return []

    def get_stats(self) -> Dict:
        """
        Get notification statistics

        Returns:
            Dictionary with statistics
        """
        try:
            cursor = self.conn.cursor()

            # Total counts
            cursor.execute("SELECT COUNT(*) FROM notifications")
            total = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM notifications WHERE notification_type = 'SMS'")
            total_sms = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM notifications WHERE notification_type = 'CALL'")
            total_calls = cursor.fetchone()[0]

            # Recent counts (last 24 hours)
            cursor.execute("""
                SELECT COUNT(*) FROM notifications
                WHERE timestamp > datetime('now', '-1 day')
            """)
            recent_24h = cursor.fetchone()[0]

            return {
                'total': total,
                'total_sms': total_sms,
                'total_calls': total_calls,
                'recent_24h': recent_24h
            }

        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {}

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
