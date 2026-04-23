"""
Reminder CRUD router with audio file upload support.
"""

import logging
import os
import re
import shutil
import uuid
import subprocess
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import Response
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Reminder, ReminderTemplate
from app.auth import get_current_user
from app.schemas import ReminderResponse, MessageResponse, FeedbackSubmit

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/reminders", tags=["Reminders"])

# Audio upload directory (backend/uploads/)
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {".wav", ".mp3", ".ogg", ".webm"}
TWILIO_SUPPORTED_EXTENSIONS = {".wav", ".mp3"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB


def transcode_to_wav(source_path: str, target_path: str) -> None:
    """Transcode an audio file to WAV using ffmpeg."""
    command = [
        "ffmpeg",
        "-y",
        "-i",
        source_path,
        "-ac",
        "1",
        "-ar",
        "16000",
        target_path,
    ]
    try:
        subprocess.run(
            command,
            check=True,
            timeout=30,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except subprocess.TimeoutExpired as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Audio transcoding timed out.",
        ) from exc
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ffmpeg is not installed or not available on PATH. Install ffmpeg to enable audio playback in calls.",
        ) from exc
    except subprocess.CalledProcessError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to transcode audio for Twilio playback.",
        ) from exc
    except OSError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Audio transcoding failed due to a system error.",
        ) from exc


def parse_scheduled_time(scheduled_time: str) -> datetime:
    """Parse ISO 8601 input and normalize it to naive UTC datetime."""
    # Python < 3.11 doesn't support the 'Z' suffix in fromisoformat
    normalized = scheduled_time.replace("Z", "+00:00")
    try:
        parsed_time = datetime.fromisoformat(normalized)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid datetime format. Use ISO 8601 (e.g., 2025-12-31T14:30:00Z or 2025-12-31T14:30:00+05:30)",
        )

    if parsed_time.tzinfo is None:
        # No timezone info — treat as UTC (frontend should always send UTC)
        parsed_time = parsed_time.replace(tzinfo=timezone.utc)

    return parsed_time.astimezone(timezone.utc).replace(tzinfo=None)


def save_audio_file(file: UploadFile) -> str:
    """Save an uploaded audio file with a UUID filename. Returns the filename."""
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Audio file must have a valid filename with an extension.",
        )
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Audio format '{ext}' not supported. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # Generate temporary filename for the uploaded audio
    temp_name = f"{uuid.uuid4()}{ext}"
    temp_path = os.path.join(UPLOAD_DIR, temp_name)

    # Write in 64 KB chunks and abort early if the size limit is exceeded,
    # avoiding writing a full oversized file to disk before rejecting it
    total_bytes = 0
    chunk_size = 64 * 1024
    try:
        with open(temp_path, "wb") as buffer:
            while True:
                chunk = file.file.read(chunk_size)
                if not chunk:
                    break
                total_bytes += len(chunk)
                if total_bytes > MAX_FILE_SIZE:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Audio file exceeds 5 MB limit",
                    )
                buffer.write(chunk)
    except HTTPException:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise
    except Exception as exc:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save audio file.",
        ) from exc

    if ext in TWILIO_SUPPORTED_EXTENSIONS:
        return temp_name

    # Transcode unsupported formats to WAV for Twilio playback
    converted_name = f"{uuid.uuid4()}.wav"
    converted_path = os.path.join(UPLOAD_DIR, converted_name)
    try:
        transcode_to_wav(temp_path, converted_path)
    finally:
        try:
            os.remove(temp_path)
        except OSError as e:
            logger.warning(f"Could not delete temporary audio file {temp_path}: {e}")
    return converted_name


def delete_audio_file(filename: str):
    """Delete an audio file from the uploads directory."""
    file_path = os.path.join(UPLOAD_DIR, filename)
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except OSError as e:
            logger.warning(f"Could not delete audio file {filename}: {e}")


VALID_RECURRENCES = {"daily", "weekly", "monthly", "weekdays"}
VALID_STATUSES = {"pending", "processing", "calling", "answered", "no-answer", "busy", "failed"}
_TERMINAL_STATUSES = {"answered", "no-answer", "busy", "failed"}
_E164_RE = re.compile(r"^\+[1-9]\d{0,14}$")


