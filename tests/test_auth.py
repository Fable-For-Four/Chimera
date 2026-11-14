import sqlite3
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from api import db
from api import email as mailer
from api.main import app
from api.permissions import require
from api.seed import seed

SECRET = "test-secret-that-is-at-least-32-characters"
PASSWORD = "test-pass-123"

perm_app = FastAPI()


@perm_app.get("/read")
def read_route(user=Depends(require("case:read"))):
    return {"ok": True}


@perm_app.post("/approve")
def approve_route(user=Depends(require("action:approve"))):
    return {"ok": True}


@perm_app.get("/users")
def users_route(user=Depends(require("user:manage"))):
    return {"ok": True}


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("JWT_SECRET", SECRET)
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    monkeypatch.setattr(mailer, "send_verification_email", lambda to, name, link: None)
    with TestClient(app) as c:
        conn = db.connect()
        seed(conn, PASSWORD)
        conn.close()
        yield c


def signup(client, email="new@example.com", name="New Person", password="good-password"):
    body = {"email": email, "name": name, "password": password}
    return client.post("/api/auth/signup", json=body)


def login(client, email, password=PASSWORD):
    return client.post("/api/auth/login", json={"email": email, "password": password})


def session_for(client, email):
    assert login(client, email).status_code == 200
    token = client.cookies.get("session")
    client.cookies.clear()
    return token


def perm_client(token):
    c = TestClient(perm_app)
    c.cookies.set("session", token)
    return c


def test_signup_returns_viewer_and_session_cookie(client):
    r = signup(client)
    assert r.status_code == 201
    body = r.json()
    assert body == {
        "id": body["id"],
        "email": "new@example.com",
        "name": "New Person",
        "role": "viewer",
        "verified": False,
    }
    cookie = r.headers["set-cookie"].lower()
    assert "session=" in cookie
    assert "httponly" in cookie
    assert "samesite=lax" in cookie
    assert "max-age=3600" in cookie
    assert "secure" not in cookie


def test_signup_same_email_different_case_is_conflict(client):
    assert signup(client, email="Case@Example.com").status_code == 201
    r = signup(client, email="  case@EXAMPLE.com ")
    assert r.status_code == 409
    assert r.json() == {"detail": "An account with this email already exists"}


@pytest.mark.parametrize("password", ["a" * 7, "a" * 73, "é" * 37])
def test_signup_password_outside_8_to_72_bytes_is_rejected(client, password):
    r = signup(client, password=password)
    assert r.status_code == 422
    assert password not in r.text


@pytest.mark.parametrize("field,value", [("email", "not-an-email"), ("name", "   ")])
def test_signup_bad_email_or_empty_name_is_rejected(client, field, value):
    body = {"email": "x@example.com", "name": "X", "password": "good-password", field: value}
    r = client.post("/api/auth/signup", json=body)
    assert r.status_code == 422
    assert isinstance(r.json()["detail"], str)


def test_wrong_password_and_unknown_email_give_same_401(client):
    wrong = login(client, "analyst@acme.test", "wrong-password")
    unknown = login(client, "nobody@acme.test", "wrong-password")
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json() == {"detail": "Email or password is incorrect"}


@pytest.mark.parametrize("password", ["x" * 73, "é" * 40])
def test_login_with_over_long_password_is_same_401(client, password):
    known = login(client, "analyst@acme.test", password)
    unknown = login(client, "nobody@acme.test", password)
    assert known.status_code == unknown.status_code == 401
    assert known.json() == unknown.json() == {"detail": "Email or password is incorrect"}


def test_bad_email_message_is_plain(client):
    r = signup(client, email="not-an-email")
    assert r.json() == {"detail": "Enter a valid email address"}


@pytest.mark.parametrize("password", ["short", "x" * 73])
def test_seed_rejects_a_bad_seed_password(monkeypatch, tmp_path, password):
    from api import seed as seed_module

    monkeypatch.setattr(db, "DB_PATH", tmp_path / "seed.db")
    monkeypatch.setenv("SEED_PASSWORD", password)
    with pytest.raises(SystemExit, match="8 to 72 bytes"):
        seed_module.main()


def test_seeded_analyst_can_sign_in_and_see_themselves(client):
    r = login(client, "ANALYST@acme.test")
    assert r.status_code == 200
    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["role"] == "analyst"
    assert me.json()["verified"] is True


def test_me_without_cookie_is_401(client):
    assert client.get("/api/auth/me").status_code == 401


