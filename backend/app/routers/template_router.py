"""
Template CRUD router — save/apply reusable reminder configurations.
"""

import logging
import os
import shutil
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Reminder, ReminderTemplate
from app.auth import get_current_user
from app.schemas import TemplateResponse, TemplateSaveRequest, MessageResponse
from app.routers.reminder_router import save_audio_file, UPLOAD_DIR

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/templates", tags=["Templates"])


def _copy_audio(source_filename: str) -> str:
    """Copy an audio file to a new UUID filename and return the new filename."""
    ext = os.path.splitext(source_filename)[1]
    new_filename = f"{uuid.uuid4()}{ext}"
    src = os.path.join(UPLOAD_DIR, source_filename)
    dst = os.path.join(UPLOAD_DIR, new_filename)
    if not os.path.exists(src):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audio file not found on server.",
        )
    shutil.copy2(src, dst)
    return new_filename


@router.get("", response_model=list[TemplateResponse])
def list_templates(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all templates for the current user."""
    return (
        db.query(ReminderTemplate)
        .filter(ReminderTemplate.user_id == current_user.id)
        .order_by(ReminderTemplate.created_at.desc())
        .all()
    )


@router.post("", response_model=TemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_template(
    name: str = Form(...),
    title: str = Form(...),
    phone_number: str = Form(...),
    audio_file: UploadFile = File(...),
    recurrence: Optional[str] = Form(None),
    retry_count: int = Form(0),
    retry_gap_minutes: int = Form(10),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new template by uploading an audio file alongside reminder settings."""
    audio_filename = save_audio_file(audio_file)
    template = ReminderTemplate(
        user_id=current_user.id,
        name=name,
        title=title,
        phone_number=phone_number,
        audio_filename=audio_filename,
        recurrence=recurrence or None,
        retry_count=retry_count,
        retry_gap_minutes=retry_gap_minutes,
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


@router.post(
    "/from-reminder/{reminder_id}",
    response_model=TemplateResponse,
    status_code=status.HTTP_201_CREATED,
)
def save_reminder_as_template(
    reminder_id: int,
    payload: TemplateSaveRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Save an existing reminder as a reusable template (copies its audio file)."""
    reminder = (
        db.query(Reminder)
        .filter(Reminder.id == reminder_id, Reminder.user_id == current_user.id)
        .first()
    )
    if not reminder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reminder not found")

    audio_filename = _copy_audio(reminder.audio_filename)
    template = ReminderTemplate(
        user_id=current_user.id,
        name=payload.name,
        title=reminder.title,
        phone_number=reminder.phone_number,
        audio_filename=audio_filename,
        recurrence=reminder.recurrence,
        retry_count=reminder.retry_count,
        retry_gap_minutes=reminder.retry_gap_minutes,
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


@router.delete("/{template_id}", response_model=MessageResponse)
def delete_template(
    template_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a template and its audio file."""
    template = (
        db.query(ReminderTemplate)
        .filter(ReminderTemplate.id == template_id, ReminderTemplate.user_id == current_user.id)
        .first()
    )
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")

    audio_filename = template.audio_filename
    name = template.name
    db.delete(template)
    db.commit()

    file_path = os.path.join(UPLOAD_DIR, audio_filename)
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except OSError as e:
            logger.warning(f"Could not delete template audio {file_path}: {e}")

    return {"message": f"Template '{name}' deleted successfully"}
