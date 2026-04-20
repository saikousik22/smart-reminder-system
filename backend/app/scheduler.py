"""
APScheduler background job that checks for due reminders every 60 seconds
and triggers Twilio calls.
"""

import calendar
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Reminder
from app.twilio_service import make_reminder_call

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


def compute_next_time(scheduled_time: datetime, recurrence: str) -> Optional[datetime]:
    """Return the next fire time for a recurring reminder, or None for unknown recurrence."""
    if recurrence == "daily":
        return scheduled_time + timedelta(days=1)
    if recurrence == "weekly":
        return scheduled_time + timedelta(weeks=1)
    if recurrence == "monthly":
        month = scheduled_time.month + 1
        year = scheduled_time.year + (month - 1) // 12
        month = ((month - 1) % 12) + 1
        day = min(scheduled_time.day, calendar.monthrange(year, month)[1])
        return scheduled_time.replace(year=year, month=month, day=day)
    if recurrence == "weekdays":
        next_time = scheduled_time + timedelta(days=1)
        while next_time.weekday() >= 5:  # skip Saturday (5) and Sunday (6)
            next_time += timedelta(days=1)
        return next_time
    return None


def _schedule_retry(db: Session, reminder: Reminder) -> None:
    """Create a retry pending reminder if retries are configured and attempts remain."""
    if reminder.retry_count == 0:
        return
    if reminder.attempt_number > reminder.retry_count:
        return

    retry_time = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=reminder.retry_gap_minutes)
    retry = Reminder(
        user_id=reminder.user_id,
        title=reminder.title,
        phone_number=reminder.phone_number,
        scheduled_time=retry_time,
        audio_filename=reminder.audio_filename,
        status="pending",
        recurrence=reminder.recurrence,
        recurrence_end_date=reminder.recurrence_end_date,
        retry_count=reminder.retry_count,
        retry_gap_minutes=reminder.retry_gap_minutes,
        attempt_number=reminder.attempt_number + 1,
        parent_reminder_id=reminder.parent_reminder_id or reminder.id,
    )
    db.add(retry)
    logger.info(
        f"Reminder {reminder.id}: retry scheduled in {reminder.retry_gap_minutes} min "
        f"(attempt {reminder.attempt_number + 1} of {reminder.retry_count + 1})"
    )


def _schedule_next_occurrence(db: Session, reminder: Reminder) -> None:
    """Create the next pending occurrence for a recurring reminder."""
    next_time = compute_next_time(reminder.scheduled_time, reminder.recurrence)
    if next_time is None:
        return
    if reminder.recurrence_end_date and next_time > reminder.recurrence_end_date:
        logger.info(f"Reminder {reminder.id}: recurrence end date reached, no next occurrence.")
        return

    next_reminder = Reminder(
        user_id=reminder.user_id,
        title=reminder.title,
        phone_number=reminder.phone_number,
        scheduled_time=next_time,
        audio_filename=reminder.audio_filename,
        status="pending",
        recurrence=reminder.recurrence,
        recurrence_end_date=reminder.recurrence_end_date,
    )
    db.add(next_reminder)
    logger.info(f"Reminder {reminder.id}: next occurrence scheduled at {next_time} (recurrence={reminder.recurrence})")


def check_and_trigger_reminders():
    """
    Query all pending reminders whose scheduled_time has passed,
    then initiate a Twilio call for each one.
    """
    db: Session = SessionLocal()
    try:
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        # Recover reminders stuck in "calling" for more than 10 minutes —
        # these are left over from a crash or a missed status callback
        stuck_cutoff = now - timedelta(minutes=10)
        stuck_reminders = (
            db.query(Reminder)
            .filter(
                Reminder.status == "calling",
                Reminder.scheduled_time <= stuck_cutoff,
            )
            .all()
        )
        for reminder in stuck_reminders:
            reminder.status = "failed"
            _schedule_retry(db, reminder)
            logger.warning(f"Reminder {reminder.id} recovered from stuck 'calling' state → marked failed.")
        if stuck_reminders:
            db.commit()

        pending_reminders = (
            db.query(Reminder)
            .filter(
                Reminder.status == "pending",
                Reminder.scheduled_time <= now,
            )
            .all()
        )

        if pending_reminders:
            logger.info(f"Found {len(pending_reminders)} due reminder(s) to process.")

        for reminder in pending_reminders:
            try:
                call_sid = make_reminder_call(reminder.phone_number, reminder.id)
                reminder.status = "calling"
                reminder.call_sid = call_sid
                logger.info(f"Reminder {reminder.id} call initiated. SID: {call_sid}")

                # Queue the next occurrence before committing so both writes are atomic
                if reminder.recurrence:
                    _schedule_next_occurrence(db, reminder)

            except Exception as e:
                reminder.status = "failed"
                logger.error(f"Reminder {reminder.id} call failed: {e}")
            finally:
                db.commit()

    except Exception as e:
        logger.error(f"Scheduler job error: {e}")
    finally:
        db.close()


def start_scheduler():
    """Start the background scheduler with the reminder check job."""
    scheduler.add_job(
        check_and_trigger_reminders,
        "interval",
        seconds=60,
        id="reminder_checker",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("APScheduler started — checking reminders every 60 seconds.")


def stop_scheduler():
    """Gracefully shut down the scheduler."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("APScheduler stopped.")
