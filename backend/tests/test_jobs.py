from collections.abc import Generator
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database import Base, get_db
from backend.app.main import app
from backend.app.models import User

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
    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()
    test_client.close()


def sign_in_as_admin(client: TestClient) -> None:
    email = "jobs-admin@example.com"
    assert (
        client.post(
            "/auth/register",
            json={
                "email": email,
                "full_name": "Jobs Admin",
                "password": "correct horse battery",
            },
        ).status_code
        == 202
    )
    token = client.get(
        "/auth/dev-email",
        params={"email": email, "purpose": "verification"},
    ).json()["token"]
    assert client.post("/auth/verify-email", json={"token": token}).status_code == 200
    assert (
        client.post(
            "/auth/login",
            json={"email": email, "password": "correct horse battery"},
        ).status_code
        == 200
    )
    with TestingSessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        assert user is not None
        user.is_admin = True
        db.commit()
    client.post("/auth/logout")
    assert (
        client.post(
            "/auth/login",
            json={"email": email, "password": "correct horse battery"},
        ).status_code
        == 200
    )


def job_payload() -> dict[str, object]:
    now = datetime.now(timezone.utc)
    return {
        "slug": "engineering-officer-2026",
        "title": "Engineering Officer",
        "recruiting_body": "Central Recruitment Board",
        "description": "A central government engineering recruitment notice.",
        "employment_type": "Full-time",
        "eligible_states": ["Karnataka"],
        "minimum_qualification": "BTech",
        "minimum_education_level": "Undergraduate",
        "field_of_study": "Mechanical Engineering",
        "minimum_experience_years": 1,
        "minimum_age": 20,
        "maximum_age": 35,
        "keywords": ["engineering", "technical"],
        "application_opens": (now - timedelta(days=2)).isoformat(),
        "application_deadline": (now + timedelta(days=10)).isoformat(),
        "deadline_status": "known",
        "official_notice_url": "https://recruitment.gov.in/notices/engineering-2026",
        "application_url": "https://recruitment.gov.in/apply/engineering-2026",
        "status": "open",
        "documents": [
            {"name": "Degree certificate", "description": "Engineering degree proof."},
            {"name": "Identity proof"},
        ],
        "reason": "Entered from the official recruitment notification.",
    }


def test_admin_curates_and_verifies_jobs_before_publication(
    client: TestClient,
) -> None:
    assert client.get("/api/v1/jobs").json()["total"] == 0
    assert client.get("/api/v1/job-recommendations").status_code == 401
    sign_in_as_admin(client)

    created = client.post("/api/v1/admin/jobs", json=job_payload())
    assert created.status_code == 201
    assert created.json()["verification_status"] == "unverified"
    assert client.get("/api/v1/jobs").json()["total"] == 0

    verified = client.post(
        "/api/v1/admin/jobs/engineering-officer-2026/verify",
        json={"review_note": "Checked current dates and requirements in the official notice."},
    )
    assert verified.status_code == 200
    assert verified.json()["verification_status"] == "verified"

    public = client.get("/api/v1/jobs", params={"state": "Karnataka"})
    assert public.status_code == 200
    assert public.json()["total"] == 1
    record = public.json()["items"][0]
    assert record["title"] == "Engineering Officer"
    assert record["deadline_status"] == "known"
    assert len(record["documents"]) == 2
    assert record["official_notice_url"].startswith("https://")

    profile = client.put(
        "/api/v1/profile",
        json={
            "state": "Karnataka",
            "occupation": "Job seeker",
            "education_level": "Undergraduate",
            "qualification": "BTech",
            "field_of_study": "Mechanical Engineering",
            "years_experience": 2,
            "preferred_job_roles": ["engineering"],
            "preferred_job_states": ["Karnataka"],
            "age": 25,
        },
    )
    assert profile.status_code == 200
    assert "reservation_category" not in profile.json()

    recommendations = client.get("/api/v1/job-recommendations")
    assert recommendations.status_code == 200
    match = recommendations.json()["items"][0]
    assert match["slug"] == "engineering-officer-2026"
    assert match["missing_information"] == []
    assert match["match_reasons"]


def test_job_update_requires_reverification_and_expired_jobs_stay_hidden(
    client: TestClient,
) -> None:
    sign_in_as_admin(client)
    payload = job_payload()
    assert client.post("/api/v1/admin/jobs", json=payload).status_code == 201
    assert (
        client.post(
            "/api/v1/admin/jobs/engineering-officer-2026/verify",
            json={"review_note": "Checked current dates and requirements in the official notice."},
        ).status_code
        == 200
    )

    updated = {**payload, "description": "Updated recruitment information from notice."}
    response = client.put(
        "/api/v1/admin/jobs/engineering-officer-2026",
        json=updated,
    )
    assert response.status_code == 200
    assert response.json()["verification_status"] == "requires_review"
    assert client.get("/api/v1/jobs").json()["total"] == 0

    expired = job_payload()
    expired["slug"] = "expired-job"
    expired["application_deadline"] = (
        datetime.now(timezone.utc) - timedelta(days=1)
    ).isoformat()
    assert client.post("/api/v1/admin/jobs", json=expired).status_code == 201
    rejected = client.post(
        "/api/v1/admin/jobs/expired-job/verify",
        json={"review_note": "Checked that this notice deadline has expired."},
    )
    assert rejected.status_code == 409
