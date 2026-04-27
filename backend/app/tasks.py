"""
Celery tasks.

trigger_call            — worker task; atomically claims and executes one reminder call.
recover_missed_reminders— beat task (every 120s); recovers reminders missed by ETA
                          (e.g. after a Redis restart) and stuck reminders.

Two-layer retry system
──────────────────────
Layer 1 — User retry (user-side failure):
  Triggered by: no-answer, busy (Twilio voice callback)
  Controlled by: reminder.retry_count (user's setting, 0–2)
  Scheduled by: _schedule_retry() in voice_router.py
  New reminder row created for each retry attempt

Layer 2 — System retry (infrastructure failure):
  Triggered by: TwilioRestException, network timeout, any exception in trigger_call
  Controlled by: MAX_SYSTEM_RETRIES = 2 (always, regardless of user settings)
  Backoff: 30s → 60s (exponential)
  Tracked by: reminder.system_retry_count on the SAME reminder row
  Status on exhaustion: 'failed_system'
"""

import logging
from datetime import datetime, timezone, timedelta

from app.celery_app import celery_app
from app.database import SessionLocal
from app.models import Reminder
from app.twilio_service import make_reminder_call


logger = logging.getLogger(__name__)

MAX_SYSTEM_RETRIES = 2


def enqueue_reminder_eta(reminder: Reminder) -> None:
    """Schedule trigger_call at reminder.scheduled_time (or immediately if past).

    Call this after every db.commit() that creates or reschedules a reminder.
    scheduled_time is stored as naive UTC — we make it timezone-aware for Celery.
    """
    eta = reminder.scheduled_time
    if eta.tzinfo is None:
        eta = eta.replace(tzinfo=timezone.utc)
    trigger_call.apply_async(args=[reminder.id], eta=eta)
    logger.info(f"Reminder {reminder.id}: ETA task scheduled for {eta}")


def _handle_system_failure(db, reminder: Reminder, reason: str) -> None:
    """
    Handle an infrastructure failure in trigger_call.

    System retries are always applied regardless of user's retry_count setting.
    Backoff: 30s after first failure, 60s after second.
    After MAX_SYSTEM_RETRIES exhausted: status → 'failed_system'.

    This is separate from user-side retries (no-answer, busy) which are
    handled by _schedule_retry() in voice_router.py.
    """
    reminder.system_retry_count += 1

    if reminder.system_retry_count <= MAX_SYSTEM_RETRIES:
        # Exponential backoff: 30s, 60s
        backoff_seconds = 30 * (2 ** (reminder.system_retry_count - 1))
        reminder.status = "pending"
        db.commit()

        retry_eta = datetime.now(timezone.utc) + timedelta(seconds=backoff_seconds)
        trigger_call.apply_async(args=[reminder.id], eta=retry_eta)
        logger.warning(
            f"Reminder {reminder.id}: system retry {reminder.system_retry_count}/{MAX_SYSTEM_RETRIES} "
            f"in {backoff_seconds}s. Reason: {reason}"
        )
    else:
        # All system retries exhausted — mark as infrastructure failure
        reminder.status = "failed_system"
        db.commit()
        logger.error(
            f"Reminder {reminder.id}: system retries exhausted ({MAX_SYSTEM_RETRIES}) "
            f"→ failed_system. Last reason: {reason}"
        )


