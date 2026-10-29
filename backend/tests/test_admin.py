from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database import Base, get_db
from backend.app.main import app
from backend.app.models import (
    AuditLog,
    Scheme,
    SchemeCategory,
    SchemeEligibilityRule,
    SchemeReviewHistory,
    SchemeSource,
    User,
    utc_now,
)
from backend.tests.catalog_fixtures import seed_catalog_test_fixtures
from backend.app.seed_central_scheme_candidates import (
    seed_central_scheme_candidates,
)

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
    monkeypatch.setenv("OFFICIAL_SOURCE_ALLOWLIST", "gov.in")
    Base.metadata.drop_all(bind=TEST_ENGINE)
    Base.metadata.create_all(bind=TEST_ENGINE)
    with TestingSessionLocal() as db:
        seed_catalog_test_fixtures(db)
    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()
    test_client.close()


def sign_in(client: TestClient, email: str) -> None:
    assert client.post(
        "/auth/register",
        json={"email": email, "full_name": "Admin Test User", "password": "correct horse battery"},
    ).status_code == 202
    token = client.get("/auth/dev-email", params={"email": email, "purpose": "verification"})
    assert client.post("/auth/verify-email", json={"token": token.json()["token"]}).status_code == 200
    assert client.post("/auth/login", json={"email": email, "password": "correct horse battery"}).status_code == 200


def promote(client: TestClient, email: str) -> None:
    with TestingSessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        assert user is not None
        user.is_admin = True
        db.commit()
    assert client.get("/auth/me").json()["is_admin"] is True


def test_ordinary_user_cannot_access_admin_endpoints(client: TestClient) -> None:
    assert client.get("/api/v1/admin/dashboard").status_code == 401
    sign_in(client, "ordinary@example.com")
    assert client.get("/api/v1/admin/dashboard").status_code == 403
    assert client.get("/api/v1/admin/categories").status_code == 403
    assert client.post(
        "/api/v1/admin/categories",
        json={"name": "Unauthorized", "slug": "unauthorized", "description": None},
    ).status_code == 403
    assert client.post(
        "/api/v1/admin/schemes",
        json={
            "name": "Unauthorized scheme",
            "slug": "unauthorized-scheme",
            "description": "An unauthorized attempt to create a scheme.",
        },
    ).status_code == 403
    assert client.post(
        "/api/v1/admin/schemes/demo-education/sources",
        json={
            "url": "https://ministry.gov.in/scheme",
            "title": "Source",
            "source_type": "official_portal",
        },
    ).status_code == 403
    assert client.post(
        "/api/v1/admin/schemes/demo-education/eligibility-rules",
        json={
            "rule_type": "age",
            "rule_text": "Applicants must meet the published age requirement.",
            "reason": "Unauthorized rule creation attempt.",
        },
    ).status_code == 403
    assert client.post(
        "/api/v1/admin/schemes/demo-education/documents",
        json={
            "name": "Identity document",
            "reason": "Unauthorized document requirement attempt.",
        },
    ).status_code == 403
    assert client.post(
        "/api/v1/admin/schemes/demo-education/deadlines",
        json={"deadline_status": "unknown"},
    ).status_code == 403
    assert client.get("/api/v1/admin/audit-logs").status_code == 403


def test_admin_dashboard_flags_quality_and_exposes_reviewed_workflows(
    client: TestClient,
) -> None:
    with TestingSessionLocal() as db:
        seed_central_scheme_candidates(db)
        scheme = db.scalar(select(Scheme).where(Scheme.slug == "pm-kisan"))
        assert scheme is not None
        scheme.eligibility_rules.append(
            SchemeEligibilityRule(
                rule_type="age",
                rule_text="An unsupported operator must be reviewed.",
                rule_data={"field": "age", "operator": "invented", "value": 18},
            )
        )
        db.commit()
    sign_in(client, "admin-dashboard@example.com")
    promote(client, "admin-dashboard@example.com")
    dashboard = client.get("/api/v1/admin/dashboard")
    assert dashboard.status_code == 200
    payload = dashboard.json()
    assert payload["counts"]["schemes"] == 7
    assert all(not item["slug"].startswith("demo-") for item in payload["schemes"])
    candidate = next(item for item in payload["schemes"] if item["slug"] == "pm-kisan")
    assert "Human review required" in candidate["issue_flags"]
    assert "Missing official application URL" in candidate["issue_flags"]
    assert "Unsupported or unstructured eligibility rule" in candidate["issue_flags"]
    assert "categories" in payload
    assert "failed_extractions" in payload
    assert "assistant_feedback" in payload
    assert client.get("/api/v1/admin/review-history").status_code == 200


