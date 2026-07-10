"""Password hashing — Argon2id, per the Authentication skill's Credential
Management principle ("Hash passwords using Argon2id (preferred)")."""

from __future__ import annotations

from argon2 import PasswordHasher as _Argon2Hasher
from argon2.exceptions import Argon2Error

_hasher = _Argon2Hasher()

ALGORITHM = "argon2id"


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except Argon2Error:
        return False
