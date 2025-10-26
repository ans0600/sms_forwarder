"""
Telegram notification module for SMS Forwarder
"""

import logging
import requests
from typing import Optional


logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Handle Telegram notifications"""

    def __init__(self, bot_token: str, chat_id: str):
        """
        Initialize Telegram notifier

        Args:
            bot_token: Telegram bot token from @BotFather
            chat_id: Telegram chat ID to send messages to
        """
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    def send_message(self, message: str, parse_mode: str = 'HTML') -> bool:
        """
        Send message to Telegram

        Args:
            message: Message text to send
            parse_mode: Parse mode for message formatting (HTML or Markdown)

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            payload = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': parse_mode
            }
            response = requests.post(self.api_url, json=payload, timeout=10)
            response.raise_for_status()
            logger.info("Message sent to Telegram successfully")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send message to Telegram: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending to Telegram: {e}")
            return False

    def test_connection(self) -> bool:
        """
        Test Telegram bot connection

        Returns:
            True if connection is successful
        """
        try:
            test_url = f"https://api.telegram.org/bot{self.bot_token}/getMe"
            response = requests.get(test_url, timeout=10)
            response.raise_for_status()
            logger.info("Telegram connection test successful")
            return True
        except Exception as e:
            logger.error(f"Telegram connection test failed: {e}")
            return False
