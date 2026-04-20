"""
Pydantic schemas for request/response validation.
"""

from pydantic import BaseModel, EmailStr, Field, field_validator
from datetime import datetime
from typing import Optional, Literal


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


class ReminderUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    phone_number: Optional[str] = Field(None, min_length=10, max_length=20)
    scheduled_time: Optional[datetime] = None
    recurrence: Optional[Literal["daily", "weekly", "monthly", "weekdays"]] = None
    recurrence_end_date: Optional[datetime] = None
    retry_count: Optional[int] = Field(None, ge=0, le=2)
    retry_gap_minutes: Optional[int] = Field(None, ge=5, le=60)


class ReminderResponse(BaseModel):
    id: int
    user_id: int
    title: str
    phone_number: str
    scheduled_time: datetime
    audio_filename: str
    status: str
    recurrence: Optional[str] = None
    recurrence_end_date: Optional[datetime] = None
    call_sid: Optional[str] = None
    retry_count: int = 0
    retry_gap_minutes: int = 10
    attempt_number: int = 1
    parent_reminder_id: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    message: str
