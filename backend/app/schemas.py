"""
Pydantic schemas for request/response validation.
"""

import re
from pydantic import BaseModel, EmailStr, Field, field_validator
from datetime import datetime
from typing import Optional, Literal

_E164_RE = re.compile(r"^\+[1-9]\d{0,14}$")


# ──────────────────────────────── Auth Schemas ────────────────────────────────

class UserSignup(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    created_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ──────────────────────────────── Reminder Schemas ────────────────────────────

class ReminderCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    phone_number: str = Field(..., min_length=10, max_length=20)
    scheduled_time: datetime
    recurrence: Optional[Literal["daily", "weekly", "monthly", "weekdays"]] = None
    recurrence_end_date: Optional[datetime] = None
    retry_count: int = Field(0, ge=0, le=2)
    retry_gap_minutes: int = Field(10, ge=5, le=60)
    original_text: Optional[str] = Field(None, max_length=1000)
    fallback_text: Optional[str] = Field(None, max_length=1000)
    preferred_language: Optional[str] = Field(None, max_length=10)

    @field_validator("phone_number")
    @classmethod
    def validate_phone_e164(cls, v: str) -> str:
        if not _E164_RE.match(v):
            raise ValueError("Phone number must be in E.164 format (e.g., +919876543210)")
        return v


class ReminderUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    phone_number: Optional[str] = Field(None, min_length=10, max_length=20)
    scheduled_time: Optional[datetime] = None
    recurrence: Optional[Literal["daily", "weekly", "monthly", "weekdays"]] = None
    recurrence_end_date: Optional[datetime] = None
    retry_count: Optional[int] = Field(None, ge=0, le=2)
    retry_gap_minutes: Optional[int] = Field(None, ge=5, le=60)
    original_text: Optional[str] = Field(None, max_length=1000)
    fallback_text: Optional[str] = Field(None, max_length=1000)
    preferred_language: Optional[str] = Field(None, max_length=10)

    @field_validator("phone_number")
    @classmethod
    def validate_phone_e164(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not _E164_RE.match(v):
            raise ValueError("Phone number must be in E.164 format (e.g., +919876543210)")
        return v


class ReminderResponse(BaseModel):
    id: int
    user_id: int
    title: str
    phone_number: str
    scheduled_time: datetime
    audio_filename: str
    status: Literal["pending", "processing", "calling", "answered", "no-answer", "busy", "failed", "failed_system"]
    recurrence: Optional[str] = None
    recurrence_end_date: Optional[datetime] = None
    call_sid: Optional[str] = None
    retry_count: int = 0
    retry_gap_minutes: int = 10
    attempt_number: int = 1
    parent_reminder_id: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    feedback_rating: Optional[int] = None
    feedback_comment: Optional[str] = None
    original_text: Optional[str] = None
    fallback_text: Optional[str] = None
    fallback_sent: bool = False
    preferred_language: Optional[str] = None
    fallback_type: Optional[str] = None
    fallback_email: Optional[str] = None
    group_id: Optional[int] = None
    group_name: Optional[str] = None

    class Config:
        from_attributes = True


class FeedbackSubmit(BaseModel):
    rating: int = Field(..., ge=1, le=5, description="1 = worst, 5 = best")
    comment: Optional[str] = Field(None, max_length=500)


class BulkDeleteRequest(BaseModel):
    ids: list[int] = Field(..., min_length=1, max_length=100, description="List of reminder IDs to delete")


class MessageResponse(BaseModel):
    message: str


# ──────────────────────────────── Template Schemas ────────────────────────────

class TemplateSaveRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)


class TemplateResponse(BaseModel):
    id: int
    user_id: int
    name: str
    title: str
    phone_number: str
    audio_filename: str
    recurrence: Optional[str] = None
    retry_count: int = 0
    retry_gap_minutes: int = 10
    created_at: datetime

    class Config:
        from_attributes = True


# ──────────────────────────────── Group Schemas ──────────────────────────────

class GroupCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)


class GroupUpdate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)


class GroupMemberAdd(BaseModel):
    contact_id: int


class ContactInGroup(BaseModel):
    id: int
    contact_id: int
    name: str
    phone_number: str

    class Config:
        from_attributes = True


class GroupResponse(BaseModel):
    id: int
    user_id: int
    name: str
    created_at: datetime
    members: list[ContactInGroup] = []
    member_count: int = 0

    class Config:
        from_attributes = True


class GroupReminderCreateResponse(BaseModel):
    message: str
    count: int
    group_id: int
    group_name: str


# ──────────────────────────────── Contact Schemas ────────────────────────────

class ContactCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    phone_number: str = Field(..., min_length=7, max_length=20)

    @field_validator("phone_number")
    @classmethod
    def validate_phone_e164(cls, v: str) -> str:
        if not _E164_RE.match(v):
            raise ValueError("Phone number must be in E.164 format (e.g., +919876543210)")
        return v


class ContactUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    phone_number: Optional[str] = Field(None, min_length=7, max_length=20)

    @field_validator("phone_number")
    @classmethod
    def validate_phone_e164(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not _E164_RE.match(v):
            raise ValueError("Phone number must be in E.164 format (e.g., +919876543210)")
        return v


class ContactResponse(BaseModel):
    id: int
    user_id: int
    name: str
    phone_number: str
    created_at: datetime

    class Config:
        from_attributes = True


# ──────────────────────────────── Translate Schemas ───────────────────────────

class TranslateRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=1000, description="English source text")
    target_lang: str = Field(..., min_length=2, max_length=10, description="ISO 639-1 language code (e.g. 'hi', 'te')")


class TranslateResponse(BaseModel):
    original_text: str
    translated_text: str
    target_lang: str
    language_name: str
