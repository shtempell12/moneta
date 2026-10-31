import hashlib
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def new_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """Tokens are stored hashed, so a leaked database does not expose live sessions."""
    return hashlib.sha256(token.encode()).hexdigest()


def tokens_match(expected: str, received: str) -> bool:
    # Constant-time comparison: response time does not leak how many characters matched.
    return secrets.compare_digest(expected, received)
