import os
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage
from html import escape
from urllib.parse import urlencode

from sqlalchemy.orm import Session

from .models import DevelopmentEmail


@dataclass(frozen=True)
class SmtpConfiguration:
    host: str
    port: int
    username: str
    password: str
    sender: str


def _smtp_configuration() -> SmtpConfiguration:
    host = os.getenv("SMTP_HOST", "").strip()
    sender = os.getenv("EMAIL_FROM", "").strip()
    username = os.getenv("SMTP_USERNAME", "").strip()
    password = os.getenv("SMTP_PASSWORD", "")
    missing = [
        name
        for name, value in {
            "SMTP_HOST": host,
            "SMTP_USERNAME": username,
            "SMTP_PASSWORD": password,
            "EMAIL_FROM": sender,
        }.items()
        if not value
    ]
    if missing:
        raise RuntimeError(f"Missing SMTP configuration: {', '.join(missing)}.")

    try:
        port = int(os.getenv("SMTP_PORT", "587"))
    except ValueError as error:
        raise RuntimeError("SMTP_PORT must be a valid port number.") from error
    if not 1 <= port <= 65535:
        raise RuntimeError("SMTP_PORT must be between 1 and 65535.")
    return SmtpConfiguration(
        host=host,
        port=port,
        username=username,
        password=password,
        sender=sender,
    )


def _send_smtp_message(message: EmailMessage, configuration: SmtpConfiguration) -> None:
    try:
        if configuration.port == 465:
            with smtplib.SMTP_SSL(
                configuration.host, configuration.port, timeout=10
            ) as client:
                client.login(configuration.username, configuration.password)
                client.send_message(message)
        else:
            with smtplib.SMTP(
                configuration.host, configuration.port, timeout=10
            ) as client:
                client.starttls()
                client.login(configuration.username, configuration.password)
                client.send_message(message)
    except (OSError, smtplib.SMTPException) as error:
        raise RuntimeError("The configured email provider could not deliver the message.") from error


def email_provider() -> str:
    configured = os.getenv("EMAIL_PROVIDER", "").strip().lower()
    if configured:
        return configured
    return "smtp" if os.getenv("ENVIRONMENT", "").lower() == "production" else "development"


def send_auth_email(
    db: Session, recipient: str, purpose: str, token: str
) -> None:
    provider = email_provider()
    if provider == "development":
        db.add(
            DevelopmentEmail(
                email=recipient,
                purpose=purpose,
                token=token,
            )
        )
        db.commit()
        return
    if provider != "smtp":
        raise RuntimeError("EMAIL_PROVIDER must be 'development' or 'smtp'.")

    configuration = _smtp_configuration()

    frontend_url = os.getenv("FRONTEND_BASE_URL", "http://localhost:5173").rstrip("/")
    page = "verify-email" if purpose == "verification" else "reset-password"
    link = f"{frontend_url}/{page}?{urlencode({'token': token})}"
    action = "Verify email address" if purpose == "verification" else "Reset password"
    heading = "Verify your email address" if purpose == "verification" else "Reset your password"
    message = EmailMessage()
    message["Subject"] = (
        "Verify your SchemeSathi AI email"
        if purpose == "verification"
        else "Reset your SchemeSathi AI password"
    )
    message["From"] = configuration.sender
    message["To"] = recipient
    message.set_content(
        f"{heading}\n\n"
        f"Use this link to continue: {link}\n\n"
        "This link expires in one hour. If you did not request this, you can ignore this email."
    )
    message.add_alternative(
        "<!doctype html><html><body "
        'style="font-family:Arial,sans-serif;color:#1f2937;line-height:1.5">'
        f"<h1>{escape(heading)}</h1>"
        "<p>Use the button below to continue with SchemeSathi AI.</p>"
        f'<p><a href="{escape(link, quote=True)}" '
        'style="display:inline-block;background:#1d4ed8;color:#ffffff;'
        'padding:12px 18px;border-radius:6px;text-decoration:none;font-weight:600">'
        f"{escape(action)}</a></p>"
        "<p>This link expires in one hour. If you did not request this, you can ignore this email.</p>"
        "</body></html>",
        subtype="html",
    )
    _send_smtp_message(message, configuration)


def send_notification_email(recipient: str, subject: str, body: str) -> None:
    provider = email_provider()
    if provider != "smtp":
        raise RuntimeError(
            "Notification email requires EMAIL_PROVIDER=smtp; development inboxes "
            "are reserved for account verification and password recovery."
        )
    configuration = _smtp_configuration()
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = configuration.sender
    message["To"] = recipient
    message.set_content(body)

    _send_smtp_message(message, configuration)
