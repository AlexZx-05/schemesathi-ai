import hashlib
import secrets

from google.auth.exceptions import GoogleAuthError
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2 import id_token
from pwdlib import PasswordHash

password_hash = PasswordHash.recommended()
SESSION_LIFETIME_SECONDS = 60 * 60 * 24 * 14
# Google-issued tokens can briefly appear to be from the future when local and
# provider clocks differ by a few seconds. Keep this tolerance deliberately
# narrow; it is not a substitute for a correctly synchronized system clock.
GOOGLE_ID_TOKEN_CLOCK_SKEW_SECONDS = 10


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str | None) -> bool:
    if hashed_password is None:
        return False
    return password_hash.verify(password, hashed_password)


def verify_google_id_token(credential: str, client_id: str) -> dict[str, object]:
    try:
        claims = id_token.verify_oauth2_token(
            credential,
            GoogleRequest(),
            audience=client_id,
            clock_skew_in_seconds=GOOGLE_ID_TOKEN_CLOCK_SKEW_SECONDS,
        )
    except (GoogleAuthError, ValueError) as error:
        # Keep the browser response generic, but preserve the provider reason for
        # the server-side authentication log (for example, an audience mismatch).
        raise ValueError(str(error)) from error
    return claims


def create_session_token() -> str:
    return secrets.token_urlsafe(32)


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