def test_me_with_tampered_token_is_401(client):
    token = session_for(client, "analyst@acme.test")
    header, payload, signature = token.split(".")
    tampered = jwt.encode(
        {"sub": "1", "exp": datetime.now(UTC) + timedelta(hours=1)}, "x" * 40, algorithm="HS256"
    )
    client.cookies.set("session", tampered)
    assert client.get("/api/auth/me").status_code == 401
    client.cookies.set("session", f"{header}.{payload}.{signature[::-1]}")
    assert client.get("/api/auth/me").status_code == 401


def test_me_with_expired_token_is_401(client):
    expired = jwt.encode(
        {"sub": "1", "exp": datetime.now(UTC) - timedelta(seconds=1)}, SECRET, algorithm="HS256"
    )
    client.cookies.set("session", expired)
    assert client.get("/api/auth/me").status_code == 401


def test_me_for_deleted_user_is_401(client):
    token = session_for(client, "viewer@acme.test")
    conn = db.connect()
    conn.execute("DELETE FROM users WHERE email = ?", ("viewer@acme.test",))
    conn.commit()
    conn.close()
    client.cookies.set("session", token)
    assert client.get("/api/auth/me").status_code == 401


def test_token_holds_only_sub_and_exp(client):
    claims = jwt.decode(session_for(client, "analyst@acme.test"), SECRET, algorithms=["HS256"])
    assert set(claims) == {"sub", "exp"}


def test_logout_clears_cookie(client):
    login(client, "analyst@acme.test")
    r = client.post("/api/auth/logout")
    assert r.status_code == 204
    assert 'session=""' in r.headers["set-cookie"] or "max-age=0" in r.headers["set-cookie"].lower()


def test_no_response_contains_password_hash(client):
    responses = [
        signup(client),
        signup(client),
        signup(client, email="short@example.com", password="short"),
        login(client, "analyst@acme.test", "wrong-password"),
        login(client, "analyst@acme.test"),
        client.get("/api/auth/me"),
    ]
    for r in responses:
        assert "password_hash" not in r.text
        assert "$2b$" not in r.text


def test_viewer_can_read_but_not_approve(client):
    c = perm_client(session_for(client, "viewer@acme.test"))
    assert c.get("/read").status_code == 200
    r = c.post("/approve")
    assert r.status_code == 403
    assert r.json() == {"detail": "Your role cannot do this"}


def test_analyst_can_approve_but_not_manage_users(client):
    c = perm_client(session_for(client, "analyst@acme.test"))
    assert c.post("/approve").status_code == 200
    assert c.get("/users").status_code == 403


def test_admin_can_manage_users(client):
    c = perm_client(session_for(client, "admin@acme.test"))
    assert c.get("/users").status_code == 200


def test_role_change_applies_to_existing_cookie(client):
    c = perm_client(session_for(client, "analyst@acme.test"))
    assert c.post("/approve").status_code == 200
    conn = db.connect()
    conn.execute("UPDATE users SET role = ? WHERE email = ?", ("viewer", "analyst@acme.test"))
    conn.commit()
    conn.close()
    assert c.post("/approve").status_code == 403


def test_unverified_user_is_told_to_confirm_email(client):
    signup(client)
    c = perm_client(client.cookies.get("session"))
    r = c.get("/read")
    assert r.status_code == 403
    assert r.json() == {"detail": "Confirm your email first"}


def test_not_signed_in_is_401_before_permission_check(monkeypatch, tmp_path):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    assert TestClient(perm_app).post("/approve").status_code == 401


@pytest.mark.parametrize("secret", [None, "too-short"])
def test_app_refuses_to_start_without_a_long_jwt_secret(monkeypatch, tmp_path, secret):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    if secret is None:
        monkeypatch.delenv("JWT_SECRET", raising=False)
    else:
        monkeypatch.setenv("JWT_SECRET", secret)
    with pytest.raises(RuntimeError):
        with TestClient(app):
            pass


def test_seed_is_idempotent(client):
    conn = db.connect()
    assert seed(conn, PASSWORD) == []
    count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    conn.close()
    assert count == 3


def test_signup_cleans_email_and_ignores_extra_role_field(client):
    body = {"email": "  Mixed@Example.COM ", "name": " Pat ", "password": "good-password"}
    r = client.post("/api/auth/signup", json={**body, "role": "admin"})
    assert r.status_code == 201
    assert r.json()["email"] == "mixed@example.com"
    assert r.json()["name"] == "Pat"
    assert r.json()["role"] == "viewer"
    client.cookies.clear()
    again = login(client, " MIXED@example.com ", "good-password")
    assert again.status_code == 200
    assert again.json()["role"] == "viewer"


