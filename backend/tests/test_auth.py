from collections.abc import Generator

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
def client(
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[TestClient, None, None]:
    monkeypatch.setenv("EMAIL_PROVIDER", "development")
    monkeypatch.setenv("ENVIRONMENT", "test")
    Base.metadata.drop_all(bind=TEST_ENGINE)
    Base.metadata.create_all(bind=TEST_ENGINE)
    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()
    test_client.close()


def register(client: TestClient, email: str = "person@example.com") -> dict:
    response = client.post(
        "/auth/register",
        json={
            "email": email,
            "full_name": " Sample Person ",
            "password": "correct horse battery",
        },
    )
    assert response.status_code == 202
    email_record = client.get(
        "/auth/dev-email",
        params={"email": email, "purpose": "verification"},
    )
    assert email_record.status_code == 200
    verified = client.post(
        "/auth/verify-email",
        json={"token": email_record.json()["token"]},
    )
    assert verified.status_code == 200
    login_response = client.post(
        "/auth/login",
        json={"email": email, "password": "correct horse battery"},
    )
    assert login_response.status_code == 200
    return login_response.json()


def profile_payload(**updates: object) -> dict:
    payload: dict = {
        "full_name": "Sample Person",
        "age": None,
        "state": "Karnataka",
        "occupation": "Student",
        "occupation_other": None,
        "education_level": "Undergraduate",
        "annual_income_range": "Prefer not to say",
        "beneficiary_categories": ["Students"],
    }
    payload.update(updates)
    return payload


def test_register_creates_account_and_secure_session(client: TestClient) -> None:
    response = client.post(
        "/auth/register",
        json={
            "email": "  Person@Example.com ",
            "full_name": "  Sample   Person ",
            "password": "correct horse battery",
        },
    )

    assert response.status_code == 202
    assert "verification email" in response.json()["message"]
    assert "set-cookie" not in response.headers

    with TestingSessionLocal() as session:
        user = session.scalar(select(User).where(User.email == "person@example.com"))
        assert user is not None
        assert user.email_verified is False
        assert user.password_hash != "correct horse battery"

    email_record = client.get(
        "/auth/dev-email",
        params={"email": "person@example.com", "purpose": "verification"},
    )
    assert email_record.status_code == 200
    verification = client.post(
        "/auth/verify-email",
        json={"token": email_record.json()["token"]},
    )
    assert verification.status_code == 200
    login = client.post(
        "/auth/login",
        json={"email": "person@example.com", "password": "correct horse battery"},
    )
    assert login.status_code == 200
    cookie = login.headers["set-cookie"].lower()
    assert "httponly" in cookie
    assert "samesite=lax" in cookie
    assert client.get("/auth/me").json()["email"] == "person@example.com"


def test_google_signup_can_complete_profile(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client-id")
    monkeypatch.setattr(
        "backend.app.auth.verify_google_id_token",
        lambda _credential, _client_id: {
            "sub": "google-subject",
            "email": "google-person@example.com",
            "email_verified": True,
            "name": "Google Person",
        },
    )

    signup = client.post(
        "/auth/google",
        json={"credential": "verified-google-token"},
    )
    assert signup.status_code == 200
    assert signup.json()["profile_complete"] is False

    profile = client.put(
        "/profile",
        json={
            "state": "Karnataka",
            "occupation": "Student",
            "education_level": "Undergraduate",
        },
    )
    assert profile.status_code == 200
    assert profile.json()["profile_complete"] is True
    assert profile.json()["email"] == "google-person@example.com"


def test_email_delivery_status_only_exposes_local_inbox_in_development(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert client.get("/auth/email-delivery-status").json() == {
        "development_inbox_available": True
    }

    monkeypatch.setenv("EMAIL_PROVIDER", "smtp")
    assert client.get("/auth/email-delivery-status").json() == {
        "development_inbox_available": False
    }



def test_duplicate_emails_are_case_insensitive(client: TestClient) -> None:
    register(client)

    response = client.post(
        "/auth/register",
        json={
            "email": "PERSON@example.com",
            "full_name": "Another Person",
            "password": "correct horse battery",
        },
    )

    assert response.status_code == 202
    assert response.json() == {
        "message": "If this address can be registered, a verification email will be sent."
    }


def test_login_uses_generic_invalid_credentials_error(client: TestClient) -> None:
    register(client)

    response = client.post(
        "/auth/login",
        json={"email": "person@example.com", "password": "wrong password"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Email or password is incorrect."


def test_unverified_account_is_directed_to_verify_email(client: TestClient) -> None:
    response = client.post(
        "/auth/register",
        json={
            "email": "person@example.com",
            "full_name": "Sample Person",
            "password": "correct horse battery",
        },
    )

    assert response.status_code == 202
    login = client.post(
        "/auth/login",
        json={"email": "person@example.com", "password": "correct horse battery"},
    )
    assert login.status_code == 403
    assert login.json()["detail"] == "Verify your email address before signing in."


def test_password_reset_uses_one_time_token_and_revokes_sessions(
    client: TestClient,
) -> None:
    register(client)
    request = client.post(
        "/auth/forgot-password",
        json={"email": "person@example.com"},
    )
    assert request.status_code == 200
    development_email = client.get(
        "/auth/dev-email",
        params={"email": "person@example.com", "purpose": "password_reset"},
    )
    token = development_email.json()["token"]

    reset = client.post(
        "/auth/reset-password",
        json={"token": token, "new_password": "a brand new long password"},
    )
    assert reset.status_code == 200
    assert client.get("/auth/me").status_code == 401
    assert client.post(
        "/auth/reset-password",
        json={"token": token, "new_password": "another long password"},
    ).status_code == 400
    assert client.post(
        "/auth/login",
        json={"email": "person@example.com", "password": "correct horse battery"},
    ).status_code == 401
    assert client.post(
        "/auth/login",
        json={"email": "person@example.com", "password": "a brand new long password"},
    ).status_code == 200


def test_authentication_endpoint_rate_limit(client: TestClient) -> None:
    for _ in range(10):
        response = client.post(
            "/auth/login",
            json={"email": "person@example.com", "password": "wrong password"},
        )
        assert response.status_code == 401

    limited = client.post(
        "/auth/login",
        json={"email": "person@example.com", "password": "wrong password"},
    )
    assert limited.status_code == 429
    assert limited.headers["retry-after"] == "900"


def test_registration_validates_password_and_rejects_extra_fields(
    client: TestClient,
) -> None:
    response = client.post(
        "/auth/register",
        json={
            "email": "person@example.com",
            "full_name": "Sample Person",
            "password": "short",
            "admin": True,
        },
    )

    assert response.status_code == 422


def test_profile_is_private_and_can_be_created_and_corrected(
    client: TestClient,
) -> None:
    account = register(client)
    initial = client.get("/profile")

    assert initial.status_code == 200
    assert initial.json()["id"] == account["id"]
    assert initial.json()["state"] is None

    saved = client.put(
        "/profile",
        json=profile_payload(full_name="Updated Name", state="Kerala"),
    )
    assert saved.status_code == 200
    assert saved.json()["full_name"] == "Updated Name"
    assert saved.json()["state"] == "Kerala"
    assert saved.json()["beneficiary_categories"] == ["Students"]
    assert client.get("/auth/me").json()["full_name"] == "Updated Name"

    client.post("/auth/logout")
    register(client, "second@example.com")
    own_profile = client.get("/profile")

    assert own_profile.status_code == 200
    assert own_profile.json()["id"] != account["id"]
    assert own_profile.json()["state"] is None
    assert client.get(f"/profile/{account['id']}").status_code == 404


def test_profile_validation_and_origin_protection(client: TestClient) -> None:
    register(client)
    invalid_profile = client.put(
        "/profile",
        json=profile_payload(age=17, state="Not a state"),
    )
    rejected_origin = client.post(
        "/auth/logout",
        headers={"Origin": "https://attacker.example"},
    )

    assert invalid_profile.status_code == 422
    assert rejected_origin.status_code == 403
    assert client.get("/profile").json()["state"] is None


def test_profile_partial_save_and_completion(client: TestClient) -> None:
    register(client)
    first_step = client.put("/profile", json={"age": 32, "district": "Mysuru"})
    assert first_step.status_code == 200
    assert first_step.json()["district"] == "Mysuru"
    assert first_step.json()["profile_complete"] is False

    completed = client.put(
        "/profile",
        json={
            "state": "Karnataka",
            "occupation": "Farmer",
            "education_level": "Secondary",
        },
    )
    assert completed.status_code == 200
    assert completed.json()["age"] == 32
    assert completed.json()["district"] == "Mysuru"
    assert completed.json()["profile_complete"] is True


def test_logout_revokes_session_and_protected_profile_requires_login(
    client: TestClient,
) -> None:
    register(client)

    response = client.post("/auth/logout")

    assert response.status_code == 204
    assert client.get("/auth/me").status_code == 401
    assert client.get("/profile").status_code == 401
