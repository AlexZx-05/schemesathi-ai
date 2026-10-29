"""Notification preferences, history, and idempotent deadline reminder jobs."""

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Callable
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session, selectinload

from .auth import _check_origin, get_current_user
from .database import SessionLocal, get_db
from .email_delivery import send_notification_email
from .models import (
    ApplicationTracking,
    AuditLog,
    Notification,
    NotificationPreference,
    SavedScheme,
    Scheme,
    SchemeDeadline,
    SchemeSource,
    User,
    utc_now,
)
from .notification_schemas import (
    DeadlineUpdateRequest,
    NotificationPageResponse,
    NotificationPreferencesResponse,
    NotificationPreferencesUpdate,
    NotificationReadRequest,
    NotificationResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["notifications"])
DEFAULT_TIMEZONE = "Asia/Kolkata"
REMINDER_DAYS = (7, 1)
MAX_EMAIL_ATTEMPTS = 5


def _aware(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def _freshness_days() -> int:
    configured = os.getenv("KNOWLEDGE_MAX_AGE_DAYS", "365")
    try:
        days = int(configured)
    except ValueError as error:
        raise RuntimeError("KNOWLEDGE_MAX_AGE_DAYS must be a positive integer.") from error
    if days < 1:
        raise RuntimeError("KNOWLEDGE_MAX_AGE_DAYS must be a positive integer.")
    return days


def _source_is_current(source: SchemeSource | None, now: datetime) -> bool:
    return bool(
        source
        and source.status == "verified"
        and source.last_verified_at
        and _aware(source.last_verified_at) >= now - timedelta(days=_freshness_days())
    )


def _deadline_is_current(deadline: SchemeDeadline, now: datetime) -> bool:
    scheme = deadline.scheme
    return bool(
        deadline.deadline_status == "known"
        and deadline.closes_at
        and deadline.last_verified_at
        and _aware(deadline.last_verified_at) >= now - timedelta(days=_freshness_days())
        and _source_is_current(deadline.source, now)
        and not scheme.is_demo
        and scheme.status == "active"
        and scheme.verification_status == "verified"
        and not scheme.requires_human_review
    )


def _scheme_is_current(scheme: Scheme) -> bool:
    return (
        not scheme.is_demo
        and scheme.status == "active"
        and scheme.verification_status == "verified"
        and not scheme.requires_human_review
    )


def _preference_values(preference: NotificationPreference | None) -> dict[str, object]:
    if preference is None:
        return {
            "in_app_enabled": True,
            "email_enabled": False,
            "reminders_enabled": True,
            "deadline_reminders_enabled": True,
            "timezone": DEFAULT_TIMEZONE,
            "updated_at": None,
        }
    return {
        "in_app_enabled": preference.in_app_enabled,
        "email_enabled": preference.email_enabled,
        "reminders_enabled": preference.reminders_enabled,
        "deadline_reminders_enabled": preference.deadline_reminders_enabled,
        "timezone": preference.timezone,
        "updated_at": preference.updated_at,
    }


def _notification_response(notification: Notification) -> NotificationResponse:
    return NotificationResponse(
        id=notification.id,
        notification_type=notification.notification_type,
        title=notification.title,
        message=notification.message,
        created_at=notification.created_at,
        read_at=notification.read_at,
        is_valid=notification.is_valid,
        deadline_at=notification.deadline_at,
        source_url=notification.source.url if notification.source else None,
        source_verified_at=notification.source_verified_at,
        email_delivery_status=notification.email_delivery_status,
    )


@router.get("/notifications/preferences", response_model=NotificationPreferencesResponse)
def get_notification_preferences(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> NotificationPreferencesResponse:
    preference = db.scalar(
        select(NotificationPreference).where(NotificationPreference.user_id == user.id)
    )
    return NotificationPreferencesResponse(**_preference_values(preference))


@router.put("/notifications/preferences", response_model=NotificationPreferencesResponse)
def update_notification_preferences(
    payload: NotificationPreferencesUpdate,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NotificationPreferencesResponse:
    _check_origin(request)
    preference = db.scalar(
        select(NotificationPreference).where(NotificationPreference.user_id == user.id)
    )
    if preference is None:
        preference = NotificationPreference(user_id=user.id)
        db.add(preference)
    for field, value in payload.model_dump().items():
        setattr(preference, field, value)
    db.add(
        AuditLog(
            actor_user_id=user.id,
            action="notification_preferences.updated",
            entity_type="notification_preference",
            entity_id=str(user.id),
            details={
                "in_app_enabled": payload.in_app_enabled,
                "email_enabled": payload.email_enabled,
                "reminders_enabled": payload.reminders_enabled,
                "deadline_reminders_enabled": payload.deadline_reminders_enabled,
            },
        )
    )
    db.commit()
    db.refresh(preference)
    return NotificationPreferencesResponse(**_preference_values(preference))


@router.get("/notifications", response_model=NotificationPageResponse)
def list_notifications(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    unread_only: bool = False,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NotificationPageResponse:
    conditions = [
        Notification.user_id == user.id,
        Notification.in_app_visible.is_(True),
    ]
    if unread_only:
        conditions.append(Notification.read_at.is_(None))
    total = db.scalar(
        select(func.count(Notification.id)).where(*conditions)
    ) or 0
    unread_count = db.scalar(
        select(func.count(Notification.id)).where(
            Notification.user_id == user.id,
            Notification.in_app_visible.is_(True),
            Notification.is_valid.is_(True),
            Notification.read_at.is_(None),
        )
    ) or 0
    records = db.scalars(
        select(Notification)
        .where(*conditions)
        .options(selectinload(Notification.source))
        .order_by(Notification.created_at.desc(), Notification.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return NotificationPageResponse(
        items=[_notification_response(item) for item in records],
        unread_count=unread_count,
        page=page,
        page_size=page_size,
        total=total,
    )


@router.patch("/notifications/{notification_id}/read", response_model=NotificationResponse)
def set_notification_read(
    notification_id: int,
    payload: NotificationReadRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NotificationResponse:
    _check_origin(request)
    notification = db.scalar(
        select(Notification)
        .where(
            Notification.id == notification_id,
            Notification.user_id == user.id,
            Notification.in_app_visible.is_(True),
        )
        .options(selectinload(Notification.source))
    )
    if notification is None:
        raise HTTPException(status_code=404, detail="Notification not found.")
    notification.read_at = utc_now() if payload.read else None
    db.add(
        AuditLog(
            actor_user_id=user.id,
            action="notification.read_status_changed",
            entity_type="notification",
            entity_id=str(notification.id),
            details={"read": payload.read},
        )
    )
    db.commit()
    db.refresh(notification)
    return _notification_response(notification)


def _require_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Administrator access is required.")
    return user


@router.put("/admin/schemes/{scheme_id}/deadlines/{deadline_id}", tags=["scheme administration"])
def update_verified_deadline(
    scheme_id: str,
    deadline_id: int,
    payload: DeadlineUpdateRequest,
    request: Request,
    admin: User = Depends(_require_admin),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    _check_origin(request)
    scheme = db.scalar(select(Scheme).where(Scheme.slug == scheme_id))
    deadline = db.scalar(
        select(SchemeDeadline).where(
            SchemeDeadline.id == deadline_id,
            SchemeDeadline.scheme_id == scheme.id if scheme else False,
        )
    )
    if scheme is None or deadline is None:
        raise HTTPException(status_code=404, detail="Scheme deadline not found.")

    source = db.get(SchemeSource, payload.source_id) if payload.source_id else None
    if payload.deadline_status == "known":
        if (
            not _scheme_is_current(scheme)
            or source is None
            or source.scheme_id != scheme.id
            or not _source_is_current(source, utc_now())
        ):
            raise HTTPException(
                status_code=422,
                detail="A known deadline must cite a current verified source for this scheme.",
            )
    old_close = _aware(deadline.closes_at) if deadline.closes_at else None
    new_close = _aware(payload.closes_at) if payload.closes_at else None
    changed = (
        old_close != new_close
        or deadline.source_id != payload.source_id
        or deadline.deadline_status != payload.deadline_status
    )
    deadline.deadline_type = payload.deadline_type
    deadline.deadline_status = payload.deadline_status
    deadline.closes_at = payload.closes_at
    deadline.opens_at = payload.opens_at
    deadline.source_id = payload.source_id
    deadline.last_verified_at = utc_now() if payload.deadline_status == "known" else None
    deadline.notes = payload.notes
    if changed:
        for notification in db.scalars(
            select(Notification).where(
                Notification.deadline_id == deadline.id,
                Notification.is_valid.is_(True),
            )
        ):
            notification.is_valid = False
            if notification.email_delivery_status in {"pending", "failed", "sending"}:
                notification.email_delivery_status = "invalidated"
                notification.email_failure = "Deadline or its source was updated."
                notification.email_next_attempt_at = None
    db.add(
        AuditLog(
            actor_user_id=admin.id,
            action="scheme_deadline.verified_update",
            entity_type="scheme_deadline",
            entity_id=str(deadline.id),
            details={
                "scheme_id": scheme.slug,
                "deadline_status": deadline.deadline_status,
                "source_id": deadline.source_id,
                "changed": changed,
            },
        )
    )
    db.commit()
    return {
        "deadline_id": deadline.id,
        "deadline_status": deadline.deadline_status,
        "closes_at": deadline.closes_at,
        "source_id": deadline.source_id,
        "last_verified_at": deadline.last_verified_at,
    }


@router.post(
    "/admin/schemes/{scheme_id}/deadlines",
    status_code=201,
    tags=["scheme administration"],
)
def create_verified_deadline(
    scheme_id: str,
    payload: DeadlineUpdateRequest,
    request: Request,
    admin: User = Depends(_require_admin),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    _check_origin(request)
    scheme = db.scalar(select(Scheme).where(Scheme.slug == scheme_id))
    if scheme is None:
        raise HTTPException(status_code=404, detail="Scheme not found.")
    source = db.get(SchemeSource, payload.source_id) if payload.source_id else None
    if payload.deadline_status == "known" and (
        not _scheme_is_current(scheme)
        or source is None
        or source.scheme_id != scheme.id
        or not _source_is_current(source, utc_now())
    ):
        raise HTTPException(
            status_code=422,
            detail="A known deadline must cite a current verified source for this scheme.",
        )
    deadline = SchemeDeadline(
        scheme_id=scheme.id,
        deadline_type=payload.deadline_type,
        deadline_status=payload.deadline_status,
        opens_at=payload.opens_at,
        closes_at=payload.closes_at,
        source_id=payload.source_id,
        last_verified_at=utc_now() if payload.deadline_status == "known" else None,
        notes=payload.notes,
    )
    db.add(deadline)
    db.flush()
    db.add(
        AuditLog(
            actor_user_id=admin.id,
            action="scheme_deadline.created",
            entity_type="scheme_deadline",
            entity_id=str(deadline.id),
            details={
                "scheme_id": scheme.slug,
                "deadline_status": deadline.deadline_status,
                "source_id": deadline.source_id,
            },
        )
    )
    db.commit()
    return {
        "deadline_id": deadline.id,
        "deadline_status": deadline.deadline_status,
        "closes_at": deadline.closes_at,
        "source_id": deadline.source_id,
        "last_verified_at": deadline.last_verified_at,
    }


def _recipient_ids(db: Session, scheme_id: int) -> list[int]:
    statement = select(SavedScheme.user_id).where(SavedScheme.scheme_id == scheme_id).union(
        select(ApplicationTracking.user_id).where(
            ApplicationTracking.scheme_id == scheme_id,
            ApplicationTracking.status.not_in(["completed", "not_proceeding"]),
        )
    )
    return list(db.scalars(statement).all())


def _reminder_is_due(deadline_at: datetime, now: datetime, timezone_name: str) -> list[int]:
    local_now = now.astimezone(ZoneInfo(timezone_name))
    local_deadline = deadline_at.astimezone(ZoneInfo(timezone_name))
    remaining_days = (local_deadline.date() - local_now.date()).days
    return [
        reminder_days
        for reminder_days in REMINDER_DAYS
        if 0 < remaining_days <= reminder_days
    ]


def _invalidate_outdated_notifications(db: Session, now: datetime) -> int:
    candidates = db.scalars(
        select(Notification)
        .where(
            Notification.deadline_id.is_not(None),
            Notification.is_valid.is_(True),
        )
        .options(
            selectinload(Notification.deadline)
            .selectinload(SchemeDeadline.scheme),
            selectinload(Notification.deadline)
            .selectinload(SchemeDeadline.source),
        )
    ).all()
    invalidated = 0
    for notification in candidates:
        deadline = notification.deadline
        if (
            deadline is None
            or not _deadline_is_current(deadline, now)
            or _aware(deadline.closes_at) != _aware(notification.deadline_at)
            or deadline.source_id != notification.source_id
            or _aware(deadline.source.last_verified_at)
            != _aware(notification.source_verified_at)
        ):
            notification.is_valid = False
            if notification.email_delivery_status in {"pending", "failed", "sending"}:
                notification.email_delivery_status = "invalidated"
                notification.email_failure = "Deadline or source verification is no longer current."
                notification.email_next_attempt_at = None
            invalidated += 1
    return invalidated


def run_deadline_reminders(
    db: Session,
    now: datetime | None = None,
    email_sender: Callable[[str, str, str], None] = send_notification_email,
) -> dict[str, int]:
    """Create unique reminder records and retry eligible email deliveries."""
    current = _aware(now or datetime.now(timezone.utc))
    freshness_cutoff = current - timedelta(days=_freshness_days())
    deadlines = db.scalars(
        select(SchemeDeadline)
        .join(Scheme, SchemeDeadline.scheme_id == Scheme.id)
        .where(
            SchemeDeadline.deadline_status == "known",
            SchemeDeadline.closes_at > current,
            SchemeDeadline.last_verified_at.is_not(None),
            SchemeDeadline.last_verified_at >= freshness_cutoff,
            Scheme.is_demo.is_(False),
            Scheme.status == "active",
            Scheme.verification_status == "verified",
            Scheme.requires_human_review.is_(False),
        )
        .options(
            selectinload(SchemeDeadline.scheme),
            selectinload(SchemeDeadline.source),
        )
    ).all()
    created = 0
    invalidated = _invalidate_outdated_notifications(db, current)
    dialect = db.get_bind().dialect.name
    insert = sqlite_insert if dialect == "sqlite" else pg_insert
    for deadline in deadlines:
        if not _deadline_is_current(deadline, current):
            continue
        closes_at = _aware(deadline.closes_at)
        for user_id in _recipient_ids(db, deadline.scheme_id):
            preference = db.scalar(
                select(NotificationPreference).where(
                    NotificationPreference.user_id == user_id
                )
            )
            values = _preference_values(preference)
            if not values["reminders_enabled"] or not values["deadline_reminders_enabled"]:
                continue
            if not values["in_app_enabled"] and not values["email_enabled"]:
                continue
            timezone_name = str(values["timezone"])
            for reminder_days in _reminder_is_due(closes_at, current, timezone_name):
                dedupe_key = (
                    f"deadline:{deadline.id}:{closes_at.isoformat()}:"
                    f"{reminder_days}:{user_id}"
                )
                local_closing_time = closes_at.astimezone(ZoneInfo(timezone_name))
                actual_days_remaining = (
                    local_closing_time.date()
                    - current.astimezone(ZoneInfo(timezone_name)).date()
                ).days
                title = (
                    f"{deadline.scheme.name} deadline in "
                    f"{actual_days_remaining} day(s)"
                )
                message = (
                    f"A deadline recorded for {deadline.scheme.name} is approaching. "
                    f"Recorded closing time: {local_closing_time.isoformat()}. "
                    f"The linked official source was last verified "
                    f"{_aware(deadline.source.last_verified_at).date().isoformat()}: "
                    f"{deadline.source.url}. Verify it before acting."
                )
                statement = insert(Notification).values(
                    user_id=user_id,
                    notification_type="verified_deadline_reminder",
                    title=title,
                    message=message,
                    dedupe_key=dedupe_key,
                    deadline_id=deadline.id,
                    deadline_at=closes_at,
                    source_id=deadline.source_id,
                    source_verified_at=deadline.source.last_verified_at,
                    is_valid=True,
                    in_app_visible=bool(values["in_app_enabled"]),
                    email_delivery_status=(
                        "pending" if values["email_enabled"] else "not_requested"
                    ),
                    email_next_attempt_at=current if values["email_enabled"] else None,
                )
                result = db.execute(
                    statement.on_conflict_do_nothing(index_elements=["dedupe_key"])
                )
                created += result.rowcount or 0
    db.commit()

    email_sent = 0
    email_failed = 0
    email_skipped = 0
    if os.getenv("ENVIRONMENT", "").strip().lower() == "test":
        skipped = db.scalars(
            select(Notification).where(
                Notification.email_delivery_status == "pending",
                Notification.email_next_attempt_at <= current,
            )
        ).all()
        for item in skipped:
            item.email_delivery_status = "skipped"
            item.email_failure = "Email delivery is disabled in test environments."
            item.email_next_attempt_at = None
            email_skipped += 1
        db.commit()
    else:
        candidates = db.scalars(
            select(Notification)
            .where(
                Notification.email_delivery_status.in_(["pending", "failed", "sending"]),
                Notification.email_attempts < MAX_EMAIL_ATTEMPTS,
                Notification.email_next_attempt_at <= current,
                Notification.is_valid.is_(True),
            )
            .order_by(Notification.id)
            .limit(100)
        ).all()
        for item in candidates:
            claimed = db.execute(
                update(Notification)
                .where(
                    Notification.id == item.id,
                    Notification.email_delivery_status
                    == item.email_delivery_status,
                    Notification.email_attempts == item.email_attempts,
                )
                .values(
                    email_delivery_status="sending",
                    email_attempts=Notification.email_attempts + 1,
                    email_next_attempt_at=current + timedelta(minutes=15),
                )
            )
            if claimed.rowcount != 1:
                continue
            db.commit()
            notification = db.scalar(
                select(Notification)
                .where(Notification.id == item.id)
                .options(selectinload(Notification.user), selectinload(Notification.deadline)
                         .selectinload(SchemeDeadline.scheme))
            )
            preference = (
                notification.user.notification_preferences
                if notification is not None and notification.user is not None
                else None
            )
            if (
                notification is None
                or notification.user is None
                or preference is None
                or not preference.email_enabled
                or not preference.reminders_enabled
                or not preference.deadline_reminders_enabled
            ):
                if notification is not None:
                    notification.email_delivery_status = "skipped"
                    notification.email_failure = "Email reminders are disabled in current user preferences."
                    notification.email_next_attempt_at = None
                    db.commit()
                continue
            if (
                notification.deadline is None
                or not _deadline_is_current(notification.deadline, current)
                or _aware(notification.deadline.closes_at) != _aware(notification.deadline_at)
                or notification.deadline.source_id != notification.source_id
                or _aware(notification.deadline.source.last_verified_at)
                != _aware(notification.source_verified_at)
            ):
                if notification is not None:
                    notification.is_valid = False
                    notification.email_delivery_status = "invalidated"
                    notification.email_failure = "Deadline or source could not be re-verified before delivery."
                    notification.email_next_attempt_at = None
                    db.commit()
                continue
            try:
                email_sender(
                    notification.user.email,
                    notification.title,
                    notification.message,
                )
            except (RuntimeError, ValueError) as error:
                attempts = notification.email_attempts
                notification.email_delivery_status = "failed"
                notification.email_failure = str(error)[:500]
                notification.email_next_attempt_at = (
                    current + timedelta(minutes=min(60, 2**attempts))
                    if attempts < MAX_EMAIL_ATTEMPTS
                    else None
                )
                email_failed += 1
                logger.warning(
                    "Deadline notification email failed: notification_id=%s attempt=%s",
                    notification.id,
                    attempts,
                )
            else:
                notification.email_delivery_status = "sent"
                notification.email_sent_at = current
                notification.email_failure = None
                notification.email_next_attempt_at = None
                email_sent += 1
            db.commit()
    return {
        "created": created,
        "invalidated": invalidated,
        "email_sent": email_sent,
        "email_failed": email_failed,
        "email_skipped": email_skipped,
    }


def main() -> None:
    with SessionLocal() as db:
        result = run_deadline_reminders(db)
    logger.info("Deadline reminder run finished: %s", result)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
