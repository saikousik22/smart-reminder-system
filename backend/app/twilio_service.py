"""
Twilio Voice API integration for making automated reminder calls.
"""

import logging
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def get_twilio_client() -> Client:
    """Create and return a Twilio REST client."""
    return Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)


def make_reminder_call(phone_number: str, reminder_id: int) -> str:
    """
    Initiate an outbound voice call via Twilio.

    Args:
        phone_number: The user's phone number to call (E.164 format).
        reminder_id: The reminder ID, used to construct the webhook URL.

    Returns:
        The Twilio Call SID on success.

    Raises:
        TwilioRestException: If the call fails.
    """
    client = get_twilio_client()
    webhook_url = f"{settings.PUBLIC_BASE_URL}/voice/{reminder_id}"

    logger.info(f"Initiating call to {phone_number} with webhook {webhook_url}")

    status_callback_url = f"{settings.PUBLIC_BASE_URL}/voice/status/{reminder_id}"

    try:
        call = client.calls.create(
            to=phone_number,
            from_=settings.TWILIO_PHONE_NUMBER,
            url=webhook_url,
            method="POST",
            status_callback=status_callback_url,
            status_callback_method="POST",
            status_callback_event=["completed", "no-answer", "busy", "failed"],
        )
        logger.info(f"Call initiated successfully. SID: {call.sid}")
        return call.sid
    except TwilioRestException as e:
        logger.error(f"Twilio call failed for reminder {reminder_id}: {e}")
        raise
