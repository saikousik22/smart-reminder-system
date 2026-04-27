"""
Groups router — manage contact groups and create multi-recipient reminders.
"""

import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import User, Group, GroupMember, Contact, Reminder, ReminderTemplate
from app.auth import get_current_user
from app.schemas import (
    GroupCreate, GroupUpdate, GroupMemberAdd,
    GroupResponse, ContactInGroup, GroupReminderCreateResponse, MessageResponse,
)
from app.routers.reminder_router import save_audio_file, parse_scheduled_time, VALID_RECURRENCES, _E164_RE
from app.services import blob_storage
from app.tasks import enqueue_reminder_eta

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/groups", tags=["Groups"])


def _build_group_response(group: Group) -> GroupResponse:
    members = [
        ContactInGroup(
            id=m.id,
            contact_id=m.contact_id,
            name=m.contact.name,
            phone_number=m.contact.phone_number,
        )
        for m in group.members
    ]
    return GroupResponse(
        id=group.id,
        user_id=group.user_id,
        name=group.name,
        created_at=group.created_at,
        members=members,
        member_count=len(members),
    )


def _load_group(db: Session, group_id: int, user_id: int) -> Group | None:
    """Fetch a single group with members+contacts eagerly loaded in one query."""
    return (
        db.query(Group)
        .options(joinedload(Group.members).joinedload(GroupMember.contact))
        .filter(Group.id == group_id, Group.user_id == user_id)
        .first()
    )


def _load_groups(db: Session, user_id: int) -> list[Group]:
    """Fetch all groups for a user with members+contacts eagerly loaded in one query."""
    return (
        db.query(Group)
        .options(joinedload(Group.members).joinedload(GroupMember.contact))
        .filter(Group.user_id == user_id)
        .order_by(Group.name)
        .all()
    )


# ── CRUD ──────────────────────────────────────────────────────────────────────

