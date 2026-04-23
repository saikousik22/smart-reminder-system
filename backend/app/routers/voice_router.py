"""
Twilio Voice webhook router.
Returns TwiML XML that instructs Twilio to play the reminder's audio file,
and receives Twilio call-status callbacks to update delivery status.

Retry + SMS fallback logic (applied in the status callback):
  - CASE 1 (no retries): any failure → send SMS immediately
  - CASE 2 (retries enabled, not final attempt): schedule next retry call
  - CASE 3 (retries enabled, final attempt failed): send SMS fallback
  - CASE 4 (any attempt answered): mark complete, skip SMS

Idempotency: fallback_sent flag is checked before every SMS send so the
message is delivered at most once, even if Twilio fires the callback twice.

Security: Twilio webhook signature is validated on every request.
If TWILIO_AUTH_TOKEN is absent the endpoint raises 403 rather than
processing unauthenticated webhooks.
"""

import logging
from xml.sax.saxutils import escape as xml_escape
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import Response
from sqlalchemy.orm import Session
from twilio.request_validator import RequestValidator
from app.database import get_db
from app.models import Reminder
from app.config import get_settings
from app.scheduler import _schedule_retry, _schedule_next_occurrence
from app.services.sms_service import send_sms

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(tags=["Twilio Voice Webhook"])

_TWILIO_STATUS_MAP = {
    "completed": "answered",
    "no-answer": "no-answer",
    "busy": "busy",
    "failed": "failed",
    "canceled": "failed",
}

_FAILURE_STATUSES = {"no-answer", "busy", "failed"}


def _validate_twilio_signature(request: Request, params: dict, path: str) -> None:
    """Raise 403 if the request does not carry a valid Twilio signature."""
    if not settings.TWILIO_AUTH_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Twilio webhook validation is not configured. Set TWILIO_AUTH_TOKEN.",
        )
    validator = RequestValidator(settings.TWILIO_AUTH_TOKEN)
    signature = request.headers.get("X-Twilio-Signature", "")
    url = f"{settings.PUBLIC_BASE_URL}{path}"
    if not validator.validate(url, params, signature):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid Twilio signature")


def _try_send_fallback_sms(db: Session, reminder: Reminder) -> None:
    """Send an SMS fallback for *reminder* if not already sent (idempotent).

    Message priority:
      1. reminder.fallback_text  (user-provided / translated text)
      2. "You missed a reminder: <original_text>"
      3. "You missed a reminder: <title>"
    """
    if reminder.fallback_sent:
        logger.info(f"Reminder {reminder.id}: SMS fallback already sent — skipping.")
        return

    message = reminder.fallback_text
    if not message:
        source = reminder.original_text or reminder.title
        message = f"You missed a reminder: {source}"

    success = send_sms(reminder.phone_number, message)
    if success:
        reminder.fallback_sent = True
        logger.info(f"Reminder {reminder.id}: SMS fallback sent to {reminder.phone_number}.")
    else:
        logger.error(f"Reminder {reminder.id}: SMS fallback failed for {reminder.phone_number}.")


# Status callback MUST be declared before /voice/{reminder_id} so FastAPI
# doesn't try to cast the literal string "status" to an integer reminder_id.
@router.post("/voice/status/{reminder_id}")
async def voice_status_callback(reminder_id: int, request: Request, db: Session = Depends(get_db)):
    """
    Twilio calls this endpoint when a call reaches a terminal state.
    Applies retry scheduling or SMS fallback based on reminder configuration.
    """
    form_data = await request.form()
    params = dict(form_data)

    _validate_twilio_signature(request, params, f"/voice/status/{reminder_id}")

    call_status = params.get("CallStatus", "")
    new_status = _TWILIO_STATUS_MAP.get(call_status)

    if not new_status:
        logger.debug(f"Reminder {reminder_id}: ignoring intermediate CallStatus='{call_status}'")
        return Response(status_code=200)

    reminder = db.query(Reminder).filter(Reminder.id == reminder_id).first()

    # Only transition from "calling" — avoids overwriting if the stuck-recovery
    # job already marked it "failed".
    if not reminder or reminder.status != "calling":
        return Response(status_code=200)

    reminder.status = new_status

    if new_status == "answered":
        # Successful call — schedule next recurrence if applicable, no SMS.
        if reminder.recurrence:
            _schedule_next_occurrence(db, reminder)
        logger.info(f"Reminder {reminder_id}: answered — no SMS fallback needed.")

    elif new_status in _FAILURE_STATUSES:
        # Determine whether a retry is still available.
        # retry_count=0  → no retries; attempt_number is always 1 for these.
        # retry_count=N  → N retries allowed; attempt N+1 is the final attempt.
        has_retries = reminder.retry_count > 0
        is_final_attempt = (not has_retries) or (reminder.attempt_number > reminder.retry_count)

        if not is_final_attempt:
            # More attempts remain — schedule the next retry call, skip SMS.
            _schedule_retry(db, reminder)
            logger.info(
                f"Reminder {reminder_id}: attempt {reminder.attempt_number} failed "
                f"({new_status}) — retry scheduled."
            )
        else:
            # Final attempt also failed — send SMS fallback (idempotent).
            if reminder.recurrence:
                _schedule_next_occurrence(db, reminder)
            _try_send_fallback_sms(db, reminder)
            logger.info(
                f"Reminder {reminder_id}: final attempt failed ({new_status}) — "
                f"SMS fallback attempted."
            )

    db.commit()
    logger.info(f"Reminder {reminder_id} status → '{new_status}' (Twilio CallStatus={call_status})")

    return Response(status_code=200)


@router.post("/voice/{reminder_id}")
async def voice_webhook(reminder_id: int, request: Request, db: Session = Depends(get_db)):
    """
    Twilio webhook endpoint called when the callee picks up the phone.
    Returns TwiML that plays the reminder's recorded audio.
    """
    form_data = await request.form()
    params = dict(form_data)

    _validate_twilio_signature(request, params, f"/voice/{reminder_id}")

    reminder = db.query(Reminder).filter(Reminder.id == reminder_id).first()

    if not reminder:
        twiml = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="alice">Sorry, the requested reminder was not found. Goodbye.</Say>
    <Hangup/>
</Response>"""
        return Response(content=twiml, media_type="application/xml")

    audio_url = xml_escape(f"{settings.PUBLIC_BASE_URL}/audio/{reminder.audio_filename}")

    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="alice">Hello! Here is your scheduled reminder.</Say>
    <Pause length="1"/>
    <Play>{audio_url}</Play>
    <Pause length="1"/>
    <Say voice="alice">This was your reminder from Smart Reminder System. Goodbye!</Say>
    <Hangup/>
</Response>"""

    return Response(content=twiml, media_type="application/xml")
