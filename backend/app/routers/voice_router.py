"""
Twilio Voice webhook router.
Returns TwiML XML that instructs Twilio to play the reminder's audio file,
and receives Twilio call-status callbacks to update delivery status.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import Response
from sqlalchemy.orm import Session
from twilio.request_validator import RequestValidator
from app.database import get_db
from app.models import Reminder
from app.config import get_settings
from app.scheduler import _schedule_retry

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(tags=["Twilio Voice Webhook"])

# Map Twilio CallStatus values to our internal statuses
_TWILIO_STATUS_MAP = {
    "completed": "answered",
    "no-answer": "no-answer",
    "busy": "busy",
    "failed": "failed",
    "canceled": "failed",
}


def _validate_twilio_signature(request: Request, params: dict, path: str) -> None:
    """Raise 403 if the request does not carry a valid Twilio signature."""
    if not settings.TWILIO_AUTH_TOKEN:
        return
    validator = RequestValidator(settings.TWILIO_AUTH_TOKEN)
    signature = request.headers.get("X-Twilio-Signature", "")
    url = f"{settings.PUBLIC_BASE_URL}{path}"
    if not validator.validate(url, params, signature):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid Twilio signature")


# ── Status callback — must be defined BEFORE /voice/{reminder_id} so FastAPI
#    doesn't try to parse the literal "status" as an integer reminder_id.
@router.post("/voice/status/{reminder_id}")
async def voice_status_callback(reminder_id: int, request: Request, db: Session = Depends(get_db)):
    """
    Twilio calls this endpoint when a call reaches a terminal state.
    Maps the Twilio CallStatus to our internal delivery status.
    """
    form_data = await request.form()
    params = dict(form_data)

    _validate_twilio_signature(request, params, f"/voice/status/{reminder_id}")

    call_status = params.get("CallStatus", "")
    new_status = _TWILIO_STATUS_MAP.get(call_status)

    if new_status:
        reminder = db.query(Reminder).filter(Reminder.id == reminder_id).first()
        # Only transition from "calling" — avoids overwriting if the
        # stuck-recovery job already marked it "failed"
        if reminder and reminder.status == "calling":
            reminder.status = new_status
            if new_status != "answered":
                _schedule_retry(db, reminder)
            db.commit()
            logger.info(
                f"Reminder {reminder_id} delivery status → '{new_status}' "
                f"(Twilio CallStatus={call_status})"
            )
    else:
        logger.debug(f"Reminder {reminder_id}: ignoring intermediate CallStatus='{call_status}'")

    # Twilio ignores the response body for status callbacks
    return Response(status_code=200)


@router.post("/voice/{reminder_id}")
async def voice_webhook(reminder_id: int, request: Request, db: Session = Depends(get_db)):
    """
    Twilio webhook endpoint.
    Called by Twilio when the user picks up the phone.
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

    audio_url = f"{settings.PUBLIC_BASE_URL}/audio/{reminder.audio_filename}"

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
