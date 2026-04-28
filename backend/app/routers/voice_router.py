"""
Twilio Voice webhook router.
Returns TwiML XML that instructs Twilio to play the reminder's audio file,
and receives Twilio call-status callbacks to update delivery status.

Failure classification:
  - completed                → answered (user picked up)
  - no-answer / busy        → USER FAILURE  (phone rang, user didn't answer)
  - failed / canceled       → SYSTEM FAILURE (Twilio couldn't connect; carrier/network issue)

User-failure retry logic (status callback):
  - CASE 1 (no retries): user failure → send SMS immediately
  - CASE 2 (retries enabled, not final attempt): schedule next retry call
  - CASE 3 (retries enabled, final attempt failed): send SMS fallback
  - CASE 4 (answered): mark complete, skip SMS

System-failure retry logic (status callback):
  - CASE A (system retries remain): backoff 30s→60s, re-enqueue via _handle_system_failure
  - CASE B (system retries exhausted → failed_system): schedule next recurrence + SMS fallback

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
from app.tasks import enqueue_reminder_eta, _handle_system_failure
from app.services.blob_storage import generate_sas_url

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(tags=["Twilio Voice Webhook"])

# Twilio terminal call statuses — all others are intermediate (ringing, in-progress, etc.)
_TERMINAL_CALL_STATUSES = {"completed", "no-answer", "busy", "failed", "canceled"}

# User-side failures: phone rang but the person didn't answer or was busy.
# These consume user retry budget (reminder.retry_count / attempt_number).
_USER_FAILURE_STATUSES = {"no-answer", "busy"}

# System-side failures: Twilio could not connect the call at all — carrier error,
# invalid number, Twilio service issue, etc. Nothing the user can do about it.
# These consume system retry budget (reminder.system_retry_count, max 2, with backoff).
_SYSTEM_FAILURE_STATUSES = {"failed", "canceled"}


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
    logger.info(
        "Twilio signature check | url=%r | sig_present=%s | token_tail=%s",
        url,
        bool(signature),
        settings.TWILIO_AUTH_TOKEN[-4:] if settings.TWILIO_AUTH_TOKEN else "MISSING",
    )
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

    if call_status not in _TERMINAL_CALL_STATUSES:
        logger.debug(f"Reminder {reminder_id}: ignoring intermediate CallStatus='{call_status}'")
        return Response(status_code=200)

    reminder = db.query(Reminder).filter(Reminder.id == reminder_id).first()

    # Only transition from "calling" — avoids overwriting if stuck-recovery
    # already marked this reminder as failed.
    if not reminder or reminder.status != "calling":
        return Response(status_code=200)

    new_eta_reminders = []  # collect new reminders that need ETA tasks after commit

    if call_status == "completed":
        # ── Call answered ─────────────────────────────────────────────────────
        reminder.status = "answered"
        if reminder.recurrence:
            next_r = _schedule_next_occurrence(db, reminder)
            if next_r:
                new_eta_reminders.append(next_r)
        db.commit()
        logger.info(f"Reminder {reminder_id}: answered.")

    elif call_status in _USER_FAILURE_STATUSES:
        # ── User-side failure: phone rang but wasn't answered ─────────────────
        # Consumes user retry budget (retry_count / attempt_number).
        reminder.status = call_status  # "no-answer" or "busy"
        has_retries = reminder.retry_count > 0
        is_final_attempt = (not has_retries) or (reminder.attempt_number > reminder.retry_count)

        if not is_final_attempt:
            new_r = _schedule_retry(db, reminder)
            if new_r:
                new_eta_reminders.append(new_r)
            logger.info(
                f"Reminder {reminder_id}: attempt {reminder.attempt_number} "
                f"{call_status} — user retry scheduled."
            )
        else:
            if reminder.recurrence:
                next_r = _schedule_next_occurrence(db, reminder)
                if next_r:
                    new_eta_reminders.append(next_r)
            _try_send_fallback_sms(db, reminder)
            logger.info(
                f"Reminder {reminder_id}: final attempt {call_status} — "
                f"SMS fallback attempted."
            )
        db.commit()

    elif call_status in _SYSTEM_FAILURE_STATUSES:
        # ── System-side failure: Twilio couldn't connect the call ─────────────
        # Carrier error, invalid number, Twilio service issue — nothing the user
        # can do. Apply system retry (backoff 30s→60s, max 2) independent of the
        # user's retry_count setting. _handle_system_failure commits internally.
        reason = f"Twilio CallStatus={call_status}"
        _handle_system_failure(db, reminder, reason)

        if reminder.status == "failed_system":
            # All system retries exhausted — treat as final failure:
            # schedule next recurrence (if any) and send SMS fallback.
            if reminder.recurrence:
                next_r = _schedule_next_occurrence(db, reminder)
                if next_r:
                    new_eta_reminders.append(next_r)
            _try_send_fallback_sms(db, reminder)
            db.commit()
            logger.error(
                f"Reminder {reminder_id}: system retries exhausted after "
                f"Twilio {call_status} — SMS fallback attempted."
            )
        else:
            logger.warning(
                f"Reminder {reminder_id}: system failure ({call_status}) — "
                f"system retry {reminder.system_retry_count}/{2} scheduled."
            )

    # Enqueue ETA tasks AFTER all commits so new reminder IDs are persisted.
    for r in new_eta_reminders:
        enqueue_reminder_eta(r)

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

    audio_url = xml_escape(generate_sas_url(reminder.audio_filename, expiry_hours=24))

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
