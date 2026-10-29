from email.message import EmailMessage

import pytest

from backend.app import email_delivery


class FakeSmtpClient:
    def __init__(self) -> None:
        self.login_arguments: tuple[str, str] | None = None
        self.message: EmailMessage | None = None

    def __enter__(self) -> "FakeSmtpClient":
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def login(self, username: str, password: str) -> None:
        self.login_arguments = (username, password)

    def send_message(self, message: EmailMessage) -> None:
        self.message = message


def test_smtp_verification_email_has_a_secure_link(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = FakeSmtpClient()
    monkeypatch.setenv("EMAIL_PROVIDER", "smtp")
    monkeypatch.setenv("SMTP_HOST", "smtp.resend.com")
    monkeypatch.setenv("SMTP_PORT", "465")
    monkeypatch.setenv("SMTP_USERNAME", "resend")
    monkeypatch.setenv("SMTP_PASSWORD", "re_test_key")
    monkeypatch.setenv("EMAIL_FROM", "SchemeSathi AI <hello@example.com>")
    monkeypatch.setenv("FRONTEND_BASE_URL", "http://localhost:5173")
    monkeypatch.setattr(email_delivery.smtplib, "SMTP_SSL", lambda *_, **__: client)

    email_delivery.send_auth_email(
        object(), "person@example.com", "verification", "safe_token-_123"
    )

    assert client.login_arguments == ("resend", "re_test_key")
    assert client.message is not None
    assert client.message["To"] == "person@example.com"
    assert client.message["Subject"] == "Verify your SchemeSathi AI email"
    plain_part = client.message.get_body(preferencelist=("plain",))
    assert plain_part is not None
    assert "http://localhost:5173/verify-email?token=safe_token-_123" in plain_part.get_content()
    html_part = client.message.get_body(preferencelist=("html",))
    assert html_part is not None
    assert "Verify email address" in html_part.get_content()


def test_smtp_delivery_requires_a_password(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EMAIL_PROVIDER", "smtp")
    monkeypatch.setenv("SMTP_HOST", "smtp.resend.com")
    monkeypatch.setenv("SMTP_PORT", "465")
    monkeypatch.setenv("SMTP_USERNAME", "resend")
    monkeypatch.delenv("SMTP_PASSWORD", raising=False)
    monkeypatch.setenv("EMAIL_FROM", "SchemeSathi AI <hello@example.com>")

    with pytest.raises(RuntimeError, match="SMTP_PASSWORD"):
        email_delivery.send_auth_email(
            object(), "person@example.com", "verification", "safe_token-_123"
        )
