"""
SQLAlchemy ORM models for Users and Reminders.
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Index
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationship
    reminders = relationship("Reminder", back_populates="owner", cascade="all, delete-orphan")


class Reminder(Base):
    __tablename__ = "reminders"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(200), nullable=False)
    phone_number = Column(String(20), nullable=False)
    scheduled_time = Column(DateTime, nullable=False)
    audio_filename = Column(Text, nullable=False)
    status = Column(String(20), default="pending", nullable=False)
    # Recurrence: daily, weekly, monthly, weekdays — null means one-time
    recurrence = Column(String(20), nullable=True)
    recurrence_end_date = Column(DateTime, nullable=True)
    # Twilio Call SID stored for reference/debugging
    call_sid = Column(String(50), nullable=True)
    # Retry configuration: retry_count=0 means no retries; max is 2 (3 calls total)
    retry_count = Column(Integer, default=0, nullable=False)
    retry_gap_minutes = Column(Integer, default=10, nullable=False)
    # attempt_number=1 for original call, 2 for first retry, etc.
    attempt_number = Column(Integer, default=1, nullable=False)
    parent_reminder_id = Column(Integer, ForeignKey("reminders.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationship
    owner = relationship("User", back_populates="reminders")

    __table_args__ = (
        Index("ix_reminders_user_id", "user_id"),
        Index("ix_reminders_status_scheduled", "status", "scheduled_time"),
    )
