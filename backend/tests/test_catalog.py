from collections.abc import Generator
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database import Base, get_db
from backend.app.main import app
from backend.app.models import (
    AuditLog,
    SavedScheme,
    ApplicationTracking,
    SchemeDeadline,
    Scheme,
    SchemeCategory,
    SchemeSource,
    SchemeStateCoverage,
    User,
)
from backend.tests.catalog_fixtures import seed_catalog_test_fixtures
from backend.app.seed_central_scheme_candidates import (
    seed_central_scheme_candidates,
)

TEST_ENGINE = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(
    bind=TEST_ENGINE,
    autoflush=False,
    expire_on_commit=False,
)


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
    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()
    test_client.close()


def authenticated_client(client: TestClient, email: str) -> None:
    registered = client.post(
        "/auth/register",
        json={
            "email": email,
            "full_name": "Sample Person",
            "password": "correct horse battery",
        },
    )
    assert registered.status_code == 202
    dev_email = client.get(
        "/auth/dev-email",
        params={"email": email, "purpose": "verification"},
    )
    assert dev_email.status_code == 200
    assert client.post(
        "/auth/verify-email",
        json={"token": dev_email.json()["token"]},
    ).status_code == 200
    assert client.post(
        "/auth/login",
        json={"email": email, "password": "correct horse battery"},
    ).status_code == 200


def test_catalog_hides_unverified_and_test_records(client: TestClient) -> None:
    page = client.get("/api/v1/schemes", params={"page": 2, "page_size": 2})
    assert page.status_code == 200
    assert page.json()["items"] == []
    assert page.json()["total"] == 0
    assert page.json()["pages"] == 0

    searched = client.get("/api/v1/schemes", params={"q": "career"})
    assert searched.json()["items"] == []
    category = client.get("/api/v1/schemes", params={"category": "education"})
    assert category.json()["items"] == []
    bypass_attempt = client.get(
        "/api/v1/schemes", params={"include_demo": "true", "page_size": 100}
    )
    assert bypass_attempt.json()["total"] == 0
    assert client.get("/api/v1/schemes", params={"page_size": 101}).status_code == 422

    with TestingSessionLocal() as db:
        scheme = db.scalar(select(Scheme).where(Scheme.slug == "demo-education"))
        assert scheme is not None
        scheme.state_coverage.append(SchemeStateCoverage(state="Karnataka"))
        db.commit()
    state_filtered = client.get(
        "/api/v1/schemes", params={"state": "Karnataka"}
    )
    assert state_filtered.json()["items"] == []


def test_scheme_detail_categories_sources_and_unknown_deadlines(
    client: TestClient,
) -> None:
    assert client.get("/api/v1/schemes/demo-education").status_code == 404
    assert client.get("/api/v1/categories").json() == []
    assert client.get("/api/v1/schemes/missing/sources").status_code == 404


def test_central_scheme_candidates_are_idempotent_and_unverified(
    client: TestClient,
) -> None:
    with TestingSessionLocal() as db:
        assert seed_central_scheme_candidates(db) == 7
        assert seed_central_scheme_candidates(db) == 0

    candidates = client.get("/api/v1/schemes", params={"page_size": 100})
    assert candidates.status_code == 200
    assert candidates.json()["total"] == 0

    detail = client.get("/api/v1/schemes/pm-kisan")
    assert detail.status_code == 404


def test_verified_scheme_is_published_with_its_official_source(
    client: TestClient,
) -> None:
    with TestingSessionLocal() as db:
        scheme = db.scalar(select(Scheme).where(Scheme.slug == "demo-education"))
        assert scheme is not None
        scheme.is_demo = False
        scheme.status = "active"
        scheme.verification_status = "verified"
        scheme.requires_human_review = False
        db.add(
            SchemeSource(
                scheme_id=scheme.id,
                url="https://education.gov.in/scheme",
                title="Education department",
                status="verified",
                last_verified_at=datetime.now(timezone.utc),
            )
        )
        db.commit()

    listing = client.get("/api/v1/schemes")
    assert listing.status_code == 200
    assert listing.json()["total"] == 1
    assert listing.json()["items"][0]["id"] == "demo-education"
    assert listing.json()["items"][0]["data_status"] == "verified"

    detail = client.get("/api/v1/schemes/demo-education")
    assert detail.status_code == 200
    assert detail.json()["verification_status"] == "verified"
    assert detail.json()["sources"][0]["status"] == "verified"
    assert [item["name"] for item in client.get("/api/v1/categories").json()] == [
        "Education"
    ]


