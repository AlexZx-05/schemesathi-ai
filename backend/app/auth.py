import os
import time
import logging
import secrets

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from pydantic import ValidationError
from sqlalchemy import case, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from .database import get_db
from .email_delivery import email_provider, send_auth_email
from .models import AuthRateLimit, AuthSession, AuthToken, DevelopmentEmail, Profile, User
from .schemas import (
    EmailRequest,
    EmailDeliveryStatusResponse,
    GoogleIdentityClaims,
    GoogleTokenRequest,
    LoginRequest,
    PasswordResetRequest,
    RegisterRequest,
    TokenRequest,
    UserResponse,
)
from .security import (
    SESSION_LIFETIME_SECONDS,
    create_session_token,
    hash_password,
    hash_session_token,
    verify_password,
    verify_google_id_token,
)

router = APIRouter(prefix="/auth", tags=["authentication"])
SESSION_COOKIE_NAME = "schemesathi_session"
AUTH_TOKEN_LIFETIME_SECONDS = 60 * 60
logger = logging.getLogger(__name__)


def _cookie_secure() -> bool:
    if os.getenv("ENVIRONMENT", "").strip().lower() == "production":
        return True
    default = "false"
    return os.getenv("AUTH_COOKIE_SECURE", default).strip().lower() in {
        "1",
        "true",
        "yes",
    }


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=SESSION_LIFETIME_SECONDS,
        httponly=True,
        secure=_cookie_secure(),
        samesite="lax",
        path="/",
    )


def _check_origin(request: Request) -> None:
    origin = request.headers.get("origin")
    if not origin:
        return
    allowed = {
        value.strip()
        for value in os.getenv(
            "API_CORS_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173",
        ).split(",")
        if value.strip()
    }
    if origin not in allowed:
        raise HTTPException(status_code=403, detail="Request origin is not allowed.")


def _issue_session(db: Session, user: User, response: Response) -> None:
    token = create_session_token()
    db.add(
        AuthSession(
            token_hash=hash_session_token(token),
            user_id=user.id,
            expires_at=int(time.time()) + SESSION_LIFETIME_SECONDS,
        )
    )
    db.commit()
    _set_session_cookie(response, token)


def _check_rate_limit(request: Request, db: Session, endpoint: str) -> None:
    client_ip = request.client.host if request.client else "unknown"
    bucket_key = hash_session_token(f"{endpoint}:{client_ip}")
    now = int(time.time())
    window_seconds = 15 * 60
    dialect = db.get_bind().dialect.name
    insert = sqlite_insert if dialect == "sqlite" else pg_insert
    values = {
        "key_hash": bucket_key,
        "attempts": 1,
        "window_started_at": now,
    }
    reset_window = AuthRateLimit.window_started_at <= now - window_seconds
    statement = insert(AuthRateLimit).values(**values)
    statement = statement.on_conflict_do_update(
        index_elements=[AuthRateLimit.key_hash],
        set_={
            "attempts": case(
                (reset_window, 1), else_=AuthRateLimit.attempts + 1
            ),
            "window_started_at": case(
                (reset_window, now), else_=AuthRateLimit.window_started_at
            ),
        },
    )
    db.execute(statement)
    db.commit()
    attempts = db.scalar(
        select(AuthRateLimit.attempts).where(AuthRateLimit.key_hash == bucket_key)
    )
    if attempts is not None and attempts > 10:
        raise HTTPException(
            status_code=429,
            detail="Too many authentication requests. Please try again later.",
            headers={"Retry-After": str(window_seconds)},
        )


def _issue_auth_token(db: Session, user: User, purpose: str) -> str:
    db.query(AuthToken).filter(
        AuthToken.user_id == user.id, AuthToken.purpose == purpose
    ).delete()
    token = secrets.token_urlsafe(32)
    db.add(
        AuthToken(
            token_hash=hash_session_token(token),
            user_id=user.id,
            purpose=purpose,
            expires_at=int(time.time()) + AUTH_TOKEN_LIFETIME_SECONDS,
        )
    )
    db.commit()
    return token


