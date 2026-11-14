import logging
import os
import sqlite3
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import PurePosixPath
from typing import Literal

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, Field, field_validator
from starlette.concurrency import run_in_threadpool

from api import case_files, report_md
from api import email as mailer
from api.auth import (
    MAX_PASSWORD_BYTES,
    check_dummy_password,
    check_password,
    clear_session_cookie,
    current_user,
    hash_password,
    jwt_secret,
    new_verification_token,
    set_session_cookie,
    use_verification_token,
    user_out,
)
from api.db import get_db, init_db, now_iso
from api.permissions import DEFAULT_ROLE, ROLE_PERMISSIONS, require

logger = logging.getLogger("chimera.api")
UPLOAD_LIMIT_BYTES = 10 * 1024 * 1024


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


@app.exception_handler(case_files.UnreadableCaseFile)
async def unreadable_case_file(request: Request, exc: case_files.UnreadableCaseFile):
    logger.error("Could not read a case file: %s", exc)
    return JSONResponse(status_code=500, content={"detail": "The case files could not be read"})


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


class VerifyBody(BaseModel):
    token: str = Field(max_length=200)


class RunBody(BaseModel):
    night: Literal["attack", "stopped", "gap", "quiet", "spray", "late_work", "random"] = "attack"


def app_url():
    return (os.environ.get("APP_URL") or "http://localhost:3000").rstrip("/")


def send_verification(background_tasks, db, user):
    token = new_verification_token(db, user["id"])
    db.commit()
    link = f"{app_url()}/verify?token={token}"
    background_tasks.add_task(mailer.send_verification_email, user["email"], user["name"], link)


@app.post("/api/auth/signup", status_code=201)
def signup(
    body: SignupBody,
    response: Response,
    background_tasks: BackgroundTasks,
    db=Depends(get_db),
):
    try:
        cursor = db.execute(
            "INSERT INTO users (email, name, password_hash, role, created_at)"
            " VALUES (?, ?, ?, ?, ?)",
            (body.email, body.name, hash_password(body.password), DEFAULT_ROLE, now_iso()),
        )
    except sqlite3.IntegrityError:
        raise HTTPException(
            status_code=409, detail="An account with this email already exists"
        ) from None
    row = db.execute("SELECT * FROM users WHERE id = ?", (cursor.lastrowid,)).fetchone()
    send_verification(background_tasks, db, row)
    set_session_cookie(response, row["id"])
    return user_out(row)


@app.post("/api/auth/verify")
def verify(body: VerifyBody, db=Depends(get_db)):
    row = use_verification_token(db, body.token)
    if row is None:
        raise HTTPException(status_code=400, detail="This link is invalid or has expired")
    return user_out(row)


@app.post("/api/auth/resend-verification", status_code=204)
def resend_verification(
    background_tasks: BackgroundTasks, user=Depends(current_user), db=Depends(get_db)
):
    if user["email_verified_at"] is not None:
        raise HTTPException(status_code=409, detail="Your email is already confirmed")
    send_verification(background_tasks, db, user)


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


def no_case():
    return HTTPException(status_code=404, detail="Run the investigation first")


@app.get("/api/intake")
def get_intake(user=Depends(require("case:read"))):
    data = case_files.intake()
    if data is None:
        raise no_case()
    return JSONResponse(content=data)


@app.get("/api/case")
def get_case(user=Depends(require("case:read"))):
    data = case_files.case()
    if data is None:
        raise no_case()
    return JSONResponse(content=data)


@app.get("/api/case/stress/{level}")
def get_stress(level: str, user=Depends(require("case:read"))):
    if level not in {str(n) for n in case_files.STRESS_LEVELS}:
        raise HTTPException(status_code=404, detail="Unknown stress level")
    with case_files.lock:
        data = case_files.stress(int(level))
        has_case = data is not None or case_files.case() is not None
    if not has_case:
        raise no_case()
    if data is None:
        raise HTTPException(status_code=404, detail="This stress level is not ready yet")
    return JSONResponse(content=data)


@app.post("/api/case/run")
def run_case(body: RunBody | None = None, user=Depends(require("case:run")), db=Depends(get_db)):
    def clear_approvals():
        db.execute("DELETE FROM approvals")
        db.commit()

    night = body.night if body else "attack"
    try:
        data = case_files.run_investigation(on_success=clear_approvals, night=night)
    except Exception as exc:
        logger.error("The investigation failed: %s", exc)
        raise HTTPException(status_code=500, detail="The investigation failed") from None
    if data is None:
        logger.error("The investigation failed: the engine wrote no case.json")
        raise HTTPException(status_code=500, detail="The investigation failed")
    return JSONResponse(content=data)


