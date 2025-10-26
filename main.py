#!/usr/bin/env python3
"""
SMS Forwarder for Air 780EPV Devices
Main entry point for the application

Receives SMS from 2 Air 780EPV devices and forwards them to Telegram
"""

import logging
import sys
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

import config
from sms_forwarder_at import SMSForwarderAT as SMSForwarder


def setup_logging():
    """Configure logging for the application"""
    log_handlers = [logging.StreamHandler()]

    # Add file handler if configured
    if config.LOG_FILE:
        log_handlers.append(
            logging.FileHandler(config.LOG_FILE)
        )

    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL.upper()),
        format=config.LOG_FORMAT,
        handlers=log_handlers
    )


def validate_config() -> bool:
    """
    Validate configuration settings

    Returns:
        True if configuration is valid
    """
    logger = logging.getLogger(__name__)

    # Check Telegram configuration
    if config.TELEGRAM_BOT_TOKEN == 'YOUR_TELEGRAM_BOT_TOKEN':
        logger.error("Please set TELEGRAM_BOT_TOKEN in config.py or environment variable")
        return False

    if config.TELEGRAM_CHAT_ID == 'YOUR_TELEGRAM_CHAT_ID':
        logger.error("Please set TELEGRAM_CHAT_ID in config.py or environment variable")
        return False

    # Check device configuration
    if not config.DEVICES:
        logger.error("No devices configured in config.py")
        return False

    for i, device in enumerate(config.DEVICES):
        if 'name' not in device or 'port' not in device:
            logger.error(f"Device {i} is missing 'name' or 'port' configuration")
            return False

    logger.info("Configuration validated successfully")
    return True


def main():
    """Main entry point"""
    # Setup logging
    setup_logging()

    logger = logging.getLogger(__name__)
    logger.info("="*60)
    logger.info("SMS Forwarder for Air 780EPV Devices")
    logger.info("Using AT Commands mode")
    logger.info("="*60)

    # Validate configuration
    if not validate_config():
        logger.error("Configuration validation failed. Exiting.")
        sys.exit(1)

    # Create and start forwarder
    try:
        forwarder = SMSForwarder(
            telegram_token=config.TELEGRAM_BOT_TOKEN,
            telegram_chat_id=config.TELEGRAM_CHAT_ID,
            devices=config.DEVICES,
            poll_interval=config.POLL_INTERVAL,
            delete_after_forward=config.DELETE_AFTER_FORWARD
        )

        forwarder.start()

    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