def test_scheme_changes_require_review_and_keep_rollback_snapshot(
    client: TestClient,
) -> None:
    sign_in(client, "admin-edit@example.com")
    promote(client, "admin-edit@example.com")
    changed = client.patch(
        "/api/v1/admin/schemes/demo-education",
        json={
            "official_application_url": "https://apply.gov.example/education",
            "reason": "Updated from an approved official department document.",
        },
    )
    assert changed.status_code == 200
    assert changed.json()["requires_human_review"] is True
    with TestingSessionLocal() as db:
        scheme = db.scalar(select(Scheme).where(Scheme.slug == "demo-education"))
        assert scheme is not None
        assert scheme.official_application_url == "https://apply.gov.example/education"
        history = db.scalar(
            select(SchemeReviewHistory)
            .where(SchemeReviewHistory.action == "scheme_updated_pending_review")
        )
        assert history is not None
        assert history.before_snapshot is not None
        assert history.before_snapshot["official_application_url"] is None


def test_admin_can_review_corrections_without_auto_applying_user_change(
    client: TestClient,
) -> None:
    sign_in(client, "correction-author@example.com")
    submitted = client.post(
        "/api/v1/scheme-corrections",
        json={
            "scheme_id": "demo-education",
            "report_type": "incorrect_information",
            "description": "The published record appears to have an old application address.",
        },
    )
    assert submitted.status_code == 201
    with TestingSessionLocal() as db:
        scheme = db.scalar(select(Scheme).where(Scheme.slug == "demo-education"))
        assert scheme is not None
        original_url = scheme.official_application_url

    client.post("/auth/logout")
    sign_in(client, "correction-admin@example.com")
    promote(client, "correction-admin@example.com")
    reports = client.get("/api/v1/admin/scheme-corrections")
    assert reports.status_code == 200
    report = reports.json()[0]
    reviewed = client.patch(
        f"/api/v1/admin/scheme-corrections/{report['id']}",
        json={
            "status": "in_review",
            "review_notes": "Checking against the current official department page.",
        },
    )
    assert reviewed.status_code == 200
    with TestingSessionLocal() as db:
        scheme = db.scalar(select(Scheme).where(Scheme.slug == "demo-education"))
        assert scheme is not None
        assert scheme.official_application_url == original_url
        assert db.scalar(select(AuditLog).where(AuditLog.action == "admin.scheme_correction_reviewed"))


def test_admin_category_crud_and_protected_scheme_creation(client: TestClient) -> None:
    sign_in(client, "category-admin@example.com")
    promote(client, "category-admin@example.com")
    created_category = client.post(
        "/api/v1/admin/categories",
        json={
            "name": "Community support",
            "slug": "community-support",
            "description": "Reviewed local support programmes.",
        },
    )
    assert created_category.status_code == 201
    category_id = created_category.json()["id"]
    created_scheme = client.post(
        "/api/v1/admin/schemes",
        json={
            "name": "Reviewed Candidate",
            "slug": "reviewed-candidate",
            "description": "A candidate record entered for authorized review.",
            "category_id": category_id,
            "government_level": "Central",
            "beneficiaries": ["Families"],
            "keywords": ["candidate"],
            "status": "unknown",
        },
    )
    assert created_scheme.status_code == 201
    assert created_scheme.json()["verification_status"] == "unverified"
    with TestingSessionLocal() as db:
        scheme = db.scalar(
            select(Scheme).where(Scheme.slug == "reviewed-candidate")
        )
        assert scheme is not None
        assert scheme.requires_human_review is True
        assert scheme.is_demo is False
        assert scheme.categories[0].id == category_id

    assert client.delete(f"/api/v1/admin/categories/{category_id}").status_code == 409