@pytest.mark.parametrize("password", ["a" * 8, "a" * 72])
def test_signup_password_of_8_and_72_bytes_is_accepted(client, password):
    assert signup(client, password=password).status_code == 201


def test_password_is_stored_as_bcrypt_cost_12_hash(client):
    signup(client, password="good-password")
    conn = db.connect()
    stored = conn.execute("SELECT password_hash FROM users WHERE email = ?", ("new@example.com",))
    stored = stored.fetchone()[0]
    conn.close()
    assert stored.startswith("$2b$12$")
    assert "good-password" not in stored


def test_login_cookie_has_the_same_flags_as_signup(client):
    cookie = login(client, "analyst@acme.test").headers["set-cookie"].lower()
    for flag in ["httponly", "samesite=lax", "path=/", "max-age=3600"]:
        assert flag in cookie
    assert "secure" not in cookie


def test_cookie_is_secure_when_cookie_secure_is_true(client, monkeypatch):
    monkeypatch.setenv("COOKIE_SECURE", "true")
    assert "secure" in login(client, "analyst@acme.test").headers["set-cookie"].lower()
    assert "secure" in client.post("/api/auth/logout").headers["set-cookie"].lower()


def test_signup_cookie_path_is_root(client):
    assert "path=/" in signup(client).headers["set-cookie"].lower().replace("; ", ";").split(";")


def test_token_sub_is_user_id_string_and_expires_in_one_hour(client):
    claims = jwt.decode(session_for(client, "viewer@acme.test"), SECRET, algorithms=["HS256"])
    assert claims["sub"].isdigit()
    left = claims["exp"] - datetime.now(UTC).timestamp()
    assert 3500 < left <= 3600


def test_unknown_email_login_still_runs_a_bcrypt_check(client, monkeypatch):
    calls = []
    monkeypatch.setattr("api.main.check_dummy_password", lambda password: calls.append(password))
    assert login(client, "nobody@acme.test", "whatever-1").status_code == 401
    assert calls == ["whatever-1"]


def make_token(claims, secret=SECRET, algorithm="HS256"):
    return jwt.encode(claims, secret, algorithm=algorithm)


def test_me_rejects_token_without_exp_or_with_bad_sub_or_alg_none(client):
    soon = datetime.now(UTC) + timedelta(hours=1)
    bad_tokens = [
        make_token({"sub": "1"}),
        make_token({"sub": "abc", "exp": soon}),
        make_token({"exp": soon}),
        jwt.encode({"sub": "1", "exp": soon}, None, algorithm="none"),
    ]
    for token in bad_tokens:
        client.cookies.set("session", token)
        assert client.get("/api/auth/me").status_code == 401


def test_unverified_admin_is_told_to_confirm_email_before_role_check(client):
    signup(client)
    conn = db.connect()
    conn.execute("UPDATE users SET role = ? WHERE email = ?", ("admin", "new@example.com"))
    conn.commit()
    conn.close()
    c = perm_client(client.cookies.get("session"))
    for r in [c.get("/users"), c.post("/approve")]:
        assert r.status_code == 403
        assert r.json() == {"detail": "Confirm your email first"}


def test_unknown_role_has_no_permissions(client):
    conn = db.connect()
    conn.execute("UPDATE users SET role = ? WHERE email = ?", ("ghost", "viewer@acme.test"))
    conn.commit()
    conn.close()
    c = perm_client(session_for(client, "viewer@acme.test"))
    r = c.get("/read")
    assert r.status_code == 403
    assert r.json() == {"detail": "Your role cannot do this"}


def test_seed_creates_verified_users_with_expected_roles(client):
    conn = db.connect()
    rows = conn.execute("SELECT email, role, email_verified_at FROM users ORDER BY email")
    rows = [tuple(r) for r in rows]
    conn.close()
    assert [(e, role) for e, role, _ in rows] == [
        ("admin@acme.test", "admin"),
        ("analyst@acme.test", "analyst"),
        ("viewer@acme.test", "viewer"),
    ]
    assert all(verified for _, _, verified in rows)


def test_approvals_table_rejects_a_second_approval_of_the_same_action(client):
    conn = db.connect()
    sql = "INSERT INTO approvals (action_id, user_id, approved_at) VALUES (?, ?, ?)"
    conn.execute(sql, ("act-1", 1, db.now_iso()))
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(sql, ("act-1", 2, db.now_iso()))
    conn.close()
