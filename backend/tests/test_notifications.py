from collections.abc import Generator
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database import Base, get_db
from backend.app.main import app
from backend.app.models import (
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
from backend.app.notifications import _reminder_is_due, run_deadline_reminders
from backend.tests.catalog_fixtures import seed_catalog_test_fixtures

TEST_ENGINE = create_engine(
    "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(bind=TEST_ENGINE, autoflush=False, expire_on_commit=False)


def override_get_db() -> Generator[Session, None, None]:
    with TestingSessionLocal() as session:
        yield session


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Generator[TestClient, None, None]:
    monkeypatch.setenv("EMAIL_PROVIDER", "development")
    monkeypatch.setenv("ENVIRONMENT", "test")
    Base.metadata.drop_all(bind=TEST_ENGINE)
    Base.metadata.create_all(bind=TEST_ENGINE)
    with TestingSessionLocal() as db:
        seed_catalog_test_fixtures(db)
        scheme = db.scalar(select(Scheme).where(Scheme.slug == "demo-education"))
        assert scheme is not None
        scheme.is_demo = False
        scheme.status = "active"
        scheme.verification_status = "verified"
        scheme.requires_human_review = False
        scheme.last_verified_at = utc_now()
        source = SchemeSource(
            scheme_id=scheme.id,
            url="https://official.gov.example/scheme",
            title="Official scheme page",
            source_type="government_document",
            official_domain="official.gov.example",
            status="verified",
            last_verified_at=utc_now(),
        )
        db.add(source)
        db.flush()
        db.add(
            SchemeDeadline(
                scheme_id=scheme.id,
                deadline_type="application",
                closes_at=utc_now() + timedelta(days=7),
                deadline_status="known",
                source_id=source.id,
                last_verified_at=utc_now(),
            )
        )
        db.commit()
    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()
    test_client.close()


def sign_in(client: TestClient, email: str) -> None:
    assert client.post(
        "/auth/register",
        json={"email": email, "full_name": "Reminder User", "password": "correct horse battery"},
    ).status_code == 202
    token = client.get("/auth/dev-email", params={"email": email, "purpose": "verification"})
    assert client.post("/auth/verify-email", json={"token": token.json()["token"]}).status_code == 200
    assert client.post("/auth/login", json={"email": email, "password": "correct horse battery"}).status_code == 200


def _prepare_saved_user(email: str = "alerts@example.com") -> int:
    with TestingSessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        if user is None:
            user = User(
                email=email,
                full_name="Reminder User",
                password_hash="not-used-in-this-job-test",
                email_verified=True,
            )
            db.add(user)
            db.flush()
        scheme = db.scalar(select(Scheme).where(Scheme.slug == "demo-education"))
        assert scheme is not None
        db.add(SavedScheme(user_id=user.id, scheme_id=scheme.id))
        db.commit()
        return user.id


def test_deadline_job_is_idempotent_and_requires_verified_current_source(
    client: TestClient,
) -> None:
    user_id = _prepare_saved_user()
    with TestingSessionLocal() as db:
        deadline = db.scalar(select(SchemeDeadline))
        assert deadline is not None and deadline.closes_at is not None
        now = utc_now()
        deadline.closes_at = now + timedelta(days=7)
        db.commit()
        first = run_deadline_reminders(db, now=now)
        second = run_deadline_reminders(db, now=now)
        assert first["created"] == 1
        assert second["created"] == 0
        notifications = db.scalars(
            select(Notification).where(Notification.user_id == user_id)
        ).all()
        assert len(notifications) == 1
        assert notifications[0].source_id == deadline.source_id
        assert notifications[0].email_delivery_status == "not_requested"
        assert "https://official.gov.example/scheme" in notifications[0].message
        assert "last verified" in notifications[0].message

        deadline.deadline_status = "unknown"
        db.commit()
        assert run_deadline_reminders(db, now=now)["created"] == 0


def test_deadline_notification_preferences_read_state_and_ownership(
    client: TestClient,
) -> None:
    sign_in(client, "prefs-owner@example.com")
    defaults = client.get("/api/v1/notifications/preferences")
    assert defaults.status_code == 200
    assert defaults.json()["timezone"] == "Asia/Kolkata"
    updated = client.put(
        "/api/v1/notifications/preferences",
        json={
            "in_app_enabled": True,
            "email_enabled": False,
            "reminders_enabled": True,
            "deadline_reminders_enabled": False,
            "timezone": "America/Los_Angeles",
        },
    )
    assert updated.status_code == 200
    assert client.put(
        "/api/v1/notifications/preferences",
        json={
            "in_app_enabled": True,
            "email_enabled": False,
            "reminders_enabled": True,
            "deadline_reminders_enabled": True,
            "timezone": "not/a-zone",
        },
    ).status_code == 422

    user_id = _prepare_saved_user("prefs-owner@example.com")
    with TestingSessionLocal() as db:
        user = db.get(User, user_id)
        assert user is not None
        preference = user.notification_preferences
        assert preference is not None
        preference.timezone = "Asia/Kolkata"
        deadline = db.scalar(select(SchemeDeadline))
        assert deadline is not None
        deadline.closes_at = utc_now() + timedelta(days=7)
        db.commit()
        assert run_deadline_reminders(db)["created"] == 0
        preference.deadline_reminders_enabled = True
        db.commit()
        run_deadline_reminders(db)

    listed = client.get("/api/v1/notifications")
    assert listed.status_code == 200
    assert listed.json()["unread_count"] == 1
    notification_id = listed.json()["items"][0]["id"]
    assert client.patch(
        f"/api/v1/notifications/{notification_id}/read", json={"read": True}
    ).status_code == 200
    assert client.get("/api/v1/notifications").json()["unread_count"] == 0
    assert client.post("/auth/logout").status_code == 204
    sign_in(client, "prefs-other@example.com")
    assert client.patch(
        f"/api/v1/notifications/{notification_id}/read", json={"read": False}
    ).status_code == 404


def test_changed_deadline_invalidates_old_notification(client: TestClient) -> None:
    user_id = _prepare_saved_user("changed@example.com")
    with TestingSessionLocal() as db:
        deadline = db.scalar(select(SchemeDeadline))
        assert deadline is not None
        now = utc_now()
        deadline.closes_at = now + timedelta(days=7)
        db.commit()
        run_deadline_reminders(db, now=now)
        notification = db.scalar(
            select(Notification).where(Notification.user_id == user_id)
        )
        assert notification is not None and notification.is_valid
        deadline.closes_at = now + timedelta(days=10)
        db.commit()
        result = run_deadline_reminders(db, now=now)
        db.refresh(notification)
        assert result["invalidated"] == 1
        assert notification.is_valid is False


def test_email_failure_is_recorded_and_retryable_without_real_delivery(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    user_id = _prepare_saved_user("email@example.com")
    monkeypatch.setenv("ENVIRONMENT", "production")
    with TestingSessionLocal() as db:
        user = db.get(User, user_id)
        assert user is not None
        user.notification_preferences = NotificationPreference(
            in_app_enabled=True,
            email_enabled=True,
            reminders_enabled=True,
            deadline_reminders_enabled=True,
            timezone="Asia/Kolkata",
        )
        now = utc_now()
        deadline = db.scalar(select(SchemeDeadline))
        assert deadline is not None
        deadline.closes_at = now + timedelta(days=7)
        db.commit()

        def failed_sender(*_args: str) -> None:
            raise RuntimeError("simulated SMTP outage")

        result = run_deadline_reminders(db, now=now, email_sender=failed_sender)
        assert result["email_failed"] == 1
        notification = db.scalar(
            select(Notification).where(Notification.user_id == user_id)
        )
        assert notification is not None
        assert notification.email_delivery_status == "failed"
        assert notification.email_attempts == 1
        assert "SMTP outage" in (notification.email_failure or "")

        def successful_sender(*_args: str) -> None:
            return None

        result = run_deadline_reminders(
            db,
            now=now + timedelta(minutes=10),
            email_sender=successful_sender,
        )
        assert result["email_sent"] == 1
        db.refresh(notification)
        assert notification.email_delivery_status == "sent"
        assert notification.email_attempts == 2


def test_test_environment_never_calls_email_sender(client: TestClient) -> None:
    user_id = _prepare_saved_user("test-no-email@example.com")
    with TestingSessionLocal() as db:
        user = db.get(User, user_id)
        assert user is not None
        user.notification_preferences = NotificationPreference(
            in_app_enabled=True,
            email_enabled=True,
            reminders_enabled=True,
            deadline_reminders_enabled=True,
            timezone="Asia/Kolkata",
        )
        deadline = db.scalar(select(SchemeDeadline))
        assert deadline is not None
        deadline.closes_at = utc_now() + timedelta(days=7)
        db.commit()
        called = False

        def forbidden_sender(*_args: str) -> None:
            nonlocal called
            called = True

        result = run_deadline_reminders(
            db, now=utc_now(), email_sender=forbidden_sender
        )
        notification = db.scalar(
            select(Notification).where(Notification.user_id == user_id)
        )
        assert result["email_skipped"] == 1
        assert not called
        assert notification is not None
        assert notification.email_delivery_status == "skipped"


def test_reminder_calendar_uses_user_timezone() -> None:
    now = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
    deadline = datetime(2026, 1, 2, 6, 0, tzinfo=timezone.utc)
    assert _reminder_is_due(deadline, now, "Asia/Kolkata") == [7, 1]
    assert _reminder_is_due(deadline, now, "America/Los_Angeles") == []


def test_admin_must_link_known_deadline_to_current_verified_scheme_source(
    client: TestClient,
) -> None:
    sign_in(client, "deadline-admin@example.com")
    with TestingSessionLocal() as db:
        admin = db.scalar(select(User).where(User.email == "deadline-admin@example.com"))
        source = db.scalar(select(SchemeSource))
        assert admin is not None and source is not None
        admin.is_admin = True
        db.commit()

    created = client.post(
        "/api/v1/admin/schemes/demo-education/deadlines",
        json={
            "deadline_type": "application",
            "deadline_status": "known",
            "closes_at": (utc_now() + timedelta(days=20)).isoformat(),
            "source_id": source.id,
            "notes": "Confirmed against the official source.",
        },
    )
    assert created.status_code == 201
    assert created.json()["last_verified_at"] is not None
    with TestingSessionLocal() as db:
        actions = db.scalars(
            select(AuditLog.action).where(AuditLog.action == "scheme_deadline.created")
        ).all()
        assert actions == ["scheme_deadline.created"]

    assert client.post(
        "/api/v1/admin/schemes/demo-education/deadlines",
        json={
            "deadline_type": "application",
            "deadline_status": "known",
            "closes_at": (utc_now() + timedelta(days=20)).isoformat(),
            "source_id": source.id + 999,
        },
    ).status_code == 422