def test_source_url_does_not_imply_verification(client: TestClient) -> None:
    with TestingSessionLocal() as db:
        scheme = db.scalar(select(Scheme).where(Scheme.slug == "demo-education"))
        assert scheme is not None
        db.add(
            SchemeSource(
                scheme_id=scheme.id,
                url="https://example.gov.test/scheme",
                title="Unreviewed source",
                source_type="official_portal",
                official_domain="example.gov.test",
            )
        )
        db.commit()

    sources = client.get("/api/v1/schemes/demo-education/sources")
    assert sources.status_code == 404
    with TestingSessionLocal() as db:
        scheme = db.scalar(select(Scheme).where(Scheme.slug == "demo-education"))
        assert scheme is not None
        db.add(
            SchemeSource(
                scheme_id=scheme.id,
                url="https://example.gov.test/scheme",
                source_type="official_portal",
            )
        )
        with pytest.raises(IntegrityError):
            db.flush()
        db.rollback()


def test_authenticated_profile_patch_uses_session_identity(
    client: TestClient,
) -> None:
    assert client.get("/api/v1/profile").status_code == 401
    authenticated_client(client, "private@example.com")
    response = client.patch(
        "/api/v1/profile",
        json={
            "state": "Karnataka",
            "education_level": "Undergraduate",
            "occupation": "Student",
        },
    )
    assert response.status_code == 200
    assert response.json()["profile_complete"] is True
    assert client.patch(
        "/api/v1/profile",
        json={"user_id": 999, "state": "Karnataka"},
    ).status_code == 422


def test_unique_constraints_and_audit_model_crud(client: TestClient) -> None:
    with TestingSessionLocal() as db:
        user = User(
            email="crud@example.com",
            full_name="CRUD User",
            password_hash="not-used-in-this-db-test",
            email_verified=True,
        )
        scheme = Scheme(
            name="Persistence Test",
            slug="persistence-test",
            description="A schema-level persistence fixture.",
            government_level="Unknown",
            target_beneficiaries=[],
            keywords=[],
            status="unknown",
            verification_status="requires_review",
            requires_human_review=True,
            is_demo=False,
        )
        category = db.scalar(
            select(SchemeCategory).where(SchemeCategory.slug == "education")
        )
        assert category is not None
        scheme.categories.append(category)
        user.saved_schemes.append(SavedScheme(scheme=scheme))
        db.add(user)
        db.commit()

        with pytest.raises(IntegrityError):
            db.add(SavedScheme(user_id=user.id, scheme_id=scheme.id))
            db.commit()
        db.rollback()

        saved = db.scalar(
            select(SavedScheme).where(
                SavedScheme.user_id == user.id,
                SavedScheme.scheme_id == scheme.id,
            )
        )
        assert saved is not None
        db.delete(saved)
        scheme.description = "Updated persistence test description."
        db.commit()
        assert db.scalar(
            select(Scheme).where(Scheme.slug == "persistence-test")
        ).description == "Updated persistence test description."
        db.delete(scheme)
        db.commit()
        assert db.scalar(
            select(Scheme).where(Scheme.slug == "persistence-test")
        ) is None

    with TestingSessionLocal() as db:
        audit = AuditLog(
            action="test.create",
            entity_type="scheme",
            entity_id="persistence-test",
            details={"test": True},
        )
        db.add(audit)
        db.commit()
        assert db.scalar(select(AuditLog).where(AuditLog.action == "test.create"))
        db.delete(audit)
        db.commit()
        assert db.scalar(select(AuditLog).where(AuditLog.action == "test.create")) is None


