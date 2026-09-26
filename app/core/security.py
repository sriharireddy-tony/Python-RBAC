"""Password hashing and JWT issuing/verification.

No database and no HTTP here -- pure cryptographic helpers, so they can be
unit-tested and reused from a CLI or worker.
"""

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

from app.core.config import settings

# Argon2id is the current password-hashing recommendation (OWASP). It is
# memory-hard, which makes GPU/ASIC cracking far more expensive than bcrypt.
_hasher = PasswordHasher()

ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"


# --------------------------------------------------------------------------
# Passwords
# --------------------------------------------------------------------------
def hash_password(password: str) -> str:
    """Hash a plaintext password. The salt is generated and embedded by argon2."""
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Constant-time-ish verification. Never raises on a bad password."""
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def needs_rehash(password_hash: str) -> bool:
    """True when the hash was made with weaker parameters than we now use."""
    try:
        return _hasher.check_needs_rehash(password_hash)
    except InvalidHashError:
        return False


# --------------------------------------------------------------------------
# JSON Web Tokens
# --------------------------------------------------------------------------
def _create_token(
    *,
    subject: uuid.UUID,
    tenant_id: uuid.UUID,
    token_type: str,
    expires_delta: timedelta,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "tenant_id": str(tenant_id),
        "token_type": token_type,
        "iat": now,
        "exp": now + expires_delta,
        "jti": str(uuid.uuid4()),
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(*, user_id: uuid.UUID, tenant_id: uuid.UUID) -> str:
    """Short-lived token carrying identity only.

    Deliberately carries NO permissions: they are resolved from the database
    per request, so revoking a role takes effect immediately instead of when
    the token happens to expire.
    """
    return _create_token(
        subject=user_id,
        tenant_id=tenant_id,
        token_type=ACCESS_TOKEN_TYPE,
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )


def create_refresh_token(
    *, user_id: uuid.UUID, tenant_id: uuid.UUID, family_id: uuid.UUID
) -> str:
    return _create_token(
        subject=user_id,
        tenant_id=tenant_id,
        token_type=REFRESH_TOKEN_TYPE,
        expires_delta=timedelta(days=settings.refresh_token_expire_days),
        extra_claims={"family_id": str(family_id)},
    )


def decode_token(token: str) -> dict[str, Any]:
    """Decode and verify a JWT. Raises jwt.PyJWTError on any problem."""
    return jwt.decode(
        token,
        settings.secret_key,
        algorithms=[settings.jwt_algorithm],
        # Pin the algorithm list: accepting "none" or a caller-chosen algorithm
        # is the classic JWT forgery vector.
    )


# --------------------------------------------------------------------------
# Opaque token hashing (for refresh tokens at rest)
# --------------------------------------------------------------------------
def hash_token(token: str) -> str:
    """SHA-256 of a token, for storage and lookup.

    A fast hash is correct here, unlike for passwords: the token already has
    full cryptographic entropy, so there is nothing to brute-force, and
    lookups must stay indexable.
    """
    return hashlib.sha256(token.encode()).hexdigest()


def generate_opaque_token() -> str:
    return secrets.token_urlsafe(48)
