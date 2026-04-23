from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta, date
from collections import Counter, defaultdict
from typing import List, Optional
from pydantic import BaseModel

from app.database import get_db
from app.models import Reminder, ReminderTemplate, Group, GroupMember, Contact
from app.auth import get_current_user

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


class TrendPoint(BaseModel):
    date: str
    count: int


class AnalyticsResponse(BaseModel):
    total_reminders: int
    success_rate: float
    sms_fallback_count: int
    total_retries: int
    failed_distribution: dict
    retry_distribution: dict
    trend_7_days: List[TrendPoint]
    template_count: int


def _chain_effective_status(attempts: list) -> str:
    """Return 'answered' if any attempt succeeded; otherwise the last attempt's status."""
    if any(a.status == "answered" for a in attempts):
        return "answered"
    last = max(attempts, key=lambda a: a.attempt_number)
    return last.status


@router.get("/analytics", response_model=AnalyticsResponse)
def get_analytics(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    user_id = current_user.id

    # Fetch all reminder rows for this user in one query
    all_rows = db.query(Reminder).filter(Reminder.user_id == user_id).all()

    parents = [r for r in all_rows if r.parent_reminder_id is None]
    retry_rows = [r for r in all_rows if r.parent_reminder_id is not None]

    total_reminders = len(parents)
    total_retries = len(retry_rows)

    # Build chains: parent id -> all attempt rows (parent + its retries)
    chains: dict = defaultdict(list)
    for r in parents:
        chains[r.id].append(r)
    for r in retry_rows:
        chains[r.parent_reminder_id].append(r)

    # Effective status per chain
    chain_statuses = Counter(_chain_effective_status(chains[p.id]) for p in parents)

    answered = chain_statuses.get("answered", 0)
    success_rate = round(answered / total_reminders * 100, 1) if total_reminders > 0 else 0.0

    # Failed distribution — based on final chain outcome
    failed_distribution = {
        "failed": chain_statuses.get("failed", 0),
        "no_answer": chain_statuses.get("no-answer", 0),
        "busy": chain_statuses.get("busy", 0),
    }

    # SMS fallback: idempotent flag, at most one row per chain has it set
    sms_fallback_count = sum(1 for r in all_rows if r.fallback_sent)

    # Retry config distribution — parent reminders only (user-configured max: 0–2)
    retry_distribution: dict = {"0": 0, "1": 0, "2": 0}
    for p in parents:
        key = str(p.retry_count)
        if key in retry_distribution:
            retry_distribution[key] += 1

    # 7-day trend — parent reminders only
    today = date.today()
    window_start = datetime.combine(today - timedelta(days=6), datetime.min.time())
    trend_counter: dict = {}
    for p in parents:
        if p.scheduled_time >= window_start:
            day = p.scheduled_time.date().isoformat()
            trend_counter[day] = trend_counter.get(day, 0) + 1

    trend_7_days = [
        TrendPoint(
            date=(today - timedelta(days=6 - i)).isoformat(),
            count=trend_counter.get((today - timedelta(days=6 - i)).isoformat(), 0),
        )
        for i in range(7)
    ]

    # Saved templates count
    template_count = (
        db.query(func.count(ReminderTemplate.id))
        .filter(ReminderTemplate.user_id == user_id)
        .scalar()
        or 0
    )

    return AnalyticsResponse(
        total_reminders=total_reminders,
        success_rate=success_rate,
        sms_fallback_count=sms_fallback_count,
        total_retries=total_retries,
        failed_distribution=failed_distribution,
        retry_distribution=retry_distribution,
        trend_7_days=trend_7_days,
        template_count=template_count,
    )


# ── Group Analytics ───────────────────────────────────────────────────────────

class BatchMember(BaseModel):
    name: str
    phone_number: str
    status: str


class ReminderBatch(BaseModel):
    title: str
    scheduled_time: datetime
    answered: int
    total: int
    members: List[BatchMember]


class GroupSummary(BaseModel):
    group_id: int
    group_name: str
    member_count: int
    total_batches: int
    total_calls: int
    answer_rate: float
    last_used: Optional[str]
    batches: List[ReminderBatch]


class MemberReliability(BaseModel):
    contact_id: int
    name: str
    phone_number: str
    total_calls: int
    answered: int
    answer_rate: float


class GroupAnalyticsResponse(BaseModel):
    groups: List[GroupSummary]
    member_reliability: List[MemberReliability]


def _effective_status(rows: list) -> str:
    """Return answered if any attempt answered, else the last attempt's status."""
    if any(r.status == "answered" for r in rows):
        return "answered"
    return max(rows, key=lambda r: r.attempt_number).status


@router.get("/group-analytics", response_model=GroupAnalyticsResponse)
def get_group_analytics(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    user_id = current_user.id

    groups = db.query(Group).filter(Group.user_id == user_id).order_by(Group.name).all()
    if not groups:
        return GroupAnalyticsResponse(groups=[], member_reliability=[])

    group_ids = [g.id for g in groups]

    # All reminders belonging to any group (includes retry children)
    all_group_reminders = (
        db.query(Reminder)
        .filter(Reminder.user_id == user_id, Reminder.group_id.in_(group_ids))
        .all()
    )

    # Separate parents (original calls) from retry children
    parents = [r for r in all_group_reminders if r.parent_reminder_id is None]
    children = [r for r in all_group_reminders if r.parent_reminder_id is not None]

    # Map parent_id -> all attempt rows for effective status
    attempt_map: dict = defaultdict(list)
    for r in parents:
        attempt_map[r.id].append(r)
    for r in children:
        attempt_map[r.parent_reminder_id].append(r)

    # Build phone -> contact name map from group members
    members_rows = (
        db.query(GroupMember, Contact)
        .join(Contact, GroupMember.contact_id == Contact.id)
        .filter(GroupMember.group_id.in_(group_ids))
        .all()
    )
    # phone_number -> contact name (last-wins if duplicate, acceptable)
    phone_to_name: dict = {c.phone_number: c.name for _, c in members_rows}
    # contact_id -> contact for reliability section
    contact_id_to_contact: dict = {c.id: c for _, c in members_rows}
    # group_id -> list of contact_ids for member_count
    group_contact_ids: dict = defaultdict(set)
    for gm, c in members_rows:
        group_contact_ids[gm.group_id].add(c.id)

    # ── Build per-group summaries ────────────────────────────────────────────
    # Group parent reminders by (group_id, title, scheduled_time minute)
    # reminders created in the same batch share the exact same scheduled_time
    batch_key = lambda r: (r.group_id, r.title, r.scheduled_time.replace(second=0, microsecond=0))

    parents_by_group: dict = defaultdict(list)
    for r in parents:
        parents_by_group[r.group_id].append(r)

    group_summaries = []
    for g in groups:
        g_parents = parents_by_group.get(g.id, [])

        # Group into batches
        batches_map: dict = defaultdict(list)
        for r in g_parents:
            batches_map[batch_key(r)].append(r)

        built_batches = []
        for (gid, title, sched), batch_rows in sorted(
            batches_map.items(), key=lambda x: x[0][2], reverse=True
        ):
            batch_members = []
            answered_count = 0
            for r in batch_rows:
                eff = _effective_status(attempt_map[r.id])
                if eff == "answered":
                    answered_count += 1
                batch_members.append(BatchMember(
                    name=phone_to_name.get(r.phone_number, r.phone_number),
                    phone_number=r.phone_number,
                    status=eff,
                ))
            built_batches.append(ReminderBatch(
                title=title,
                scheduled_time=sched,
                answered=answered_count,
                total=len(batch_rows),
                members=sorted(batch_members, key=lambda m: m.name),
            ))

        total_calls = len(g_parents)
        answered_total = sum(
            1 for r in g_parents if _effective_status(attempt_map[r.id]) == "answered"
        )
        answer_rate = round(answered_total / total_calls * 100, 1) if total_calls > 0 else 0.0
        last_used = (
            max(g_parents, key=lambda r: r.scheduled_time).scheduled_time.date().isoformat()
            if g_parents else None
        )

        group_summaries.append(GroupSummary(
            group_id=g.id,
            group_name=g.name,
            member_count=len(group_contact_ids.get(g.id, set())),
            total_batches=len(built_batches),
            total_calls=total_calls,
            answer_rate=answer_rate,
            last_used=last_used,
            batches=built_batches,
        ))

    # ── Member reliability ────────────────────────────────────────────────────
    # Per phone number across all group reminders
    phone_stats: dict = defaultdict(lambda: {"total": 0, "answered": 0})
    for r in parents:
        eff = _effective_status(attempt_map[r.id])
        phone_stats[r.phone_number]["total"] += 1
        if eff == "answered":
            phone_stats[r.phone_number]["answered"] += 1

    # Map phone -> contact (use members_rows lookup)
    phone_to_contact_id: dict = {c.phone_number: c.id for _, c in members_rows}

    reliability = []
    for phone, stats in sorted(phone_stats.items(), key=lambda x: -x[1]["total"]):
        total = stats["total"]
        ans = stats["answered"]
        cid = phone_to_contact_id.get(phone, -1)
        contact = contact_id_to_contact.get(cid)
        reliability.append(MemberReliability(
            contact_id=cid,
            name=contact.name if contact else phone,
            phone_number=phone,
            total_calls=total,
            answered=ans,
            answer_rate=round(ans / total * 100, 1) if total > 0 else 0.0,
        ))

    return GroupAnalyticsResponse(groups=group_summaries, member_reliability=reliability)