def test_eligibility_requires_authentication_and_refuses_demo_records(
    client: TestClient,
) -> None:
    unauthenticated = client.post(
        "/api/v1/schemes/demo-education/eligibility"
    )
    assert unauthenticated.status_code == 401

    authenticated_client(client, "eligibility@example.com")
    response = client.post("/api/v1/schemes/demo-education/eligibility")

    assert response.status_code == 200
    result = response.json()
    assert result["outcome"] == "unable_to_determine"
    assert result["sources"] == []
    assert all(
        criterion["result"] == "requires_confirmation"
        for criterion in result["criteria"]
    )
    assert "not an eligibility guarantee" in result["disclaimer"]


def test_verified_structured_rules_use_authenticated_profile(
    client: TestClient,
) -> None:
    authenticated_client(client, "verified-eligibility@example.com")
    profile_response = client.patch(
        "/api/v1/profile",
        json={
            "age": 23,
            "state": "Bihar",
            "education_level": "Undergraduate",
            "occupation": "Student",
        },
    )
    assert profile_response.status_code == 200

    with TestingSessionLocal() as db:
        scheme = db.scalar(
            select(Scheme).where(Scheme.slug == "demo-education")
        )
        assert scheme is not None
        scheme.is_demo = False
        scheme.verification_status = "verified"
        scheme.requires_human_review = False
        for index, rule in enumerate(scheme.eligibility_rules):
            if index == 0:
                rule.rule_data = {"field": "age", "operator": "min", "value": 21}
            else:
                rule.rule_data = {
                    "field": "state",
                    "operator": "eq",
                    "value": "Bihar",
                }
        source = SchemeSource(
            scheme_id=scheme.id,
            url="https://example.gov.in/education",
            title="Verified test source",
            source_type="official_portal",
            official_domain="example.gov.in",
            status="verified",
        )
        db.add(source)
        db.flush()
        for rule in scheme.eligibility_rules:
            rule.source_id = source.id
        db.commit()

    response = client.post("/api/v1/schemes/demo-education/eligibility")

    assert response.status_code == 200
    result = response.json()
    assert result["outcome"] == "potentially_eligible"
    assert all(criterion["result"] == "satisfied" for criterion in result["criteria"])
    assert result["sources"][0]["url"] == "https://example.gov.in/education"

    not_eligible_profile = client.patch("/api/v1/profile", json={"age": 18})
    assert not_eligible_profile.status_code == 200
    non_matching = client.post(
        "/api/v1/schemes/demo-education/eligibility"
    )
    assert non_matching.json()["outcome"] == "known_criteria_not_satisfied"

    incomplete_profile = client.patch("/api/v1/profile", json={"age": None})
    assert incomplete_profile.status_code == 200
    insufficient = client.post(
        "/api/v1/schemes/demo-education/eligibility"
    )
    assert insufficient.json()["outcome"] == "more_information_required"


