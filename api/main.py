import sqlite3
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, field_validator

from api.auth import (
    MAX_PASSWORD_BYTES,
    check_dummy_password,
    check_password,
    clear_session_cookie,
    current_user,
    hash_password,
    jwt_secret,
    set_session_cookie,
    user_out,
)
from api.db import get_db, init_db, now_iso
from api.permissions import DEFAULT_ROLE


@asynccontextmanager
async def lifespan(app):
    jwt_secret()
    init_db()
    yield


app = FastAPI(title="Chimera API", lifespan=lifespan)


@app.exception_handler(RequestValidationError)
async def plain_validation_error(request: Request, exc: RequestValidationError):
    # Turns pydantic's error list into one plain sentence, and never echoes the input back.
    errors = exc.errors()
    if not errors:
        message = "Invalid request"
    elif errors[0]["loc"][-1] == "email":
        message = "Enter a valid email address"
    else:
        message = errors[0]["msg"].removeprefix("Value error, ")
    return JSONResponse(status_code=422, content={"detail": message})


def clean_email(value):
    return value.strip().lower() if isinstance(value, str) else value


class SignupBody(BaseModel):
    email: EmailStr
    name: str
    password: str

    _clean_email = field_validator("email", mode="before")(clean_email)

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("Name cannot be empty")
        return value

    @field_validator("password")
    @classmethod
    def password_length(cls, value):
        if not 8 <= len(value.encode()) <= MAX_PASSWORD_BYTES:
            raise ValueError("Password must be 8 to 72 bytes long")
        return value


class LoginBody(BaseModel):
    email: str
    password: str

    _clean_email = field_validator("email", mode="before")(clean_email)


@app.post("/api/auth/signup", status_code=201)
def signup(body: SignupBody, response: Response, db=Depends(get_db)):
    try:
        cursor = db.execute(
            "INSERT INTO users (email, name, password_hash, role, created_at)"
            " VALUES (?, ?, ?, ?, ?)",
            (body.email, body.name, hash_password(body.password), DEFAULT_ROLE, now_iso()),
        )
        db.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(
            status_code=409, detail="An account with this email already exists"
        ) from None
    row = db.execute("SELECT * FROM users WHERE id = ?", (cursor.lastrowid,)).fetchone()
    set_session_cookie(response, row["id"])
    return user_out(row)


@app.post("/api/auth/login")
def login(body: LoginBody, response: Response, db=Depends(get_db)):
    row = db.execute("SELECT * FROM users WHERE email = ?", (body.email,)).fetchone()
    if row is None:
        check_dummy_password(body.password)
        raise HTTPException(status_code=401, detail="Email or password is incorrect")
    if not check_password(body.password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="Email or password is incorrect")
    set_session_cookie(response, row["id"])
    return user_out(row)


@app.post("/api/auth/logout", status_code=204)
def logout(response: Response):
    clear_session_cookie(response)


@app.get("/api/auth/me")
def me(user=Depends(current_user)):
    return user_out(user)
