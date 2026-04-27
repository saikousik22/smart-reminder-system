"""
SQLAlchemy ORM models for Users and Reminders.
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Index, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.database import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": "SHR_V1"}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    # Relationships
    reminders = relationship("Reminder", back_populates="owner", cascade="all, delete-orphan")
    templates = relationship("ReminderTemplate", back_populates="owner", cascade="all, delete-orphan")
    contacts = relationship("Contact", back_populates="owner", cascade="all, delete-orphan")
    groups = relationship("Group", back_populates="owner", cascade="all, delete-orphan")


class Reminder(Base):
    __tablename__ = "reminders"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("SHR_V1.users.id"), nullable=False)
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
    parent_reminder_id = Column(Integer, ForeignKey("SHR_V1.reminders.id"), nullable=True)
    # System-retry counter: incremented each time trigger_call fails due to infrastructure
    # (Twilio API error, network timeout, etc.) — independent of user-configured retry_count.
    # Max 2 system retries (30s → 60s backoff). Status becomes 'failed_system' when exhausted.
    system_retry_count = Column(Integer, default=0, nullable=False, server_default="0")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    # Post-call feedback — null until the user submits a rating
    feedback_rating = Column(Integer, nullable=True)
    feedback_comment = Column(Text, nullable=True)
    # SMS fallback fields
    original_text = Column(Text, nullable=True)
    fallback_text = Column(Text, nullable=True)
    fallback_sent = Column(Boolean, default=False, nullable=False, server_default="false")
    preferred_language = Column(String(10), nullable=True)
    group_id = Column(Integer, ForeignKey("SHR_V1.groups.id"), nullable=True)

    # Relationships
    owner = relationship("User", back_populates="reminders")
    group = relationship("Group", back_populates="reminders", lazy="select")

    @property
    def group_name(self):
        return self.group.name if self.group else None

    __table_args__ = (
        Index("ix_reminders_user_id", "user_id"),
        Index("ix_reminders_status_scheduled", "status", "scheduled_time"),
        Index("ix_reminders_status_updated", "status", "updated_at"),
        Index("ix_reminders_group_id", "group_id"),
        {"schema": "SHR_V1"},
    )


class Group(Base):
    __tablename__ = "groups"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("SHR_V1.users.id"), nullable=False)
    name = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    owner = relationship("User", back_populates="groups")
    members = relationship("GroupMember", back_populates="group", cascade="all, delete-orphan")
    reminders = relationship("Reminder", back_populates="group")

    __table_args__ = (
        Index("ix_groups_user_id", "user_id"),
        Index("ix_groups_user_name", "user_id", "name"),
        {"schema": "SHR_V1"},
    )


class GroupMember(Base):
    __tablename__ = "group_members"

    id = Column(Integer, primary_key=True, autoincrement=True)
    group_id = Column(Integer, ForeignKey("SHR_V1.groups.id"), nullable=False)
    contact_id = Column(Integer, ForeignKey("SHR_V1.contacts.id"), nullable=False)

    group = relationship("Group", back_populates="members")
    contact = relationship("Contact")

    __table_args__ = (
        UniqueConstraint("group_id", "contact_id", name="uq_group_member"),
        {"schema": "SHR_V1"},
    )


class Contact(Base):
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("SHR_V1.users.id"), nullable=False)
    name = Column(String(100), nullable=False)
    phone_number = Column(String(20), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    owner = relationship("User", back_populates="contacts")

    __table_args__ = (
        Index("ix_contacts_user_id", "user_id"),
        Index("ix_contacts_user_phone", "user_id", "phone_number"),
        {"schema": "SHR_V1"},
    )


class ReminderTemplate(Base):
    __tablename__ = "reminder_templates"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("SHR_V1.users.id"), nullable=False)
    name = Column(String(100), nullable=False)
    title = Column(String(200), nullable=False)
    phone_number = Column(String(20), nullable=False)
    audio_filename = Column(Text, nullable=False)
    recurrence = Column(String(20), nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)
    retry_gap_minutes = Column(Integer, default=10, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    owner = relationship("User", back_populates="templates")

    __table_args__ = (
        Index("ix_reminder_templates_user_id", "user_id"),
        {"schema": "SHR_V1"},
    )