def _deliver_auth_token(db: Session, user: User, purpose: str) -> None:
    token = _issue_auth_token(db, user, purpose)
    try:
        send_auth_email(db, user.email, purpose, token)
    except RuntimeError as error:
        logger.error("Authentication email delivery failed: %s", error)
        raise HTTPException(
            status_code=503,
            detail="Email delivery is temporarily unavailable. Please try again later.",
        ) from error


def get_current_user(
    schemesathi_session: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
    db: Session = Depends(get_db),
) -> User:
    if not schemesathi_session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sign in to continue.",
        )

    session_record = db.get(AuthSession, hash_session_token(schemesathi_session))
    if session_record is None or session_record.expires_at <= int(time.time()):
        if session_record is not None:
            db.delete(session_record)
            db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Your session has expired. Please sign in again.",
        )

    user = db.get(User, session_record.user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="This account is unavailable. Please contact support.",
        )
    return user


@router.post("/register", status_code=202)
def register(
    data: RegisterRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    _check_origin(request)
    _check_rate_limit(request, db, "register")
    user = User(
        email=data.email,
        full_name=data.full_name,
        password_hash=hash_password(data.password),
        email_verified=False,
    )
    user.profile = Profile(beneficiary_categories=[])
    db.add(user)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        logger.info("Registration received for an existing email address.")
        return {
            "message": "If this address can be registered, a verification email will be sent."
        }
    _deliver_auth_token(db, user, "verification")
    return {
        "message": "If this address can be registered, a verification email will be sent."
    }


@router.post("/login", response_model=UserResponse)
def login(
    data: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> User:
    _check_origin(request)
    _check_rate_limit(request, db, "login")
    user = db.scalar(select(User).where(User.email == data.email))
    if user is None or not user.is_active or not verify_password(
        data.password, user.password_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email or password is incorrect.",
        )
    if not user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Verify your email address before signing in.",
        )
    _issue_session(db, user, response)
    return user


@router.post("/google", response_model=UserResponse)
def google_login(
    data: GoogleTokenRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> User:
    _check_origin(request)
    _check_rate_limit(request, db, "google")
    client_id = os.getenv("GOOGLE_CLIENT_ID", "").strip()
    if not client_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google sign-in is not configured.",
        )

    try:
        claims = GoogleIdentityClaims.model_validate(
            verify_google_id_token(data.credential, client_id)
        )
    except ValidationError as error:
        logger.warning(
            "Google sign-in rejected because the verified identity claims were incomplete or invalid: %s",
            error,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google sign-in could not be verified.",
        ) from error
    except ValueError as error:
        logger.warning("Google ID token verification failed: %s", error)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google sign-in could not be verified.",
        ) from error

    if not claims.email_verified:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google must verify your email address before sign-in.",
        )

    email = str(claims.email).strip().casefold()
    user = db.scalar(select(User).where(User.google_sub == claims.sub))
    if user is not None and user.email != email:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The Google account email has changed. Contact support.",
        )

    if user is None:
        user = db.scalar(select(User).where(User.email == email))
        if user is not None and user.google_sub not in (None, claims.sub):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This email is linked to a different Google account.",
            )
        if user is None:
            user = User(
                email=email,
                full_name=" ".join(claims.name.split()),
                password_hash=None,
                google_sub=claims.sub,
                email_verified=True,
                is_active=True,
            )
            user.profile = Profile(beneficiary_categories=[])
            db.add(user)
        else:
            user.google_sub = claims.sub
            user.email_verified = True

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="This account is unavailable. Please contact support.",
        )

    try:
        db.flush()
        _issue_session(db, user, response)
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This Google account could not be linked. Please try again.",
        ) from error
    return user


@router.get("/me", response_model=UserResponse)
def current_account(user: User = Depends(get_current_user)) -> User:
    return user


