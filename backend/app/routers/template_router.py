"""
Template CRUD router — save/apply reusable reminder configurations.
"""

import logging
import os
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Reminder, ReminderTemplate
from app.auth import get_current_user
from app.schemas import TemplateResponse, TemplateSaveRequest, MessageResponse
from app.routers.reminder_router import save_audio_file
from app.services import blob_storage

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/templates", tags=["Templates"])


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
    audio_filename = save_audio_file(audio_file, current_user.id)
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
    """Save an existing reminder as a reusable template (copies its audio blob)."""
    reminder = (
        db.query(Reminder)
        .filter(Reminder.id == reminder_id, Reminder.user_id == current_user.id)
        .first()
    )
    if not reminder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reminder not found")

    ext = os.path.splitext(reminder.audio_filename)[1]
    new_blob_path = f"{current_user.id}/{uuid.uuid4()}{ext}"
    blob_storage.copy_audio(reminder.audio_filename, new_blob_path)

    template = ReminderTemplate(
        user_id=current_user.id,
        name=payload.name,
        title=reminder.title,
        phone_number=reminder.phone_number,
        audio_filename=new_blob_path,
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
    """Delete a template and its audio blob."""
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

    blob_storage.delete_audio(audio_filename)
    return {"message": f"Template '{name}' deleted successfully"}
