"""
Pure DB helper functions shared by tasks.py.
APScheduler has been removed — scheduling is now handled by Celery Beat.
"""

import calendar
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from app.models import Reminder

logger = logging.getLogger(__name__)


def compute_next_time(scheduled_time: datetime, recurrence: str) -> Optional[datetime]:
    """Return the next fire time for a recurring reminder, or None for unknown recurrence."""
    if recurrence == "daily":
        return scheduled_time + timedelta(days=1)
    if recurrence == "weekly":
        return scheduled_time + timedelta(weeks=1)
    if recurrence == "monthly":
        next_month = scheduled_time.month + 1
        next_year = scheduled_time.year
        if next_month > 12:
            next_month = 1
            next_year += 1
        day = min(scheduled_time.day, calendar.monthrange(next_year, next_month)[1])
        return scheduled_time.replace(year=next_year, month=next_month, day=day)
    if recurrence == "weekdays":
        next_time = scheduled_time + timedelta(days=1)
        while next_time.weekday() >= 5:  # skip Saturday (5) and Sunday (6)
            next_time += timedelta(days=1)
        return next_time
    return None


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
        retry_count=reminder.retry_count,
        retry_gap_minutes=reminder.retry_gap_minutes,
        original_text=reminder.original_text,
        fallback_text=reminder.fallback_text,
        fallback_sent=False,
        preferred_language=reminder.preferred_language,
    )
    db.add(next_reminder)
    logger.info(f"Reminder {reminder.id}: next occurrence at {next_time} (recurrence={reminder.recurrence})")


def _schedule_retry(db: Session, reminder: Reminder) -> None:
    """Create a retry pending reminder if retries are configured and attempts remain.

    Caller is responsible for calling db.commit() after this function returns.

    attempt_number is 1-indexed; retry_count is the number of retries (not total
    attempts). The condition below stops scheduling once attempt_number exceeds
    retry_count, which correctly allows retry_count + 1 total calls:
      retry_count=1 → attempts 1 and 2 (1 retry)
      retry_count=2 → attempts 1, 2, and 3 (2 retries)
    """
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
        original_text=reminder.original_text,
        fallback_text=reminder.fallback_text,
        fallback_sent=False,
        preferred_language=reminder.preferred_language,
    )
    db.add(retry)
    logger.info(
        f"Reminder {reminder.id}: retry scheduled in {reminder.retry_gap_minutes} min "
        f"(attempt {reminder.attempt_number + 1} of {reminder.retry_count + 1})"
    )