@router.post("", response_model=ReminderResponse, status_code=status.HTTP_201_CREATED)
async def create_reminder(
    title: str = Form(...),
    phone_number: str = Form(...),
    scheduled_time: str = Form(...),
    audio_file: Optional[UploadFile] = File(None),
    template_id: Optional[int] = Form(None),
    recurrence: Optional[str] = Form(None),
    recurrence_end_date: Optional[str] = Form(None),
    retry_count: int = Form(0),
    retry_gap_minutes: int = Form(10),
    original_text: Optional[str] = Form(None),
    fallback_text: Optional[str] = Form(None),
    preferred_language: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new reminder. Requires either audio_file or template_id for the voice message."""
    parsed_time = parse_scheduled_time(scheduled_time)

    if parsed_time <= datetime.now(timezone.utc).replace(tzinfo=None):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Scheduled time must be in the future.",
        )

    if recurrence and recurrence not in VALID_RECURRENCES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid recurrence. Must be one of: {', '.join(VALID_RECURRENCES)}",
        )

    if not (0 <= retry_count <= 2):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="retry_count must be 0, 1, or 2")
    if not (5 <= retry_gap_minutes <= 60):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="retry_gap_minutes must be between 5 and 60")

    parsed_end_date = parse_scheduled_time(recurrence_end_date) if recurrence_end_date else None

    if parsed_end_date and parsed_end_date < parsed_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Recurrence end date must be on or after scheduled time.",
        )

    if audio_file is not None:
        audio_filename = save_audio_file(audio_file)
    elif template_id is not None:
        template = (
            db.query(ReminderTemplate)
            .filter(ReminderTemplate.id == template_id, ReminderTemplate.user_id == current_user.id)
            .first()
        )
        if not template:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
        ext = os.path.splitext(template.audio_filename)[1]
        new_filename = f"{uuid.uuid4()}{ext}"
        src = os.path.join(UPLOAD_DIR, template.audio_filename)
        dst = os.path.join(UPLOAD_DIR, new_filename)
        if not os.path.exists(src):
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Template audio file not found on server.")
        shutil.copy2(src, dst)
        audio_filename = new_filename
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either audio_file or template_id is required.",
        )

    reminder = Reminder(
        user_id=current_user.id,
        title=title,
        phone_number=phone_number,
        scheduled_time=parsed_time,
        audio_filename=audio_filename,
        status="pending",
        recurrence=recurrence or None,
        recurrence_end_date=parsed_end_date,
        retry_count=retry_count,
        retry_gap_minutes=retry_gap_minutes,
        original_text=original_text or None,
        fallback_text=fallback_text or None,
        preferred_language=preferred_language or None,
    )
    db.add(reminder)
    db.commit()
    db.refresh(reminder)

    return reminder


@router.get("", response_model=list[ReminderResponse])
def get_reminders(
    status_filter: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all reminders for the current user, optionally filtered by status."""
    if status_filter and status_filter not in VALID_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status filter. Must be one of: {', '.join(sorted(VALID_STATUSES))}",
        )
    query = db.query(Reminder).filter(Reminder.user_id == current_user.id)
    if status_filter:
        query = query.filter(Reminder.status == status_filter)
    reminders = query.order_by(Reminder.scheduled_time.desc()).all()
    return reminders


@router.get("/{reminder_id}", response_model=ReminderResponse)
def get_reminder(
    reminder_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a single reminder by ID."""
    reminder = (
        db.query(Reminder)
        .filter(Reminder.id == reminder_id, Reminder.user_id == current_user.id)
        .first()
    )
    if not reminder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reminder not found")
    return reminder


@router.put("/{reminder_id}", response_model=ReminderResponse)
async def update_reminder(
    reminder_id: int,
    title: Optional[str] = Form(None),
    phone_number: Optional[str] = Form(None),
    scheduled_time: Optional[str] = Form(None),
    audio_file: Optional[UploadFile] = File(None),
    recurrence: Optional[str] = Form(None),
    recurrence_end_date: Optional[str] = Form(None),
    retry_count: Optional[int] = Form(None),
    retry_gap_minutes: Optional[int] = Form(None),
    original_text: Optional[str] = Form(None),
    fallback_text: Optional[str] = Form(None),
    preferred_language: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update an existing reminder. Only provided fields are updated."""
    reminder = (
        db.query(Reminder)
        .filter(Reminder.id == reminder_id, Reminder.user_id == current_user.id)
        .first()
    )
    if not reminder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reminder not found")

    if title is not None:
        reminder.title = title
    if phone_number is not None:
        if not _E164_RE.match(phone_number):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number must be in E.164 format (e.g., +919876543210)",
            )
        reminder.phone_number = phone_number
    if scheduled_time is not None:
        parsed = parse_scheduled_time(scheduled_time)
        if parsed <= datetime.now(timezone.utc).replace(tzinfo=None):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Scheduled time must be in the future.",
            )
        reminder.scheduled_time = parsed

    old_audio_filename = None
    if audio_file is not None:
        old_audio_filename = reminder.audio_filename
        reminder.audio_filename = save_audio_file(audio_file)

    if recurrence is not None:
        # Empty string or "none" explicitly clears recurrence
        if recurrence and recurrence not in VALID_RECURRENCES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid recurrence. Must be one of: {', '.join(VALID_RECURRENCES)}",
            )
        reminder.recurrence = recurrence if recurrence in VALID_RECURRENCES else None
    if recurrence_end_date is not None:
        parsed_end = parse_scheduled_time(recurrence_end_date) if recurrence_end_date else None
        if parsed_end and parsed_end < reminder.scheduled_time:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Recurrence end date must be on or after scheduled time.",
            )
        reminder.recurrence_end_date = parsed_end

    if retry_count is not None:
        if not (0 <= retry_count <= 2):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="retry_count must be 0, 1, or 2")
        reminder.retry_count = retry_count
    if retry_gap_minutes is not None:
        if not (5 <= retry_gap_minutes <= 60):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="retry_gap_minutes must be between 5 and 60")
        reminder.retry_gap_minutes = retry_gap_minutes

    if original_text is not None:
        reminder.original_text = original_text or None
    if fallback_text is not None:
        reminder.fallback_text = fallback_text or None
    if preferred_language is not None:
        reminder.preferred_language = preferred_language or None

    delivery_field_changed = (
        scheduled_time is not None or audio_file is not None or phone_number is not None
    )
    if delivery_field_changed and reminder.status not in _TERMINAL_STATUSES:
        reminder.status = "pending"

    db.commit()
    db.refresh(reminder)

    # Delete old file only after a successful commit so we never lose it on rollback
    if old_audio_filename:
        delete_audio_file(old_audio_filename)

    return reminder


