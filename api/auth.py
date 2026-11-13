import os
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Request, Response

from api.db import get_db

COOKIE_NAME = "session"
SESSION_SECONDS = 3600
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
