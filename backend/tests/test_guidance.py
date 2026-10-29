from collections.abc import Generator
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database import Base, get_db
from backend.app.main import app
from backend.app.models import AuditLog, Scheme, SchemeDocument, SchemeSource, utc_now
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
        scheme.application_instructions = "Review your documents\nApply through the department portal"
        scheme.official_application_url = "https://policy.gov.example/apply"
        scheme.documents = [
            SchemeDocument(name="Identity proof", is_required=True, sort_order=1),
            SchemeDocument(name="Address proof", is_required=False, sort_order=2),
        ]
        db.add(
            SchemeSource(
                scheme_id=scheme.id,
                url="https://policy.gov.example/education",
                title="Education department",
                source_type="government_document",
                official_domain="gov.example",
                status="verified",
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
        json={"email": email, "full_name": "Guidance User", "password": "correct horse battery"},
    ).status_code == 202
    token = client.get("/auth/dev-email", params={"email": email, "purpose": "verification"})
    assert client.post("/auth/verify-email", json={"token": token.json()["token"]}).status_code == 200
    assert client.post("/auth/login", json={"email": email, "password": "correct horse battery"}).status_code == 200


def test_save_unsave_duplicate_and_unavailable_records(client: TestClient) -> None:
    sign_in(client, "saved@example.com")
    saved = client.post("/api/v1/saved-schemes/demo-education")
    assert saved.status_code == 201
    assert saved.json()["guidance_available"] is True
    assert client.post("/api/v1/saved-schemes/demo-education").status_code == 409
    assert len(client.get("/api/v1/saved-schemes").json()) == 1
    assert client.delete("/api/v1/saved-schemes/demo-education").status_code == 204
    assert client.get("/api/v1/saved-schemes").json() == []

    with TestingSessionLocal() as db:
        scheme = db.scalar(select(Scheme).where(Scheme.slug == "demo-education"))
        assert scheme is not None
        scheme.status = "inactive"
        db.commit()
    inactive = client.post("/api/v1/saved-schemes/demo-education")
    assert inactive.status_code == 201
    assert inactive.json()["guidance_available"] is False
    assert "not currently" in inactive.json()["availability_notice"]
    assert client.get("/api/v1/schemes/demo-education/documents/checklist").status_code == 409


def test_unverified_scheme_can_be_saved_but_not_used_for_guidance(
    client: TestClient,
) -> None:
    sign_in(client, "unverified-scheme@example.com")
    with TestingSessionLocal() as db:
        scheme = db.scalar(select(Scheme).where(Scheme.slug == "demo-education"))
        assert scheme is not None
        scheme.verification_status = "unverified"
        scheme.requires_human_review = True
        db.commit()

    saved = client.post("/api/v1/saved-schemes/demo-education")
    assert saved.status_code == 201
    assert saved.json()["verification_status"] == "unverified"
    assert saved.json()["guidance_available"] is False
    assert client.get(
        "/api/v1/schemes/demo-education/documents/checklist"
    ).status_code == 409
    assert client.get(
        "/api/v1/schemes/demo-education/application-guidance"
    ).status_code == 409
    assert client.post(
        "/api/v1/applications", json={"scheme_id": "demo-education"}
    ).status_code == 409


def test_document_readiness_persists_per_user_and_guidance_is_safe(client: TestClient) -> None:
    sign_in(client, "checklist-owner@example.com")
    checklist = client.get("/api/v1/schemes/demo-education/documents/checklist")
    assert checklist.status_code == 200
    item = checklist.json()["items"][0]
    assert item["ready"] is False
    assert "not individually linked to a source" in item["uncertainty_notice"]
    updated = client.put(
        f"/api/v1/schemes/demo-education/documents/{item['document_id']}",
        json={"ready": True},
    )
    assert updated.status_code == 200
    assert updated.json()["ready"] is True
    assert "does not validate" in checklist.json()["notice"]
    assert client.get("/api/v1/schemes/demo-education/documents/checklist").json()["items"][0]["ready"] is True

    guidance = client.get("/api/v1/schemes/demo-education/application-guidance")
    assert guidance.status_code == 200
    assert guidance.json()["checklist_complete"] is True
    assert guidance.json()["official_application_url"] == "https://policy.gov.example/apply"
    assert "does not submit" in guidance.json()["submission_notice"]

    assert client.post("/auth/logout").status_code == 204
    sign_in(client, "checklist-other@example.com")
    assert client.get("/api/v1/schemes/demo-education/documents/checklist").json()["items"][0]["ready"] is False


def test_saved_scheme_reports_outdated_source_and_blocks_guidance(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    sign_in(client, "outdated-source@example.com")
    monkeypatch.setenv("KNOWLEDGE_MAX_AGE_DAYS", "30")
    with TestingSessionLocal() as db:
        source = db.scalar(
            select(SchemeSource).where(SchemeSource.url == "https://policy.gov.example/education")
        )
        assert source is not None
        source.last_verified_at = utc_now() - timedelta(days=31)
        db.commit()

    saved = client.post("/api/v1/saved-schemes/demo-education")
    assert saved.status_code == 201
    assert saved.json()["guidance_available"] is False
    assert "older than 30 days" in saved.json()["availability_notice"]
    assert saved.json()["last_verified_at"] is not None
    assert client.get(
        "/api/v1/schemes/demo-education/documents/checklist"
    ).status_code == 409
    assert client.get(
        "/api/v1/schemes/demo-education/application-guidance"
    ).status_code == 409


def test_application_tracking_transitions_confirmation_and_ownership(client: TestClient) -> None:
    sign_in(client, "application-owner@example.com")
    created = client.post("/api/v1/applications", json={"scheme_id": "demo-education"})
    assert created.status_code == 201
    application_id = created.json()["id"]
    assert created.json()["status"] == "planning"
    assert client.post("/api/v1/applications", json={"scheme_id": "demo-education"}).status_code == 409
    assert client.patch(
        f"/api/v1/applications/{application_id}",
        json={"status": "submitted_externally"},
    ).status_code == 409
    assert client.patch(
        f"/api/v1/applications/{application_id}",
        json={"status": "ready_to_apply"},
    ).status_code == 200
    missing_confirmation = client.patch(
        f"/api/v1/applications/{application_id}",
        json={"status": "submitted_externally"},
    )
    assert missing_confirmation.status_code == 422
    submitted = client.patch(
        f"/api/v1/applications/{application_id}",
        json={"status": "submitted_externally", "confirm_external_submission": True},
    )
    assert submitted.status_code == 200
    assert submitted.json()["submitted_by_user_confirmation"] is True
    assert submitted.json()["submitted_at"] is not None
    assert client.patch(
        f"/api/v1/applications/{application_id}",
        json={"status": "completed"},
    ).status_code == 200

    assert client.post("/auth/logout").status_code == 204
    sign_in(client, "application-other@example.com")
    assert client.get(f"/api/v1/applications/{application_id}").status_code == 404
    assert client.patch(
        f"/api/v1/applications/{application_id}", json={"status": "planning"}
    ).status_code == 404

    with TestingSessionLocal() as db:
        actions = set(
            db.scalars(select(AuditLog.action).where(AuditLog.action.like("application_tracking.%"))).all()
        )
        assert {"application_tracking.created", "application_tracking.updated"}.issubset(actions)
