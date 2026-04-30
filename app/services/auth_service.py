from __future__ import annotations

import hashlib
import hmac
import secrets

from app.config import AppConfig
from app.db import crud
from app.db.models import UserModel
from app.schemas.entities import User


PBKDF2_ITERATIONS = 260_000
ROLE_OWNER = "owner"
ROLE_ADMIN = "admin"
ROLE_WORKER = "worker"


def hash_password(password: str, *, salt: str | None = None) -> str:
    normalized = password.encode("utf-8")
    actual_salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        normalized,
        actual_salt.encode("utf-8"),
        PBKDF2_ITERATIONS,
    ).hex()
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${actual_salt}${digest}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, iterations_raw, salt, stored_digest = password_hash.split("$", 3)
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    try:
        iterations = int(iterations_raw)
    except ValueError:
        return False
    calculated = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations,
    ).hex()
    return hmac.compare_digest(calculated, stored_digest)


class AuthService:
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def ensure_bootstrap_owner(self) -> None:
        owner = crud.get_user_by_email(self.config, self.config.bootstrap_owner_email)
        if owner is None:
            crud.create_user(
                self.config,
                User(
                    email=self.config.bootstrap_owner_email,
                    password_hash=hash_password(self.config.bootstrap_owner_password),
                    full_name=self.config.bootstrap_owner_name,
                    role=ROLE_OWNER,
                    worker_id=None,
                    status="active",
                ),
            )
        admin = crud.get_user_by_email(self.config, self.config.bootstrap_admin_email)
        if admin is None:
            crud.create_user(
                self.config,
                User(
                    email=self.config.bootstrap_admin_email,
                    password_hash=hash_password(self.config.bootstrap_admin_password),
                    full_name=self.config.bootstrap_admin_name,
                    role=ROLE_ADMIN,
                    worker_id=None,
                    status="active",
                ),
            )

    def authenticate(self, login: str, password: str) -> UserModel | None:
        user = crud.get_user_by_email(self.config, login)
        if user is None or user.status != "active":
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user