@app.get("/api/case/report.md")
def get_report_markdown(level: int = 0, user=Depends(require("case:read")), db=Depends(get_db)):
    if level not in case_files.STRESS_LEVELS:
        raise HTTPException(status_code=404, detail="Unknown stress level")
    with case_files.lock:
        data = case_files.stress(level) if level else case_files.case()
        source = case_files.source()
    if data is None:
        raise no_case()
    rows = db.execute(
        "SELECT a.action_id, u.name AS approved_by, a.approved_at"
        " FROM approvals a LEFT JOIN users u ON u.id = a.user_id"
    ).fetchall()
    approvals = {row["action_id"]: dict(row) for row in rows}
    exported_at = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    text = report_md.build(data, approvals, source, exported_at)
    return Response(
        content=text,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="chimera-incident-report.md"'},
    )


@app.get("/api/case/version")
def get_case_version(user=Depends(require("case:read")), db=Depends(get_db)):
    approvals = db.execute("SELECT COUNT(*) FROM approvals").fetchone()[0]
    return {
        "case": case_files.case_version(),
        "approvals": approvals,
        "source": case_files.source(),
    }


async def read_upload(request):
    body = bytearray()
    async for chunk in request.stream():
        body += chunk
        if len(body) > UPLOAD_LIMIT_BYTES:
            raise HTTPException(status_code=413, detail="The file is larger than 10 MB")
    text = body.decode("utf-8", errors="replace")
    if not text.strip():
        raise HTTPException(status_code=422, detail="The file is empty")
    return text


def file_label(name):
    return PurePosixPath(name.replace("\\", "/")).name.strip()[:120] or "uploaded file"


@app.post("/api/case/upload")
async def upload_logs(
    request: Request, name: str = "", user=Depends(require("case:run")), db=Depends(get_db)
):
    def clear_approvals():
        db.execute("DELETE FROM approvals")
        db.commit()

    text = await read_upload(request)
    try:
        result = await run_in_threadpool(
            case_files.run_upload, text, file_label(name), clear_approvals
        )
    except case_files.NoReadableLines as exc:
        raise HTTPException(
            status_code=422, detail=f"None of the {exc.unparsed} lines could be read as a log line"
        ) from None
    except case_files.SpanTooLong as exc:
        raise HTTPException(
            status_code=422,
            detail=f"The lines cover {exc.hours} hours. Upload at most 24 hours of logs at a time",
        ) from None
    except Exception as exc:
        logger.error("The upload investigation failed: %s", exc)
        raise HTTPException(status_code=500, detail="The investigation failed") from None
    return result


@app.post("/api/actions/{action_id}/approve", status_code=201)
def approve(action_id: str, user=Depends(require("action:approve")), db=Depends(get_db)):
    with case_files.lock:
        current = case_files.case() or {}
        if action_id not in {action["id"] for action in current.get("actions", [])}:
            raise HTTPException(status_code=404, detail="This action is not in the current case")
        stamp = now_iso()
        try:
            db.execute(
                "INSERT INTO approvals (action_id, user_id, approved_at) VALUES (?, ?, ?)",
                (action_id, user["id"], stamp),
            )
            db.commit()
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=409, detail="This action is already approved") from None
    return {"action_id": action_id, "approved_by": user["name"], "approved_at": stamp}


@app.get("/api/approvals")
def list_approvals(user=Depends(require("case:read")), db=Depends(get_db)):
    rows = db.execute(
        "SELECT a.action_id, u.name AS approved_by, a.approved_at"
        " FROM approvals a LEFT JOIN users u ON u.id = a.user_id"
        " ORDER BY a.approved_at, a.id"
    ).fetchall()
    return [dict(row) for row in rows]


@app.get("/api/users")
def list_users(user=Depends(require("user:manage")), db=Depends(get_db)):
    rows = db.execute("SELECT * FROM users ORDER BY id").fetchall()
    return [user_out(row) for row in rows]


class RoleBody(BaseModel):
    role: str

    @field_validator("role")
    @classmethod
    def known_role(cls, value):
        if value not in ROLE_PERMISSIONS:
            raise ValueError("Unknown role")
        return value


@app.patch("/api/users/{user_id}/role")
def change_role(
    user_id: int, body: RoleBody, admin=Depends(require("user:manage")), db=Depends(get_db)
):
    if user_id == admin["id"]:
        raise HTTPException(status_code=409, detail="You cannot change your own role")
    if db.execute("SELECT 1 FROM users WHERE id = ?", (user_id,)).fetchone() is None:
        raise HTTPException(status_code=404, detail="User not found")
    db.execute("UPDATE users SET role = ? WHERE id = ?", (body.role, user_id))
    db.commit()
    return user_out(db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone())