def test_scheme_verification_requires_current_source_and_review_note(
    client: TestClient,
) -> None:
    sign_in(client, "verify-admin@example.com")
    promote(client, "verify-admin@example.com")
    refused = client.post(
        "/api/v1/admin/schemes/demo-education/verify",
        json={"review_note": "Reviewed scheme details for final approval."},
    )
    assert refused.status_code == 409

    with TestingSessionLocal() as db:
        scheme = db.scalar(select(Scheme).where(Scheme.slug == "demo-education"))
        assert scheme is not None
        scheme.is_demo = False
        scheme.verification_status = "unverified"
        scheme.official_application_url = None
        scheme.requires_human_review = True
        scheme.sources.append(
            SchemeSource(
                url="https://official.gov.example/education",
                title="Official education page",
                official_domain="official.gov.example",
                status="verified",
                last_verified_at=utc_now(),
                reviewed_by_user_id=1,
            )
        )
        db.commit()

    accepted = client.post(
        "/api/v1/admin/schemes/demo-education/verify",
        json={"review_note": "Reviewed against the current official scheme source."},
    )
    assert accepted.status_code == 200
    assert accepted.json()["verification_status"] == "verified"


def test_candidate_placeholder_must_be_replaced_before_scheme_verification(
    client: TestClient,
) -> None:
    sign_in(client, "candidate-admin@example.com")
    promote(client, "candidate-admin@example.com")
    with TestingSessionLocal() as db:
        seed_central_scheme_candidates(db)
        scheme = db.scalar(select(Scheme).where(Scheme.slug == "pm-kisan"))
        assert scheme is not None
        scheme.sources[0].status = "verified"
        scheme.sources[0].last_verified_at = utc_now()
        db.commit()

    response = client.post(
        "/api/v1/admin/schemes/pm-kisan/verify",
        json={"review_note": "Reviewed current scheme details against the source."},
    )
    assert response.status_code == 409
    assert "source-backed overview" in response.json()["detail"]


def test_admin_can_register_sources_and_manage_rules_documents_and_unknown_deadlines(
    client: TestClient,
) -> None:
    sign_in(client, "records-admin@example.com")
    promote(client, "records-admin@example.com")
    category = client.post(
        "/api/v1/admin/categories",
        json={"name": "Health support", "slug": "health-support"},
    )
    assert category.status_code == 201
    scheme_response = client.post(
        "/api/v1/admin/schemes",
        json={
            "name": "Health Support Candidate",
            "slug": "health-support-candidate",
            "description": "A candidate record being entered for careful review.",
            "category_id": category.json()["id"],
        },
    )
    assert scheme_response.status_code == 201

    source_response = client.post(
        "/api/v1/admin/schemes/health-support-candidate/sources",
        json={
            "url": "https://ministry.gov.in/schemes/health",
            "title": "Ministry information page",
            "source_type": "department_page",
        },
    )
    assert source_response.status_code == 201
    source_id = source_response.json()["source_id"]

    rule = client.post(
        "/api/v1/admin/schemes/health-support-candidate/eligibility-rules",
        json={
            "rule_type": "income",
            "rule_text": "The applicant must meet the income requirement.",
            "rule_data": {
                "field": "annual_income_range",
                "operator": "equals",
                "value": "low",
            },
            "source_id": source_id,
            "reason": "Entered from the department's current published criteria.",
        },
    )
    assert rule.status_code == 201
    document = client.post(
        "/api/v1/admin/schemes/health-support-candidate/documents",
        json={
            "name": "Application form",
            "description": "Confirm the current form requirement with the source.",
            "is_required": True,
            "reason": "Recorded as stated by the current official source.",
        },
    )
    assert document.status_code == 201

    deadline = client.post(
        "/api/v1/admin/schemes/health-support-candidate/deadlines",
        json={
            "deadline_type": "application",
            "deadline_status": "unknown",
            "source_id": None,
            "closes_at": None,
            "notes": "No verified date is available.",
        },
    )
    assert deadline.status_code == 201
    assert deadline.json()["deadline_status"] == "unknown"
    assert deadline.json()["closes_at"] is None

    with TestingSessionLocal() as db:
        assert db.scalar(
            select(AuditLog).where(AuditLog.action == "knowledge.source_created")
        )
        assert db.scalar(
            select(AuditLog).where(AuditLog.action == "admin.eligibility_rule_created")
        )
        assert db.scalar(
            select(AuditLog).where(AuditLog.action == "admin.document_requirement_created")
        )
        assert db.scalar(
            select(AuditLog).where(AuditLog.action == "scheme_deadline.created")
        )