@celery_app.task(name="app.tasks.recover_missed_reminders")
def recover_missed_reminders():
    """
    Beat task (every 120s) — safety net only, not the primary scheduler.

    1. Stuck recovery: reminders in 'calling'/'processing' > 10 min.
       These are system failures (Twilio webhook lost, worker crash mid-call).
       Applies system retry logic: resets to pending with backoff if budget remains,
       otherwise marks failed_system.

    2. Missed reminders: 'pending' reminders past their scheduled_time that have no
       live ETA task (e.g. after a Redis restart). Re-enqueues immediately.
    """
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        stuck_cutoff = now - timedelta(minutes=10)

        # ── Stuck recovery ───────────────────────────────────────────────────
        stuck = (
            db.query(Reminder)
            .filter(
                Reminder.status.in_(["calling", "processing"]),
                Reminder.updated_at <= stuck_cutoff,
            )
            .all()
        )

        new_retries = []
        for r in stuck:
            old_status = r.status
            logger.warning(f"Reminder {r.id} stuck in '{old_status}' for >10 min.")

            # Stuck = system failure. Apply system retry if budget remains.
            r.system_retry_count += 1
            if r.system_retry_count <= MAX_SYSTEM_RETRIES:
                backoff_seconds = 30 * (2 ** (r.system_retry_count - 1))
                r.status = "pending"
                logger.warning(
                    f"Reminder {r.id}: system retry {r.system_retry_count}/{MAX_SYSTEM_RETRIES} "
                    f"in {backoff_seconds}s (stuck recovery)."
                )
                # Store backoff as an offset from now — enqueue after commit
                new_retries.append((r, backoff_seconds))
            else:
                r.status = "failed_system"
                logger.error(
                    f"Reminder {r.id}: stuck, system retries exhausted → failed_system."
                )

        if stuck:
            db.commit()
            for r, backoff_seconds in new_retries:
                retry_eta = datetime.now(timezone.utc) + timedelta(seconds=backoff_seconds)
                trigger_call.apply_async(args=[r.id], eta=retry_eta)

        # ── Missed-reminder recovery ─────────────────────────────────────────
        # 30-second grace period: lets normally-scheduled ETA tasks fire before
        # recovery treats them as missed.
        recovery_cutoff = now - timedelta(seconds=30)
        missed = (
            db.query(Reminder)
            .filter(
                Reminder.status == "pending",
                Reminder.scheduled_time <= recovery_cutoff,
            )
            .limit(100)
            .all()
        )

        if not missed:
            return

        logger.info(f"recover_missed_reminders: {len(missed)} missed reminder(s) found.")

        # Batch-mark 'processing' in one commit to prevent a second beat run
        # from enqueueing the same reminders again before workers process them.
        for r in missed:
            r.status = "processing"
        db.commit()

        for r in missed:
            trigger_call.delay(r.id)

    except Exception as exc:
        logger.error(f"recover_missed_reminders error: {exc}", exc_info=True)
        db.rollback()
    finally:
        db.close()


@celery_app.task(name="app.tasks.trigger_call", max_retries=0)
def trigger_call(reminder_id: int):
    """
    Worker task: initiate the Twilio call for one reminder.

    Handles two entry paths:
      A) ETA path (normal): reminder arrives as 'pending'
      B) Recovery path:     reminder arrives as 'processing'

    On success:
      pending/processing → calling  (Twilio call SID stored)

    On infrastructure failure (TwilioRestException, network error, etc.):
      → _handle_system_failure(): system retry with backoff OR failed_system

    On user-side failure (no-answer, busy):
      → handled by Twilio status callback in voice_router.py (not here)
    """
    db = SessionLocal()
    reminder = None
    try:
        # Atomic claim: prevents duplicate execution from concurrent ETA + recovery.
        count = (
            db.query(Reminder)
            .filter(
                Reminder.id == reminder_id,
                Reminder.status.in_(["pending", "processing"]),
            )
            .update({"status": "processing"}, synchronize_session=False)
        )
        db.commit()

        if count == 0:
            logger.info(f"trigger_call: Reminder {reminder_id} already handled — skipping.")
            return

        reminder = db.query(Reminder).filter(Reminder.id == reminder_id).first()
        if not reminder:
            return

        # Stale-ETA guard: reminder was rescheduled to a future time after this
        # task was enqueued. Release back to pending so the new ETA fires correctly.
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        if reminder.scheduled_time > now + timedelta(seconds=60):
            reminder.status = "pending"
            db.commit()
            logger.info(
                f"trigger_call: Reminder {reminder_id} still in future — "
                f"stale ETA, releasing back to pending."
            )
            return

        # ── Place the call ───────────────────────────────────────────────────
        try:
            call_sid = make_reminder_call(reminder.phone_number, reminder.id)
        except Exception as exc:
            # Any exception here (Twilio API error, network timeout, invalid credentials,
            # rate limit, etc.) is a SYSTEM failure — apply system retry regardless of
            # user's retry_count setting.
            logger.error(f"trigger_call: system failure placing call for reminder {reminder_id}: {exc}")
            _handle_system_failure(db, reminder, str(exc))
            return

        # Call placed successfully — user-side outcome handled by Twilio status callback
        reminder.status = "calling"
        reminder.call_sid = call_sid
        db.commit()
        logger.info(f"trigger_call: Reminder {reminder_id} call initiated. SID={call_sid}")

    except Exception as exc:
        # Unexpected error outside the call placement block (DB issue, etc.)
        logger.error(f"trigger_call: unexpected error for reminder {reminder_id}: {exc}", exc_info=True)
        if reminder is not None:
            try:
                _handle_system_failure(db, reminder, f"unexpected: {exc}")
            except Exception as inner:
                logger.error(f"trigger_call: could not save failure for {reminder_id}: {inner}")
                db.rollback()
    finally:
        db.close()