def test_hypothetical_answers_are_validated_and_do_not_update_profile(
    client: TestClient,
) -> None:
    authenticated_client(client, "hypothetical-eligibility@example.com")
    assert client.patch("/api/v1/profile", json={"age": 23}).status_code == 200

    with TestingSessionLocal() as db:
        scheme = db.scalar(
            select(Scheme).where(Scheme.slug == "demo-education")
        )
        assert scheme is not None
        scheme.is_demo = False
        scheme.verification_status = "verified"
        scheme.requires_human_review = False
        for rule in scheme.eligibility_rules:
            rule.rule_data = {"field": "age", "operator": "min", "value": 21}
        source = SchemeSource(
            scheme_id=scheme.id,
            url="https://example.gov.in/education",
            status="verified",
        )
        db.add(source)
        db.flush()
        for rule in scheme.eligibility_rules:
            rule.source_id = source.id
        db.commit()

    response = client.post(
        "/api/v1/schemes/demo-education/eligibility-check",
        json={"answers": {"age": 18}},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["assessment_mode"] == "hypothetical_answers"
    assert payload["criteria"][0]["result"] == "not_satisfied"
    assert payload["criteria"][0]["evaluated_value"] == 18
    assert payload["criteria"][0]["rule_source_references"][0]["url"] == (
        "https://example.gov.in/education"
    )

    saved_profile = client.get("/api/v1/profile")
    assert saved_profile.status_code == 200
    assert saved_profile.json()["age"] == 23
    assert client.post(
        "/api/v1/schemes/demo-education/eligibility-check",
        json={"answers": {"state": "Not a state"}},
    ).status_code == 422
    assert client.post(
        "/api/v1/schemes/demo-education/eligibility-check",
        json={"answers": {"unexpected": "value"}},
    ).status_code == 422


def test_unstructured_criteria_cannot_be_guessed(
    client: TestClient,
) -> None:
    authenticated_client(client, "unknown-rule@example.com")
    client.patch(
        "/api/v1/profile",
        json={
            "age": 23,
            "state": "Bihar",
            "education_level": "Undergraduate",
            "occupation": "Student",
        },
    )

    with TestingSessionLocal() as db:
        scheme = db.scalar(
            select(Scheme).where(Scheme.slug == "demo-education")
        )
        assert scheme is not None
        scheme.is_demo = False
        scheme.verification_status = "verified"
        scheme.requires_human_review = False
        db.add(
            SchemeSource(
                scheme_id=scheme.id,
                url="https://example.gov.in/education",
                status="verified",
            )
        )
        db.commit()

    response = client.post("/api/v1/schemes/demo-education/eligibility")

    assert response.status_code == 200
    assert response.json()["outcome"] == "more_information_required"
    assert any(
        criterion["result"] == "requires_confirmation"
        for criterion in response.json()["criteria"]
    )
    assert all(
        criterion["rule_source_references"] == []
        for criterion in response.json()["criteria"]
    )


def test_recommendations_are_authenticated_paginated_and_explain_matches(
    client: TestClient,
) -> None:
    assert client.get("/api/v1/recommendations").status_code == 401
    authenticated_client(client, "recommendations@example.com")
    profile_response = client.patch(
        "/api/v1/profile",
        json={
            "state": "Bihar",
            "education_level": "Undergraduate",
            "occupation": "Student",
            "beneficiary_categories": ["Students"],
        },
    )
    assert profile_response.status_code == 200

    first_page = client.get(
        "/api/v1/recommendations", params={"page": 1, "page_size": 1}
    )
    assert first_page.status_code == 200
    payload = first_page.json()
    assert payload["profile_complete"] is True
    assert payload["completion_percentage"] == 100
    assert payload["total"] == 0
    assert payload["pages"] == 0
    assert payload["items"] == []

    second_page = client.get(
        "/api/v1/recommendations", params={"page": 2, "page_size": 1}
    )
    assert second_page.status_code == 200
    assert second_page.json()["items"] == []
    assert client.get(
        "/api/v1/recommendations", params={"page_size": 0}
    ).status_code == 422


def test_recommendations_report_missing_profile_and_no_matches(
    client: TestClient,
) -> None:
    authenticated_client(client, "incomplete-recommendations@example.com")
    response = client.get("/api/v1/recommendations")

    assert response.status_code == 200
    payload = response.json()
    assert payload["profile_complete"] is False
    assert payload["completion_percentage"] == 0
    assert payload["missing_profile_fields"] == [
        "State or territory",
        "Education level",
        "Occupation",
    ]
    assert payload["items"] == []
    assert payload["total"] == 0


def test_recommendations_filter_verified_state_coverage(
    client: TestClient,
) -> None:
    authenticated_client(client, "state-coverage@example.com")
    client.patch(
        "/api/v1/profile",
        json={
            "state": "Bihar",
            "education_level": "Undergraduate",
            "occupation": "Student",
            "beneficiary_categories": ["Students"],
        },
    )
    with TestingSessionLocal() as db:
        scheme = db.scalar(
            select(Scheme).where(Scheme.slug == "demo-education")
        )
        assert scheme is not None
        scheme.is_demo = False
        scheme.verification_status = "verified"
        scheme.requires_human_review = False
        scheme.state_coverage.append(SchemeStateCoverage(state="Karnataka"))
        db.add(
            SchemeSource(
                scheme_id=scheme.id,
                url="https://example.gov.in/education",
                status="verified",
            )
        )
        db.commit()

    response = client.get("/api/v1/recommendations")
    assert response.status_code == 200
    assert "demo-education" not in {
        item["scheme_id"] for item in response.json()["items"]
    }


def test_recommendation_explains_verified_criteria_and_cites_source(
    client: TestClient,
) -> None:
    authenticated_client(client, "verified-recommendation@example.com")
    client.patch(
        "/api/v1/profile",
        json={
            "age": 23,
            "state": "Bihar",
            "education_level": "Undergraduate",
            "occupation": "Student",
            "beneficiary_categories": ["Students"],
        },
    )
    with TestingSessionLocal() as db:
        scheme = db.scalar(
            select(Scheme).where(Scheme.slug == "demo-education")
        )
        assert scheme is not None
        scheme.is_demo = False
        scheme.verification_status = "verified"
        scheme.requires_human_review = False
        for index, rule in enumerate(scheme.eligibility_rules):
            rule.rule_data = (
                {"field": "age", "operator": "min", "value": 18}
                if index == 0
                else {"field": "state", "operator": "eq", "value": "Bihar"}
            )
        source = SchemeSource(
            scheme_id=scheme.id,
            url="https://example.gov.in/education",
            title="Reviewed scheme details",
            status="verified",
        )
        db.add(source)
        db.flush()
        for rule in scheme.eligibility_rules:
            rule.source_id = source.id
        db.commit()

    response = client.get("/api/v1/recommendations")
    assert response.status_code == 200
    recommendation = next(
        item
        for item in response.json()["items"]
        if item["scheme_id"] == "demo-education"
    )
    assert recommendation["eligibility_status"] == "potentially_eligible"
    assert [item["result"] for item in recommendation["criteria"]] == [
        "satisfied",
        "satisfied",
    ]
    assert recommendation["sources"][0]["url"] == "https://example.gov.in/education"


def test_dashboard_summary_scopes_applications_and_only_shows_verified_deadlines(
    client: TestClient,
) -> None:
    assert client.get("/api/v1/dashboard/summary").status_code == 401
    authenticated_client(client, "dashboard-summary@example.com")
    with TestingSessionLocal() as db:
        user = db.scalar(
            select(User).where(User.email == "dashboard-summary@example.com")
        )
        scheme = db.scalar(
            select(Scheme).where(Scheme.slug == "demo-education")
        )
        assert user is not None and scheme is not None
        scheme.is_demo = False
        scheme.verification_status = "verified"
        scheme.requires_human_review = False
        db.add(
            SchemeSource(
                scheme_id=scheme.id,
                url="https://example.gov.in/education",
                title="Verified scheme source",
                status="verified",
            )
        )
        db.add(
            ApplicationTracking(
                user_id=user.id,
                scheme_id=scheme.id,
                status="preparing_documents",
            )
        )
        db.add(
            SchemeDeadline(
                scheme_id=scheme.id,
                deadline_type="application",
                closes_at=datetime.now(timezone.utc) + timedelta(days=14),
                deadline_status="known",
            )
        )
        other_user = User(
            email="another-dashboard-user@example.com",
            full_name="Another User",
            email_verified=True,
        )
        other_scheme = db.scalar(
            select(Scheme).where(Scheme.slug == "demo-agriculture")
        )
        assert other_scheme is not None
        db.add(other_user)
        db.flush()
        db.add(
            ApplicationTracking(
                user_id=other_user.id,
                scheme_id=scheme.id,
                status="completed",
            )
        )
        db.add(
            SchemeDeadline(
                scheme_id=other_scheme.id,
                deadline_type="application",
                closes_at=datetime.now(timezone.utc) + timedelta(days=3),
                deadline_status="known",
            )
        )
        db.commit()

    response = client.get("/api/v1/dashboard/summary")
    assert response.status_code == 200
    payload = response.json()
    assert payload["application_total"] == 1
    assert payload["application_status_counts"] == {"preparing_documents": 1}
    assert len(payload["verified_upcoming_deadlines"]) == 1
    assert (
        payload["verified_upcoming_deadlines"][0]["scheme_id"]
        == "demo-education"
    )
    assert (
        payload["verified_upcoming_deadlines"][0]["source_url"]
        == "https://example.gov.in/education"
    )
