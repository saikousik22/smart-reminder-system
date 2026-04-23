"""
Celery tasks.

beat_check_reminders  — runs every 60 s; marks due reminders 'processing'
                        and enqueues trigger_call for each one.
trigger_call          — worker task; makes the Twilio call and marks 'calling'.
"""

import logging
from datetime import datetime, timezone, timedelta

from app.celery_app import celery_app
from app.database import SessionLocal
from app.models import Reminder
from app.twilio_service import make_reminder_call
from app.scheduler import _schedule_next_occurrence, _schedule_retry

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.beat_check_reminders")
def beat_check_reminders():
    """
    Periodic beat task (every 60 s):
    1. Recover stuck 'calling'/'processing' reminders (updated_at > 10 min ago) → 'failed'.
    2. Atomically mark due 'pending' reminders as 'processing', then enqueue trigger_call.
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
        for r in stuck:
            old_status = r.status
            r.status = "failed"
            _schedule_retry(db, r)
            logger.warning(f"Reminder {r.id} stuck in '{old_status}' for >10 min → marked failed.")
        if stuck:
            db.commit()

        # ── Pick up due reminders ────────────────────────────────────────────
        due = (
            db.query(Reminder)
            .filter(
                Reminder.status == "pending",
                Reminder.scheduled_time <= now,
            )
            .all()
        )

        if not due:
            return

        logger.info(f"beat_check_reminders: {len(due)} due reminder(s) found.")

        # Mark all as 'processing' in one commit to prevent duplicate enqueue
        # if a second beat fires before workers finish.
        for r in due:
            r.status = "processing"
        db.commit()

        enqueue_failed = []
        for r in due:
            try:
                trigger_call.delay(r.id)
            except Exception as exc:
                logger.error(f"Failed to enqueue trigger_call for reminder {r.id}: {exc}")
                r.status = "failed"
                enqueue_failed.append(r.id)

        if enqueue_failed:
            db.commit()
            logger.warning(f"beat_check_reminders: {len(enqueue_failed)} reminder(s) failed to enqueue: {enqueue_failed}")

    except Exception as exc:
        logger.error(f"beat_check_reminders error: {exc}", exc_info=True)
        db.rollback()
        # Do not re-raise: beat tasks must not propagate exceptions or the
        # scheduler may drop the task and stop firing entirely.
    finally:
        db.close()


@celery_app.task(name="app.tasks.trigger_call", max_retries=0)
def trigger_call(reminder_id: int):
    """
    Worker task: initiate the Twilio call for one reminder.

    State transitions:
      processing → calling   (Twilio call initiated successfully)
      processing → failed    (exception; retry reminder created if configured)

    Terminal statuses (answered / no-answer / busy / failed) are set later
    by the Twilio status-callback webhook in voice_router.py.
    """
    db = SessionLocal()
    reminder = None
    try:
        reminder = (
            db.query(Reminder)
            .filter(Reminder.id == reminder_id, Reminder.status == "processing")
            .first()
        )
        if not reminder:
            # Already handled (e.g. duplicate task, manual cancel)
            logger.info(f"trigger_call: Reminder {reminder_id} not in 'processing' — skipping.")
            return

        call_sid = make_reminder_call(reminder.phone_number, reminder.id)
        reminder.status = "calling"
        reminder.call_sid = call_sid

        if reminder.recurrence:
            _schedule_next_occurrence(db, reminder)

        db.commit()
        logger.info(f"trigger_call: Reminder {reminder_id} call initiated. SID={call_sid}")

    except Exception as exc:
        logger.error(f"trigger_call: Reminder {reminder_id} failed: {exc}", exc_info=True)
        if reminder is not None:
            try:
                reminder.status = "failed"
                _schedule_retry(db, reminder)
                db.commit()
            except Exception as inner:
                logger.error(f"trigger_call: Could not save failure status for {reminder_id}: {inner}")
                db.rollback()
    finally:
        db.close()
