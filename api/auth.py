import hashlib
import os
import secrets
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Request, Response

from api.db import get_db, now_iso

COOKIE_NAME = "session"
SESSION_SECONDS = 3600
VERIFY_TOKEN_MINUTES = 30
BCRYPT_COST = 12
MAX_PASSWORD_BYTES = 72
MIN_SECRET_LENGTH = 32

# Checked against on an unknown email, so a wrong email and a wrong password take the same time.
DUMMY_HASH = bcrypt.hashpw(b"not-a-real-password", bcrypt.gensalt(BCRYPT_COST))


def jwt_secret():
    secret = os.environ.get("JWT_SECRET", "")
    if len(secret) < MIN_SECRET_LENGTH:
        raise RuntimeError("JWT_SECRET must be set to 32 characters or more")
    return secret


def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(BCRYPT_COST)).decode()


def check_password(password, password_hash):
    data = password.encode()
    if len(data) > MAX_PASSWORD_BYTES:
        check_dummy_password(password)
        return False
    return bcrypt.checkpw(data, password_hash.encode())


def check_dummy_password(password):
    bcrypt.checkpw(password.encode()[:MAX_PASSWORD_BYTES], DUMMY_HASH)


def create_token(user_id):
    expires = datetime.now(UTC) + timedelta(seconds=SESSION_SECONDS)
    return jwt.encode({"sub": str(user_id), "exp": expires}, jwt_secret(), algorithm="HS256")


def set_session_cookie(response: Response, user_id):
    response.set_cookie(
        COOKIE_NAME,
        create_token(user_id),
        max_age=SESSION_SECONDS,
        path="/",
        httponly=True,
        samesite="lax",
        secure=False,
    )


def clear_session_cookie(response: Response):
    response.delete_cookie(COOKIE_NAME, path="/", httponly=True, samesite="lax")


def user_out(row):
    return {
        "id": row["id"],
        "email": row["email"],
        "name": row["name"],
        "role": row["role"],
        "verified": row["email_verified_at"] is not None,
    }


def hash_token(token):
    return hashlib.sha256(token.encode()).hexdigest()


def new_verification_token(db, user_id):
    stamp = now_iso()
    db.execute(
        "UPDATE email_tokens SET used_at = ? WHERE user_id = ? AND used_at IS NULL",
        (stamp, user_id),
    )
    token = secrets.token_urlsafe(32)
    expires = datetime.now(UTC) + timedelta(minutes=VERIFY_TOKEN_MINUTES)
    db.execute(
        "INSERT INTO email_tokens (user_id, token_hash, expires_at) VALUES (?, ?, ?)",
        (user_id, hash_token(token), expires.isoformat(timespec="seconds")),
    )
    return token


def use_verification_token(db, token):
    stamp = now_iso()
    row = db.execute(
        "SELECT id, user_id FROM email_tokens"
        " WHERE token_hash = ? AND used_at IS NULL AND expires_at > ?",
        (hash_token(token), stamp),
    ).fetchone()
    if row is None:
        return None
    claimed = db.execute(
        "UPDATE email_tokens SET used_at = ? WHERE id = ? AND used_at IS NULL",
        (stamp, row["id"]),
    )
    if claimed.rowcount != 1:
        return None
    db.execute(
        "UPDATE users SET email_verified_at = COALESCE(email_verified_at, ?) WHERE id = ?",
        (stamp, row["user_id"]),
    )
    db.commit()
    return db.execute("SELECT * FROM users WHERE id = ?", (row["user_id"],)).fetchone()


def not_signed_in():
    return HTTPException(status_code=401, detail="Sign in first")


def current_user(request: Request, db=Depends(get_db)):
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise not_signed_in()
    try:
        claims = jwt.decode(
            token, jwt_secret(), algorithms=["HS256"], options={"require": ["sub", "exp"]}
        )
        user_id = int(claims["sub"])
    except (jwt.InvalidTokenError, ValueError):
        raise not_signed_in() from None
    row = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if row is None:
        raise not_signed_in()
    return row
