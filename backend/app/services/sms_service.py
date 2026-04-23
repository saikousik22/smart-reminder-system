"""
Twilio SMS utility.  Sends a single SMS message and returns True on success.
"""

import logging
from twilio.rest import Client
from app.config import get_settings

logger = logging.getLogger(__name__)


def send_sms(to: str, message: str) -> bool:
    """Send an SMS via Twilio.  Returns True on success, False on any error."""
    settings = get_settings()
    if not all([settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN, settings.TWILIO_PHONE_NUMBER]):
        logger.error("Twilio credentials are not fully configured — cannot send SMS.")
        return False
    try:
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        msg = client.messages.create(
            body=message,
            from_=settings.TWILIO_PHONE_NUMBER,
            to=to,
        )
        logger.info(f"SMS sent to {to}: SID={msg.sid}")
        return True
    except Exception as exc:
        logger.error(f"Failed to send SMS to {to}: {exc}")
        return False