@router.post("/verify-email")
def verify_email(
    data: TokenRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    _check_origin(request)
    _check_rate_limit(request, db, "verify-email")
    token_record = db.get(AuthToken, hash_session_token(data.token))
    if (
        token_record is None
        or token_record.purpose != "verification"
        or token_record.expires_at <= int(time.time())
    ):
        raise HTTPException(status_code=400, detail="This verification link is invalid or expired.")
    user = db.get(User, token_record.user_id)
    if user is None:
        raise HTTPException(status_code=400, detail="This verification link is invalid or expired.")
    user.email_verified = True
    db.delete(token_record)
    db.commit()
    return {"message": "Your email address has been verified. You can now sign in."}


@router.post("/resend-verification")
def resend_verification(
    data: EmailRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    _check_origin(request)
    _check_rate_limit(request, db, "resend-verification")
    user = db.scalar(select(User).where(User.email == data.email))
    if user is not None and not user.email_verified:
        _deliver_auth_token(db, user, "verification")
    return {
        "message": "If this address needs verification, an email will be sent."
    }


@router.post("/forgot-password")
def forgot_password(
    data: EmailRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    _check_origin(request)
    _check_rate_limit(request, db, "forgot-password")
    user = db.scalar(select(User).where(User.email == data.email))
    if user is not None and user.is_active:
        _deliver_auth_token(db, user, "password_reset")
    return {
        "message": "If an account exists for this address, password reset instructions will be sent."
    }


@router.post("/reset-password")
def reset_password(
    data: PasswordResetRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    _check_origin(request)
    _check_rate_limit(request, db, "reset-password")
    token_record = db.get(AuthToken, hash_session_token(data.token))
    if (
        token_record is None
        or token_record.purpose != "password_reset"
        or token_record.expires_at <= int(time.time())
    ):
        raise HTTPException(status_code=400, detail="This reset link is invalid or expired.")
    user = db.get(User, token_record.user_id)
    if user is None:
        raise HTTPException(status_code=400, detail="This reset link is invalid or expired.")
    user.password_hash = hash_password(data.new_password)
    user.email_verified = True
    db.delete(token_record)
    db.query(AuthSession).filter(AuthSession.user_id == user.id).delete()
    db.commit()
    return {"message": "Your password has been reset. Please sign in."}


@router.get("/dev-email")
def development_email(
    email: str,
    purpose: str = "verification",
    db: Session = Depends(get_db),
) -> dict[str, str]:
    if not _development_inbox_available():
        raise HTTPException(status_code=404, detail="Not found.")
    if purpose not in {"verification", "password_reset"}:
        raise HTTPException(status_code=422, detail="Unsupported email purpose.")
    delivery = db.scalar(
        select(DevelopmentEmail)
        .where(
            DevelopmentEmail.email == email.strip().casefold(),
            DevelopmentEmail.purpose == purpose,
        )
        .order_by(DevelopmentEmail.created_at.desc())
    )
    if delivery is None:
        raise HTTPException(status_code=404, detail="No development email is available.")
    return {"purpose": delivery.purpose, "token": delivery.token}


def _development_inbox_available() -> bool:
    return (
        os.getenv("ENVIRONMENT", "").lower() != "production"
        and email_provider() == "development"
    )


@router.get("/email-delivery-status", response_model=EmailDeliveryStatusResponse)
def email_delivery_status() -> EmailDeliveryStatusResponse:
    return EmailDeliveryStatusResponse(
        development_inbox_available=_development_inbox_available()
    )


@router.post("/logout", status_code=204)
def logout(
    request: Request,
    response: Response,
    schemesathi_session: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
    db: Session = Depends(get_db),
) -> Response:
    _check_origin(request)
    _check_rate_limit(request, db, "logout")
    if schemesathi_session:
        session_record = db.get(AuthSession, hash_session_token(schemesathi_session))
        if session_record is not None:
            db.delete(session_record)
            db.commit()
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        httponly=True,
        secure=_cookie_secure(),
        samesite="lax",
        path="/",
    )
    response.status_code = status.HTTP_204_NO_CONTENT
    return response