@router.get("", response_model=list[GroupResponse])
def list_groups(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    groups = _load_groups(db, current_user.id)
    return [_build_group_response(g) for g in groups]


@router.post("", response_model=GroupResponse, status_code=status.HTTP_201_CREATED)
def create_group(
    payload: GroupCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    duplicate = db.query(Group).filter(
        Group.user_id == current_user.id, Group.name == payload.name
    ).first()
    if duplicate:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"A group named '{payload.name}' already exists.")
    group = Group(user_id=current_user.id, name=payload.name)
    db.add(group)
    db.commit()
    group = _load_group(db, group.id, current_user.id)
    return _build_group_response(group)


@router.put("/{group_id}", response_model=GroupResponse)
def update_group(
    group_id: int,
    payload: GroupUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    group = db.query(Group).filter(Group.id == group_id, Group.user_id == current_user.id).first()
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    group.name = payload.name
    db.commit()
    group = _load_group(db, group_id, current_user.id)
    return _build_group_response(group)


@router.delete("/{group_id}", response_model=MessageResponse)
def delete_group(
    group_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    group = db.query(Group).filter(Group.id == group_id, Group.user_id == current_user.id).first()
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    name = group.name
    db.delete(group)
    db.commit()
    return {"message": f"Group '{name}' deleted successfully"}


# ── Member management ─────────────────────────────────────────────────────────

@router.post("/{group_id}/members", response_model=GroupResponse, status_code=status.HTTP_201_CREATED)
def add_member(
    group_id: int,
    payload: GroupMemberAdd,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    group = db.query(Group).filter(Group.id == group_id, Group.user_id == current_user.id).first()
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")

    contact = db.query(Contact).filter(
        Contact.id == payload.contact_id, Contact.user_id == current_user.id
    ).first()
    if not contact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")

    existing = db.query(GroupMember).filter(
        GroupMember.group_id == group_id, GroupMember.contact_id == payload.contact_id
    ).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"{contact.name} is already in this group.")

    db.add(GroupMember(group_id=group_id, contact_id=payload.contact_id))
    db.commit()
    group = _load_group(db, group_id, current_user.id)
    return _build_group_response(group)


@router.delete("/{group_id}/members/{contact_id}", response_model=GroupResponse)
def remove_member(
    group_id: int,
    contact_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    group = db.query(Group).filter(Group.id == group_id, Group.user_id == current_user.id).first()
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")

    member = db.query(GroupMember).filter(
        GroupMember.group_id == group_id, GroupMember.contact_id == contact_id
    ).first()
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found in group")

    db.delete(member)
    db.commit()
    group = _load_group(db, group_id, current_user.id)
    return _build_group_response(group)


# ── Group reminder creation ───────────────────────────────────────────────────

@router.post("/{group_id}/remind", response_model=GroupReminderCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_group_reminder(
    group_id: int,
    title: str = Form(...),
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
    """Create one reminder per group member, all firing at the same time."""
    group = _load_group(db, group_id, current_user.id)
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")

    if not group.members:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Group has no members. Add contacts before creating a reminder.",
        )

    parsed_time = parse_scheduled_time(scheduled_time)
    if parsed_time <= datetime.now(timezone.utc).replace(tzinfo=None):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Scheduled time must be in the future.")

    if recurrence and recurrence not in VALID_RECURRENCES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid recurrence. Must be one of: {', '.join(VALID_RECURRENCES)}")

    if not (0 <= retry_count <= 2):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="retry_count must be 0, 1, or 2")
    if not (5 <= retry_gap_minutes <= 60):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="retry_gap_minutes must be between 5 and 60")

    parsed_end_date = parse_scheduled_time(recurrence_end_date) if recurrence_end_date else None
    if parsed_end_date and parsed_end_date < parsed_time:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Recurrence end date must be on or after scheduled time.")

    # Resolve audio — upload once, then fan-out copies per member
    if audio_file is not None:
        base_audio = save_audio_file(audio_file, current_user.id)
    elif template_id is not None:
        template = db.query(ReminderTemplate).filter(
            ReminderTemplate.id == template_id, ReminderTemplate.user_id == current_user.id
        ).first()
        if not template:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
        ext = os.path.splitext(template.audio_filename)[1]
        base_audio = f"{current_user.id}/{uuid.uuid4()}{ext}"
        blob_storage.copy_audio(template.audio_filename, base_audio)
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Either audio_file or template_id is required.")

    # Fan out: each member gets their own blob copy so independent deletion is safe
    created_reminders = []
    for member in group.members:
        phone = member.contact.phone_number
        if not _E164_RE.match(phone):
            logger.warning(f"Skipping member {member.contact.name} — invalid phone: {phone}")
            continue

        ext = os.path.splitext(base_audio)[1]
        member_audio = f"{current_user.id}/{uuid.uuid4()}{ext}"
        blob_storage.copy_audio(base_audio, member_audio)

        reminder = Reminder(
            user_id=current_user.id,
            title=title,
            phone_number=phone,
            scheduled_time=parsed_time,
            audio_filename=member_audio,
            status="pending",
            recurrence=recurrence or None,
            recurrence_end_date=parsed_end_date,
            retry_count=retry_count,
            retry_gap_minutes=retry_gap_minutes,
            original_text=original_text or None,
            fallback_text=fallback_text or None,
            preferred_language=preferred_language or None,
            group_id=group_id,
        )
        db.add(reminder)
        created_reminders.append(reminder)

    # Delete the base blob used only as the copy source
    blob_storage.delete_audio(base_audio)

    db.flush()   # assign IDs to all new reminders before commit
    db.commit()

    # Enqueue ETA tasks after commit so all reminder IDs are persisted in DB
    for r in created_reminders:
        try:
            enqueue_reminder_eta(r)
        except Exception as exc:
            logger.warning(f"Reminder {r.id}: could not enqueue ETA task ({exc}). Recovery beat will handle it.")

    return GroupReminderCreateResponse(
        message=f"Reminder scheduled for {len(created_reminders)} contact(s) in '{group.name}'",
        count=len(created_reminders),
        group_id=group.id,
        group_name=group.name,
    )