@router.put("/{reminder_id}/feedback", response_model=ReminderResponse)
def submit_feedback(
    reminder_id: int,
    feedback: FeedbackSubmit,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Submit or update a rating (1–5) and optional comment for a completed reminder."""
    reminder = (
        db.query(Reminder)
        .filter(Reminder.id == reminder_id, Reminder.user_id == current_user.id)
        .first()
    )
    if not reminder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reminder not found")

    if reminder.status not in _TERMINAL_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Feedback can only be submitted for reminders with status: answered, no-answer, busy, or failed.",
        )

    reminder.feedback_rating = feedback.rating
    reminder.feedback_comment = feedback.comment
    db.commit()
    db.refresh(reminder)
    return reminder


@router.delete("/{reminder_id}", response_model=MessageResponse)
def delete_reminder(
    reminder_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a reminder and its associated audio file."""
    reminder = (
        db.query(Reminder)
        .filter(Reminder.id == reminder_id, Reminder.user_id == current_user.id)
        .first()
    )
    if not reminder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reminder not found")

    audio_filename = reminder.audio_filename
    title = reminder.title

    db.delete(reminder)
    db.commit()

    # Delete the audio file only after the DB record is gone
    delete_audio_file(audio_filename)

    return {"message": f"Reminder '{title}' deleted successfully"}


@router.get("/{reminder_id}/export-ics")
def export_reminder_ics(
    reminder_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Export a reminder as a downloadable .ics calendar file."""
    reminder = (
        db.query(Reminder)
        .filter(Reminder.id == reminder_id, Reminder.user_id == current_user.id)
        .first()
    )
    if not reminder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reminder not found")

    # scheduled_time is stored as naive UTC
    dt_start = reminder.scheduled_time.replace(tzinfo=timezone.utc)
    dt_end = dt_start + timedelta(minutes=5)
    dt_stamp = datetime.now(timezone.utc)

    def fmt(dt: datetime) -> str:
        return dt.strftime("%Y%m%dT%H%M%SZ")

    def ics_escape(s: str) -> str:
        return s.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")

    ics_content = (
        "BEGIN:VCALENDAR\r\n"
        "VERSION:2.0\r\n"
        "PRODID:-//SmartReminder//SmartReminder//EN\r\n"
        "CALSCALE:GREGORIAN\r\n"
        "METHOD:PUBLISH\r\n"
        "BEGIN:VEVENT\r\n"
        f"UID:{reminder.id}-{reminder.user_id}@smart-reminder\r\n"
        f"DTSTAMP:{fmt(dt_stamp)}\r\n"
        f"DTSTART:{fmt(dt_start)}\r\n"
        f"DTEND:{fmt(dt_end)}\r\n"
        f"SUMMARY:{ics_escape(reminder.title)}\r\n"
        f"DESCRIPTION:Phone: {ics_escape(reminder.phone_number)}\r\n"
        "END:VEVENT\r\n"
        "END:VCALENDAR\r\n"
    )

    safe_title = re.sub(r"[^\w\-]", "_", reminder.title)[:50]
    return Response(
        content=ics_content,
        media_type="text/calendar",
        headers={"Content-Disposition": f'attachment; filename="{safe_title}.ics"'},
    )
